"""Client helpers for interacting with the local Ollama LLM server."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable
import urllib.error
import urllib.request

from flask import current_app

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RankedSlot:
    """Container for a ranked appointment slot returned by the LLM."""

    slot_id: int
    score: float | None
    rationale: str


class LLMRankingError(RuntimeError):
    """Raised when the LLM response cannot be interpreted."""


class LLMCommunicationError(RuntimeError):
    """Raised when the Ollama server cannot be reached."""


def _ollama_endpoint() -> str:
    base_url: str = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return base_url.rstrip("/") + "/api/generate"


def _ollama_model() -> str:
    return current_app.config.get("OLLAMA_MODEL", "qwen2.5:1.5b")


def render_prompt(*, prompt_template: str, slot_listing: str, context: dict[str, Any]) -> str:
    """Render the prompt template defined in the LLM integration guide."""

    formatted = prompt_template.format(slot_listing=slot_listing, **context)
    return formatted.strip()


def call_llm(prompt: str) -> dict[str, Any]:
    """Call the Ollama server and return the decoded JSON response."""

    payload = {"model": _ollama_model(), "prompt": prompt, "stream": False}
    LOGGER.debug("Sending prompt to Ollama: %s", payload)

    request = urllib.request.Request(
        _ollama_endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.URLError as exc:
        raise LLMCommunicationError("Unable to contact Ollama server.") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise LLMCommunicationError("Ollama response was not valid JSON.") from exc

    LOGGER.debug("Received response from Ollama: %s", data)
    return data


def parse_llm_response(raw: str) -> list[RankedSlot]:
    """Parse the JSON payload returned by the LLM into ranked slots."""

    text = raw.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise LLMRankingError("Response did not contain JSON data.") from exc
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc2:  # pragma: no cover - defensive branch
            raise LLMRankingError("Response JSON was malformed.") from exc2

    if not isinstance(parsed, dict):
        raise LLMRankingError("Response JSON must be an object.")

    recommendations = parsed.get("recommendations")
    if not isinstance(recommendations, Iterable):
        raise LLMRankingError("Response must include a 'recommendations' array.")

    ranked_slots: list[RankedSlot] = []
    for item in recommendations:
        if not isinstance(item, dict):
            LOGGER.debug("Skipping non-object recommendation: %s", item)
            continue
        slot_id = item.get("slot_id")
        rationale = item.get("rationale", "")
        score = item.get("score")

        if not isinstance(slot_id, int):
            LOGGER.debug("Skipping recommendation without integer slot_id: %s", item)
            continue
        if score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                LOGGER.debug("Score for slot %s is not numeric: %s", slot_id, score)
                score = None
        if not isinstance(rationale, str):
            rationale = ""

        ranked_slots.append(RankedSlot(slot_id=slot_id, score=score, rationale=rationale.strip()))

    if not ranked_slots:
        raise LLMRankingError("No valid recommendations were returned by the LLM.")

    return ranked_slots


def rank_slots_with_llm(
    *,
    slots: list[dict[str, Any]],
    prompt_template: str,
    context: dict[str, Any],
) -> list[RankedSlot]:
    """Render the prompt, send it to the LLM, and parse the ranking results."""

    slot_lines = []
    for slot in slots:
        specialty_info = ""
        if slot.get("doctor_specialty"):
            specialty_info = f" (Specialty: {slot['doctor_specialty']})"

        line = (
            f"- slot_id: {slot['slot_id']} | "
            f"doctor_id: {slot['doctor_id']}{specialty_info} | "
            f"room_id: {slot['room_id']} | start: {slot['start_time']} | "
            f"end: {slot['end_time']}"
        )
        slot_lines.append(line)
    slot_listing = "\n".join(slot_lines)
    prompt = render_prompt(
        prompt_template=prompt_template,
        slot_listing=slot_listing,
        context=context,
    )

    response_data = call_llm(prompt)
    output_text = response_data.get("response")
    if not isinstance(output_text, str):  # pragma: no cover - defensive
        raise LLMRankingError("LLM response payload did not include text output.")

    return parse_llm_response(output_text)