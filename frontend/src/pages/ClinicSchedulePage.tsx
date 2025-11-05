import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, startOfDay } from "date-fns";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface ScheduleAppointment {
  id: number;
  start_time: string;
  end_time: string;
  doctor_name?: string | null;
  room_name?: string | null;
  pet_name?: string | null;
  owner_name?: string | null;
  status: string;
  reason?: string | null;
}

interface ScheduleResponse {
  appointments: ScheduleAppointment[];
}

function groupByDay(appointments: ScheduleAppointment[]) {
  const buckets: Record<string, ScheduleAppointment[]> = {};
  appointments.forEach((appt) => {
    const key = format(new Date(appt.start_time), "yyyy-MM-dd");
    buckets[key] = buckets[key] ?? [];
    buckets[key].push(appt);
  });
  return buckets;
}

function ClinicSchedulePage() {
  const { token, logout } = useAuth();
  const [view, setView] = useState<"day" | "week">("week");
  const [start, setStart] = useState(() => format(startOfDay(new Date()), "yyyy-MM-dd"));

  const scheduleQuery = useQuery({
    queryKey: ["clinic-schedule", view, start],
    queryFn: async () => {
      const response = await apiFetch<ScheduleResponse>(`/clinic/schedule?view=${view}&start=${start}`, {
        method: "GET",
        token,
      });
      return response.appointments || [];
    },
  });

  const grouped = useMemo(() => groupByDay(scheduleQuery.data ?? []), [scheduleQuery.data]);
  const orderedDays = useMemo(() => Object.keys(grouped).sort(), [grouped]);

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <h2>Clinic HQ</h2>
        <a href="/clinic/dashboard">Dashboard</a>
        <a href="/clinic/schedule">Schedule</a>
        <a href="/clinic/patients">Patients</a>
        <a href="/clinic/onboarding">Onboarding</a>
        <button className="secondary" style={{ marginTop: "2rem" }} onClick={logout}>
          Sign out
        </button>
      </aside>
      <main className="content">
        <div className="card">
          <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
            <div>
              <h1>Live schedule board</h1>
              <p style={{ color: "#4b5563", margin: 0 }}>
                Monitor upcoming appointments and resource usage across your clinic.
              </p>
            </div>
            <div className="stack horizontal" style={{ gap: "0.5rem" }}>
              <nav className="tabs">
                <button className={view === "day" ? "active" : ""} onClick={() => setView("day")}>
                  Day
                </button>
                <button className={view === "week" ? "active" : ""} onClick={() => setView("week")}>
                  Week
                </button>
              </nav>
              <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
            </div>
          </div>
        </div>
        <div className="card">
          {scheduleQuery.isLoading ? <p>Loading schedule...</p> : null}
          {scheduleQuery.isError ? (
            <div className="alert error" role="alert">
              Unable to load the clinic schedule. Try refreshing the page.
            </div>
          ) : null}
          {orderedDays.length === 0 && !scheduleQuery.isLoading ? (
            <p>No appointments scheduled during this window.</p>
          ) : null}
          <div className="schedule-grid">
            {orderedDays.map((day) => (
              <div key={day} className="schedule-card">
                <h3>{format(new Date(day), "EEEE, MMM d")}</h3>
                <ul style={{ paddingLeft: "1.25rem" }}>
                  {grouped[day].map((appointment) => (
                    <li key={appointment.id} style={{ marginBottom: "1rem" }}>
                      <strong>{new Date(appointment.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong>
                      <span style={{ color: "#4b5563" }}>
                        {" "}- {appointment.pet_name ?? "Unassigned"} ({appointment.owner_name ?? "owner"})
                      </span>
                      <div style={{ color: "#4b5563" }}>
                        {appointment.doctor_name ?? "Any doctor"} &middot; {appointment.room_name ?? "Room TBD"}
                      </div>
                      <div>
                        <span className="badge">{appointment.status}</span>
                        {appointment.reason ? <span style={{ marginLeft: "0.5rem" }}>{appointment.reason}</span> : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

export default ClinicSchedulePage;
