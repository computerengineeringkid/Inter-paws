import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { Appointment } from "../types.ts";

export function ClientHistoryPage() {
  const {
    data: history,
    isLoading,
    isError,
  } = useQuery<Appointment[]>({
    queryKey: ["clientHistory"],
    queryFn: () => apiFetch("/api/scheduler/history"),
  });

  if (isLoading) return <div>Loading appointment history...</div>;
  if (isError) return <div>Error loading history.</div>;

  return (
    <main className="content">
      <div className="card">
        <h2>My Appointment History</h2>
        <p>View your past and upcoming appointments.</p>
      </div>
      <div className="card-container">
        <div className="card">
          <h3>Appointments</h3>
          {history && history.length > 0 ? (
            <ul>
              {history.map((appt) => (
                <li key={appt.id}>
                  <strong>
                    {new Date(appt.start_time).toLocaleString()}
                  </strong>
                  <br />
                  Pet: {appt.pet_name || "N/A"}
                  <br />
                  Doctor: {appt.doctor_name || "N/A"} | Room:{" "}
                  {appt.room_name || "N/A"}
                  <br />
                  Reason: {appt.reason_for_visit}
                </li>
              ))}
            </ul>
          ) : (
            <p>No appointments found.</p>
          )}
        </div>
      </div>
    </main>
  );
}