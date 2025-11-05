import { NavLink, Outlet } from "react-router-dom";

export function ClientLayout() {
  return (
    <div className="client-layout">
      <header className="top-nav">
        <div className="nav-container">
          <h1>Interpaws</h1>
          <nav>
            <NavLink to="/client/booking">Book Appointment</NavLink>
            <NavLink to="/client/history">My History</NavLink>
            <NavLink to="/client/login">Login</NavLink>
          </nav>
        </div>
      </header>
      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}