import { Navigate, Route, Routes } from "react-router-dom";
import ClientBookingPage from "./pages/ClientBookingPage";
import ClientHistoryPage from "./pages/ClientHistoryPage";
import ClientLoginPage from "./pages/ClientLoginPage";
import ClientRegisterPage from "./pages/ClientRegisterPage";
import ClinicDashboardPage from "./pages/ClinicDashboardPage";
import ClinicSchedulePage from "./pages/ClinicSchedulePage";
import ClinicOnboardingPage from "./pages/ClinicOnboardingPage";
import ClinicPatientPage from "./pages/ClinicPatientPage";
import { ProtectedRoute } from "./components/ProtectedRoute";
import ClientLayout from "./components/ClientLayout";
import ClinicLayout from "./components/ClinicLayout";
import { useAuth } from "./context/AuthContext";

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/" element={<ClientLayout />}>
        <Route index element={<Navigate to="client/booking" replace />} />
        <Route path="client/login" element={<ClientLoginPage />} />
        <Route path="client/register" element={<ClientRegisterPage />} />
        <Route
          path="client/booking"
          element={
            <ProtectedRoute fallback="/client/login">
              <ClientBookingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="client/history"
          element={
            <ProtectedRoute fallback="/client/login">
              <ClientHistoryPage />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route
        path="/clinic"
        element={
          <ProtectedRoute fallback="/clinic/login" requireAdmin>
            <ClinicLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<ClinicDashboardPage />} />
        <Route path="schedule" element={<ClinicSchedulePage />} />
        <Route path="patients" element={<ClinicPatientPage />} />
      </Route>

      <Route path="/clinic/login" element={<ClientLoginPage mode="clinic" />} />

      <Route
        path="/onboarding"
        element={
          <ProtectedRoute fallback="/clinic/login" requireAdmin>
            <ClinicOnboardingPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinic/onboarding"
        element={
          <ProtectedRoute fallback="/clinic/login" requireAdmin>
            <ClinicOnboardingPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? "/client/booking" : "/client/login"} replace />}
      />
    </Routes>
  );
}

export default App;