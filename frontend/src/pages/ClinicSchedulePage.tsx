import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { Appointment } from "../types.ts";

export function ClinicSchedulePage() {
  const {
    data: schedule,
    isLoading,
    isError,
  } = useQuery<Appointment[]>({
    queryKey: ["clinicSchedule"],
    queryFn: () => apiFetch("/api/clinic/schedule"),
  });

  if (isLoading) return <div>Loading schedule...</div>;
  if (isError) return <div>Error loading schedule.</div>;

  return (
    <main className="content">
      <div className="card">
        <h2>Clinic Schedule</h2>
        <p>View upcoming appointments for your clinic.</p>
      </div>
      <div className="card-container">
        <div className="card">
          <h3>Upcoming Appointments</h3>
          {schedule && schedule.length > 0 ? (
            <ul>
              {schedule.map((appt) => (
                <li key={appt.id}>
                  <strong>
                    {new Date(appt.start_time).toLocaleString()} -{" "}
                    {new Date(appt.end_time).toLocaleTimeString()}
                  </strong>
                  <br />
                  Pet: {appt.pet_name || "N/A"} (Owner:{" "}
                  {appt.user_email || "N/A"})
                  <br />
                  Doctor: {appt.doctor_name || "N/A"} | Room:{" "}
                  {appt.room_name || "N/A"}
                  <br />
                  Reason: {appt.reason_for_visit}
                </li>
              ))}
            </ul>
          ) : (
            <p>No upcoming appointments found.</p>
          )}
        </div>
      </div>
    </main>
  );
}