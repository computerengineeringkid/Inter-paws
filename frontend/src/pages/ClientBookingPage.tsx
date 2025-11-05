import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import { addMinutes, format } from "date-fns";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface SlotSearchForm {
  clinic_id: number;
  reason_for_visit: string;
  urgency: string;
  start: string;
  end: string;
  duration_minutes: number;
  pet_name: string;
}

interface RankedSuggestion {
  doctor_id: number | null;
  room_id: number | null;
  start_time: string;
  end_time: string;
  rank: number;
  score: number | null;
  rationale: string;
}

interface SlotSearchResponse {
  suggestions: RankedSuggestion[];
}

function ClientBookingPage() {
  const { token, profile, logout } = useAuth();
  const defaultStart = useMemo(() => new Date(), []);
  const defaultEnd = useMemo(() => addMinutes(new Date(), 60 * 24 * 7), []);
  const form = useForm<SlotSearchForm>({
    defaultValues: {
      clinic_id: profile?.clinic_id ?? 1,
      reason_for_visit: "Wellness exam",
      urgency: "routine",
      start: format(defaultStart, "yyyy-MM-dd'T'HH:mm"),
      end: format(defaultEnd, "yyyy-MM-dd'T'HH:mm"),
      duration_minutes: 30,
      pet_name: "", 
    },
  });
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState<RankedSuggestion | null>(null);
  const [suggestions, setSuggestions] = useState<RankedSuggestion[]>([]);

  useEffect(() => {
    if (profile?.clinic_id) {
      form.setValue("clinic_id", profile.clinic_id);
    }
  }, [profile?.clinic_id, form]);

  const findSlots = useMutation({
    mutationFn: async (values: SlotSearchForm) => {
      const payload = {
        clinic_id: values.clinic_id,
        reason_for_visit: values.reason_for_visit,
        urgency: values.urgency,
        start: new Date(values.start).toISOString(),
        end: new Date(values.end).toISOString(),
        duration_minutes: values.duration_minutes,
      };
      const response = await apiFetch<SlotSearchResponse>("/schedule/find-slots", {
        method: "POST",
        body: JSON.stringify(payload),
        token,
      });
      return response.suggestions || [];
    },
    onSuccess: (slots) => {
      setSuggestions(slots);
      setSelectedSuggestion(slots[0] ?? null);
    },
    onError: (error: any) => {
      const message = error?.data?.message ?? "Unable to find appointment slots.";
      setErrorMessage(message);
    },
  });

  const book = useMutation({
    mutationFn: async () => {
      if (!selectedSuggestion) {
        throw new Error("Select a suggestion to continue");
      }
      const values = form.getValues();
      const response = await apiFetch<{ message: string }>("/schedule/book", {
        method: "POST",
        body: JSON.stringify({
          clinic_id: values.clinic_id,
          suggestion: selectedSuggestion,
          owner_name: profile?.full_name ?? "",
          owner_email: profile?.email ?? "",
          pet_name: values.pet_name,
          reason: values.reason_for_visit,
        }),
        token,
      });
      return response;
    },
    onSuccess: (payload) => {
      setSuccessMessage(payload.message ?? "Appointment booked successfully.");
      setSuggestions([]);
      setSelectedSuggestion(null);
    },
    onError: (error: any) => {
      const message = error?.data?.message ?? "Unable to complete the booking.";
      setErrorMessage(message);
    },
  });

  return (
    <>
    <div className="card">
      <h1>Find the perfect time for {profile?.full_name ?? "your pet"}</h1>
      <p style={{ color: "#4b5563" }}>
        Tell us what you need and Inter-Paws will curate recommended appointment windows across your clinic.
      </p>
      {errorMessage ? (
        <div className="alert error" role="alert">
          {errorMessage}
        </div>
      ) : null}
      {successMessage ? (
        <div className="alert success" role="status">
          {successMessage}
        </div>
      ) : null}
      <form
        className="form-grid two-column"
        onSubmit={form.handleSubmit(async (values) => {
          setErrorMessage(null);
          setSuccessMessage(null);
          await findSlots.mutateAsync(values);
        })}
      >
        <label>
          <span>Clinic ID</span>
          <input type="number" {...form.register("clinic_id", { valueAsNumber: true, required: true })} />
        </label>
        <label>
          <span>Pet name</span>
          <input type="text" {...form.register("pet_name", { required: true })} placeholder="Luna" />
        </label>
        <label>
          <span>Reason for visit</span>
          <input type="text" {...form.register("reason_for_visit", { required: true })} placeholder="Annual vaccines" />
        </label>
        <label>
          <span>Urgency</span>
          <select {...form.register("urgency")}> 
            <option value="routine">Routine</option>
            <option value="urgent">Urgent</option>
            <option value="follow-up">Follow-up</option>
          </select>
        </label>
        <label>
          <span>Search start (ISO)</span>
          <input type="datetime-local" {...form.register("start", { required: true })} />
        </label>
        <label>
          <span>Search end (ISO)</span>
          <input type="datetime-local" {...form.register("end", { required: true })} />
        </label>
        <label>
          <span>Duration (minutes)</span>
          <input type="number" {...form.register("duration_minutes", { valueAsNumber: true, required: true })} />
        </label>
        <div style={{ alignSelf: "flex-end" }}>
          <button className="primary" type="submit" disabled={findSlots.isPending}>
            {findSlots.isPending ? "Analyzing availability..." : "Search suggestions"}
          </button>
        </div>
      </form>
    </div>
    {suggestions.length > 0 ? (
      <div className="card">
        <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
          <div>
            <h2>Recommended slots</h2>
            <p style={{ color: "#4b5563", margin: 0 }}>
              Choose the time that works best. Each suggestion includes context from our scheduling assistant.
            </p>
          </div>
          <button className="primary" onClick={() => book.mutateAsync()} disabled={!selectedSuggestion || book.isPending}>
            {book.isPending ? "Booking..." : "Book selected slot"}
          </button>
        </div>
        <div className="schedule-grid" style={{ marginTop: "1.5rem" }}>
          {suggestions.map((slot) => {
            const isSelected = selectedSuggestion?.start_time === slot.start_time;
            return (
              <button
                key={`${slot.start_time}-${slot.rank}`}
                type="button"
                className="schedule-card"
                onClick={() => setSelectedSuggestion(slot)}
                style={{
                  borderColor: isSelected ? "#2563eb" : undefined,
                  boxShadow: isSelected ? "0 0 0 2px rgba(37, 99, 235, 0.35)" : undefined,
                  textAlign: "left",
                }}
              >
                <div className="badge">Rank {slot.rank}</div>
                <h3 style={{ marginBottom: "0.5rem" }}>{new Date(slot.start_time).toLocaleString()}</h3>
                <p style={{ color: "#4b5563", marginTop: 0 }}>
                  Ends at {new Date(slot.end_time).toLocaleTimeString()} &middot; Score {slot.score?.toFixed(2) ?? "N/A"}
                </p>
                <p style={{ marginTop: "0.75rem", color: "#1f2937" }}>{slot.rationale}</p>
              </button>
            );
          })}
        </div>
      </div>
    ) : null}
    </>
  );
}

export default ClientBookingPage;
