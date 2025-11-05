import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiFetchWithBody } from "../utils/api";
import { useAuth } from "../context/AuthContext";
import { Doctor, Room } from "../types";

export function ClinicDashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [newDoctorName, setNewDoctorName] = useState("");
  const [newDoctorSpecialty, setNewDoctorSpecialty] = useState("");

  const [newRoomName, setNewRoomName] = useState("");
  const [newRoomType, setNewRoomType] = useState("");

  const {
    data: clinicData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["clinicData", user?.clinicId],
    queryFn: () => apiFetch(`/api/clinic/details`),
    enabled: !!user?.clinicId,
  });

  const addDoctorMutation = useMutation({
    mutationFn: (newDoctor: Partial<Doctor>) =>
      apiFetchWithBody(`/api/clinic/doctors`, "POST", newDoctor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinicData"] });
      setNewDoctorName("");
      setNewDoctorSpecialty("");
    },
  });

  const addRoomMutation = useMutation({
    mutationFn: (newRoom: Partial<Room>) =>
      apiFetchWithBody(`/api/clinic/rooms`, "POST", newRoom),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clinicData"] });
      setNewRoomName("");
      setNewRoomType("");
    },
  });

  const handleAddDoctor = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDoctorName) return;
    addDoctorMutation.mutate({
      full_name: newDoctorName,
      specialty: newDoctorSpecialty,
    });
  };

  const handleAddRoom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoomName || !newRoomType) return;
    addRoomMutation.mutate({ name: newRoomName, room_type: newRoomType });
  };

  if (isLoading) return <div>Loading clinic data...</div>;
  if (isError) return <div>Error loading clinic data.</div>;

  const { doctors = [], rooms = [] } = clinicData || {};

  return (
    <main className="content">
      <div className="card">
        <h2>Clinic Dashboard</h2>
        <p>Manage your clinic's doctors and rooms.</p>
      </div>

      <div className="card-container">
        <div className="card">
          <h3>Manage Doctors</h3>
          <form onSubmit={handleAddDoctor}>
            <input
              type="text"
              value={newDoctorName}
              onChange={(e) => setNewDoctorName(e.target.value)}
              placeholder="Doctor's full name"
            />
            <input
              type="text"
              value={newDoctorSpecialty}
              onChange={(e) => setNewDoctorSpecialty(e.target.value)}
              placeholder="Specialty (e.g., Surgery)"
            />
            <button type="submit" disabled={addDoctorMutation.isPending}>
              {addDoctorMutation.isPending ? "Adding..." : "Add Doctor"}
            </button>
          </form>
          <h4>Current Doctors</h4>
          <ul>
            {doctors.map((doc: Doctor) => (
              <li key={doc.id}>
                {doc.full_name} {doc.specialty && `(${doc.specialty})`}
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>Manage Rooms</h3>
          <form onSubmit={handleAddRoom}>
            <input
              type="text"
              value={newRoomName}
              onChange={(e) => setNewRoomName(e.target.value)}
              placeholder="Room name (e.g., Exam 1)"
            />
            <input
              type="text"
              value={newRoomType}
              onChange={(e) => setNewRoomType(e.target.value)}
              placeholder="Room type (e.g., exam, surgery)"
            />
            <button type="submit" disabled={addRoomMutation.isPending}>
              {addRoomMutation.isPending ? "Adding..." : "Add Room"}
            </button>
          </form>
          <h4>Current Rooms</h4>
          <ul>
            {rooms.map((room: Room) => (
              <li key={room.id}>
                {room.name} ({room.room_type})
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  );
}