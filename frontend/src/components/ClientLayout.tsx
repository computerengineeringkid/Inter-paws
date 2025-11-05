import { Outlet } from "react-router-dom";

function ClientLayout() {
  return (
    <div className="client-layout">
      <header className="top-nav">
        <div className="nav-container">
          <h1>Inter-Paws</h1>
          <nav>
            <a href="/client/booking">Book Appointment</a>
            <a href="/client/history">My History</a>
            <a href="/client/login">Login</a>
          </nav>
        </div>
      </header>
      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}

export default ClientLayout;