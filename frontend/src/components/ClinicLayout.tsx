import { NavLink, Outlet } from "react-router-dom";

export function ClinicLayout() {
  return (
    <div className="main-layout">
      <aside className="sidebar">
        <h2>Inter-Paws Clinic</h2>
        <nav>
          <NavLink to="/clinic/dashboard">Dashboard</NavLink>
          <NavLink to="/clinic/schedule">Schedule</NavLink>
          <NavLink to="/clinic/patients">Patients</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}