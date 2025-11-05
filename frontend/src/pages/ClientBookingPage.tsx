import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useMutation }_from "@tanstack/react-query";
import { apiFetchWithBody } from "../utils/api";
import { RecommendedSlot, AppointmentRequest } from "../types";

export function ClientBookingPage() {
  const { user } = useAuth();
  const [reason, setReason] = useState("");
  const [urgency, setUrgency] = useState("routine");
  const [selectedPetId, setSelectedPetId] = useState("");
  const [newPetName, setNewPetName] = useState("");
  const [newPetSpecies, setNewPetSpecies] = useState("");
  const [newPetBreed, setNewPetBreed] = useState("");
  const [newPetBirthDate, setNewPetBirthDate] = useState("");

  const [recommendations, setRecommendations] = useState<RecommendedSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<RecommendedSlot | null>(
    null
  );

  const {
    mutate: findSlots,
    isPending: isFindingSlots,
    isError: findError,
  } = useMutation<RecommendedSlot[], Error, AppointmentRequest>({
    mutationFn: (request) =>
      apiFetchWithBody("/api/scheduler/recommendations", "POST", request),
    onSuccess: (data) => {
      setRecommendations(data);
      setSelectedSlot(null);
    },
  });

  const {
    mutate: bookSlot,
    isPending: isBooking,
    isSuccess: isBooked,
    error: bookError,
  } = useMutation<unknown, Error, { slot: RecommendedSlot; feedbackRank: number }>({
    mutationFn: ({ slot, feedbackRank }) =>
      apiFetchWithBody("/api/scheduler/book", "POST", {
        doctor_id: slot.doctor_id,
        room_id: slot.room_id,
        start_time: slot.start_time,
        end_time: slot.end_time,
        pet_id: selectedPetId === "new" ? null : parseInt(selectedPetId),
        pet_name: selectedPetId === "new" ? newPetName : undefined,
        pet_species: selectedPetId === "new" ? newPetSpecies : undefined,
        pet_breed: selectedPetId === "new" ? newPetBreed : undefined,
        pet_birth_date: selectedPetId === "new" ? newPetBirthDate : undefined,
        reason_for_visit: reason,
        feedback_rank_selection: feedbackRank,
      }),
    onSuccess: ()ax => {
      setRecommendations([]);
      setSelectedSlot(null);
      // In a real app, you'd probably refetch user's pets or appointments
    },
  });

  const handleFindSlots = (e: React.FormEvent) => {
    e.preventDefault();
    const startDate = new Date();
    const endDate = new Date();
    endDate.setDate(startDate.getDate() + 14); // Look 2 weeks out

    findSlots({
      start: startDate.toISOString(),
      end: endDate.toISOString(),
      duration_minutes: 30,
      reason_for_visit: reason,
      urgency,
    });
  };

  const handleBookSlot = (slot: RecommendedSlot, rank: number) => {
    setSelectedSlot(slot);
    bookSlot({ slot, feedbackRank: rank });
  };

  const petList = user?.pets || [];

  return (
    <main className="content">
      <div className="card">
        <h2>Book an Appointment</h2>
        <p>Find and book the best time for your pet's needs.</p>
      </div>

      <div className="card-container">
        <div className="card">
          <h3>1. Select Pet</h3>
          <select
            value={selectedPetId}
            onChange={(e) => setSelectedPetId(e.target.value)}
          >
            <option value="">-- Select a pet --</option>
            {petList.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.name} ({pet.species})
              </option>
            ))}
            <option value="new">-- Add a new pet --</option>
          </select>

          {selectedPetId === "new" && (
            <div className="new-pet-form">
              <input
                type="text"
                value={newPetName}
                onChange={(e) => setNewPetName(e.target.value)}
                placeholder="Pet's Name"
              />
              <input
                type="text"
                value={newPetSpecies}
                onChange={(e) => setNewPetSpecies(e.target.value)}
                placeholder="Species (e.g., Dog, Cat)"
              />
              <input
                type="text"
                value={newPetBreed}
                onChange={(e) => setNewPetBreed(e.target.value)}
                placeholder="Breed"
              />
              <input
                type="date"
                value={newPetBirthDate}
                onChange={(e) => setNewPetBirthDate(e.target.value)}
                placeholder="Birth Date"
              />
            </div>
          )}
        </div>

        <div className="card">
          <h3>2. Reason for Visit</h3>
          <form onSubmit={handleFindSlots}>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for visit (e.g., Checkup, Limping)"
              required
            />
            <select
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
            >
              <option value="routine">Routine</option>
              <option value="urgent">Urgent</option>
              <option value="emergency">Emergency</option>
            </select>
            <button
              type="submit"
              disabled={
                !selectedPetId || (selectedPetId === "new" && !newPetName)
              }
            >
              {isFindingSlots ? "Finding..." : "Find Available Slots"}
            </button>
            {findError && (
              <p className="error">Error finding slots. Please try again.</p>
            )}
          </form>
        </div>

        <div className="card">
          <h3>3. Choose a Recommended Slot</h3>
          {isFindingSlots && <p>Loading recommendations...</p>}
          {recommendations.length > 0 && (
            <ul className="recommendation-list">
              {recommendations.map((slot) => (
                <li key={slot.start_time}>
                  <div className="slot-info">
                    <strong>
                      {new Date(slot.start_time).toLocaleString()}
                    </strong>
                    <p>{slot.rationale}</p>
                  </div>
                  <button
                    onClick={() => handleBookSlot(slot, slot.rank)}
                    disabled={isBooking}
                  >
                    Book
                  </button>
                </li>
              ))}
            </ul>
          )}
          {isBooked && (
            <p className="success">Appointment booked successfully!</p>
          )}
          {bookError && (
            <p className="error">
              Failed to book slot: {bookError.message}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}