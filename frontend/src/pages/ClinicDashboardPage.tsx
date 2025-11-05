import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface DoctorPayload {
  id: number;
  display_name: string;
  specialty?: string | null;
  license_number?: string | null;
  biography?: string | null;
  is_active: boolean;
}

interface EquipmentPayload {
  id: string;
  name: string;
  notes?: string | null;
}

interface RoomPayload {
  id: number;
  name: string;
  room_type?: string | null;
  capacity?: number | null;
  notes?: string | null;
  is_active: boolean;
  equipment: EquipmentPayload[];
}

interface ClinicResourcesResponse {
  doctors: DoctorPayload[];
  rooms: RoomPayload[];
}

interface DoctorForm {
  display_name: string;
  specialty?: string;
  license_number?: string;
}

interface RoomForm {
  name: string;
  room_type?: string;
  capacity?: number | null;
}

interface EquipmentForm {
  room_id: number;
  name: string;
  notes?: string;
}

function ClinicDashboardPage() {
  const { token, logout } = useAuth();
  const resourcesQuery = useQuery({
    queryKey: ["clinic-resources"],
    queryFn: async () => {
      const response = await apiFetch<ClinicResourcesResponse>("/clinic/resources", {
        method: "GET",
        token,
      });
      return response;
    },
  });

  const doctorForm = useForm<DoctorForm>({ defaultValues: { display_name: "", specialty: "" } });
  const roomForm = useForm<RoomForm>({ defaultValues: { name: "", room_type: "exam" } });
  const equipmentForm = useForm<EquipmentForm>({ defaultValues: { name: "", room_id: 0 } });

  const invalidate = () => resourcesQuery.refetch();

  const addDoctor = useMutation({
    mutationFn: async (values: DoctorForm) =>
      apiFetch("/clinic/doctors", {
        method: "POST",
        token,
        body: JSON.stringify(values),
      }),
    onSuccess: () => {
      doctorForm.reset({ display_name: "", specialty: "", license_number: "" });
      invalidate();
    },
  });

  const deleteDoctor = useMutation({
    mutationFn: async (doctorId: number) =>
      apiFetch(`/clinic/doctors/${doctorId}`, {
        method: "DELETE",
        token,
      }),
    onSuccess: () => invalidate(),
  });

  const addRoom = useMutation({
    mutationFn: async (values: RoomForm) =>
      apiFetch("/clinic/rooms", {
        method: "POST",
        token,
        body: JSON.stringify(values),
      }),
    onSuccess: () => {
      roomForm.reset({ name: "", room_type: "exam", capacity: null });
      invalidate();
    },
  });

  const deleteRoom = useMutation({
    mutationFn: async (roomId: number) =>
      apiFetch(`/clinic/rooms/${roomId}`, {
        method: "DELETE",
        token,
      }),
    onSuccess: () => invalidate(),
  });

  const addEquipment = useMutation({
    mutationFn: async (values: EquipmentForm) =>
      apiFetch(`/clinic/rooms/${values.room_id}/equipment`, {
        method: "POST",
        token,
        body: JSON.stringify({ name: values.name, notes: values.notes }),
      }),
    onSuccess: () => {
      equipmentForm.reset({ name: "", room_id: defaultRoomId, notes: "" });
      invalidate();
    },
  });

  const deleteEquipment = useMutation({
    mutationFn: async ({ room_id, equipment_id }: { room_id: number; equipment_id: string }) =>
      apiFetch(`/clinic/rooms/${room_id}/equipment/${equipment_id}`, {
        method: "DELETE",
        token,
      }),
    onSuccess: () => invalidate(),
  });

  const rooms = resourcesQuery.data?.rooms ?? [];
  const defaultRoomId = useMemo(() => rooms[0]?.id ?? 0, [rooms]);

  useEffect(() => {
    if (defaultRoomId) {
      equipmentForm.setValue("room_id", defaultRoomId);
    }
  }, [defaultRoomId, equipmentForm]);

  return (
    <>
    <div className="card">
      <h1>Operational overview</h1>
      <p style={{ color: "#4b5563" }}>
        Manage practitioners, rooms, and equipment to keep your clinic running smoothly. Changes are synced instantly with scheduling suggestions.
      </p>
    </div>
    <div className="card">
      <h2>Add doctor</h2>
      <form
        className="form-grid two-column"
        aria-label="Add doctor"
        onSubmit={doctorForm.handleSubmit(async (values) => {
          await addDoctor.mutateAsync(values);
        })}
      >
        <label>
          <span>Display name</span>
          <input type="text" {...doctorForm.register("display_name", { required: true })} />
        </label>
        <label>
          <span>Specialty</span>
          <input type="text" {...doctorForm.register("specialty")} />
        </label>
        <label>
          <span>License</span>
          <input type="text" {...doctorForm.register("license_number")} />
        </label>
        <div style={{ alignSelf: "flex-end" }}>
          <button className="primary" type="submit" disabled={addDoctor.isPending}>
            {addDoctor.isPending ? "Saving..." : "Add doctor"}
          </button>
        </div>
      </form>
    </div>
    <div className="card">
      <h2>Doctors</h2>
      {resourcesQuery.isLoading ? <p>Loading doctors...</p> : null}
      {resourcesQuery.data?.doctors?.length ? (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Specialty</th>
              <th>License</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {resourcesQuery.data.doctors.map((doctor) => (
              <tr key={doctor.id}>
                <td>{doctor.display_name}</td>
                <td>{doctor.specialty ?? "—"}</td>
                <td>{doctor.license_number ?? "—"}</td>
                <td>
                  <button className="secondary" onClick={() => deleteDoctor.mutateAsync(doctor.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No doctors configured yet.</p>
      )}
    </div>
    <div className="card">
      <h2>Add room</h2>
      <form
        className="form-grid two-column"
        aria-label="Add room"
        onSubmit={roomForm.handleSubmit(async (values) => {
          await addRoom.mutateAsync(values);
        })}
      >
        <label>
          <span>Name</span>
          <input type="text" {...roomForm.register("name", { required: true })} />
        </label>
        <label>
          <span>Type</span>
          <input type="text" {...roomForm.register("room_type")} />
        </label>
        <label>
          <span>Capacity</span>
          <input type="number" {...roomForm.register("capacity", { valueAsNumber: true })} />
        </label>
        <div style={{ alignSelf: "flex-end" }}>
          <button className="primary" type="submit" disabled={addRoom.isPending}>
            {addRoom.isPending ? "Saving..." : "Add room"}
          </button>
        </div>
      </form>
    </div>
    <div className="card">
      <h2>Rooms & equipment</h2>
      {rooms.length === 0 ? <p>No rooms configured yet.</p> : null}
      {rooms.map((room) => (
        <div key={room.id} style={{ marginBottom: "1.5rem" }}>
          <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
            <div>
              <h3 style={{ marginBottom: "0.25rem" }}>{room.name}</h3>
              <p style={{ color: "#4b5563", margin: 0 }}>
                {room.room_type ?? "Unspecified"} &middot; Capacity {room.capacity ?? "N/A"}
              </p>
            </div>
            <button className="secondary" onClick={() => deleteRoom.mutateAsync(room.id)}>
              Remove room
            </button>
          </div>
          <ul>
            {room.equipment.map((item) => (
              <li key={item.id} style={{ marginBottom: "0.5rem" }}>
                <strong>{item.name}</strong>
                {item.notes ? <span style={{ color: "#4b5563" }}> — {item.notes}</span> : null}
                <button
                  className="secondary"
                  style={{ marginLeft: "1rem" }}
                  onClick={() => deleteEquipment.mutateAsync({ room_id: room.id, equipment_id: item.id })}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {rooms.length > 0 ? (
        <form
          className="form-grid two-column"
          aria-label="Add equipment"
          onSubmit={equipmentForm.handleSubmit(async (values) => {
            const targetRoom = values.room_id || defaultRoomId;
            await addEquipment.mutateAsync({ ...values, room_id: targetRoom });
          })}
        >
          <label>
            <span>Room</span>
            <select {...equipmentForm.register("room_id", { valueAsNumber: true })} defaultValue={defaultRoomId}>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Equipment name</span>
            <input type="text" {...equipmentForm.register("name", { required: true })} />
          </label>
          <label>
            <span>Notes</span>
            <input type="text" {...equipmentForm.register("notes")} />
          </label>
          <div style={{ alignSelf: "flex-end" }}>
            <button className="primary" type="submit" disabled={addEquipment.isPending}>
              {addEquipment.isPending ? "Saving..." : "Add equipment"}
            </button>
          </div>
        </form>
      ) : null}
    </div>
    </>
  );
}

export default ClinicDashboardPage;
