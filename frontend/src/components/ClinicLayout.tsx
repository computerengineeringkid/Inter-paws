import { Outlet } from "react-router-dom";

function ClinicLayout() {
  return (
    <div className="main-layout">
      <aside className="sidebar">
        <h2>Inter-Paws Clinic</h2>
        <nav>
          <a href="/clinic/dashboard">Dashboard</a>
          <a href="/clinic/schedule">Schedule</a>
          <a href="/clinic/patients">Patients</a>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

export default ClinicLayout;