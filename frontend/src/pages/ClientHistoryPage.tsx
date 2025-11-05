import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface AppointmentRecord {
  id: number;
  start_time: string;
  end_time: string;
  status: string;
  doctor?: { id: number; display_name: string | null } | null;
  room?: { id: number; name: string | null } | null;
  pet?: { id: number; name: string | null } | null;
  reason?: string | null;
}

interface HistoryResponse {
  appointments: AppointmentRecord[];
}

function ClientHistoryPage() {
  const { token, profile, logout } = useAuth();
  const historyQuery = useQuery({
    queryKey: ["visit-history"],
    queryFn: async () => {
      const response = await apiFetch<HistoryResponse>("/schedule/history", {
        method: "GET",
        token,
      });
      return response.appointments || [];
    },
  });

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <h2>Client Hub</h2>
        <a href="/client/booking">Book appointment</a>
        <a href="/client/history">Visit history</a>
        <a href="/clinic/login">Clinic sign-in</a>
        <button className="secondary" style={{ marginTop: "2rem" }} onClick={logout}>
          Sign out
        </button>
      </aside>
      <main className="content">
        <div className="card">
          <h1>Visit history</h1>
          <p style={{ color: "#4b5563" }}>Track past and upcoming visits associated with {profile?.full_name ?? "your account"}.</p>
        </div>
        <div className="card">
          {historyQuery.isLoading ? <p>Loading visits...</p> : null}
          {historyQuery.isError ? (
            <div className="alert error" role="alert">
              Unable to load visit history. Try refreshing the page.
            </div>
          ) : null}
          {!historyQuery.isLoading && historyQuery.data?.length === 0 ? (
            <p>No visits found yet. Start by booking an appointment.</p>
          ) : null}
          {historyQuery.data && historyQuery.data.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Pet</th>
                  <th>Doctor</th>
                  <th>Room</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {historyQuery.data.map((appointment) => (
                  <tr key={appointment.id}>
                    <td>{new Date(appointment.start_time).toLocaleString()}</td>
                    <td>{appointment.pet?.name ?? "Unknown"}</td>
                    <td>{appointment.doctor?.display_name ?? "TBD"}</td>
                    <td>{appointment.room?.name ?? "TBD"}</td>
                    <td>
                      <span className="badge">{appointment.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      </main>
    </div>
  );
}

export default ClientHistoryPage;
