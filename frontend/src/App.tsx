// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Layouts
import { ClinicLayout } from "./components/ClinicLayout";
import { ClientLayout } from "./components/ClientLayout";

// Client Pages (Using named imports)
import { ClientLoginPage } from "./pages/ClientLoginPage";
import { ClientRegisterPage } from "./pages/ClientRegisterPage";
import { ClientBookingPage } from "./pages/ClientBookingPage";
import { ClientHistoryPage } from "./pages/ClientHistoryPage";

// Clinic Pages (Using named imports)
import { ClinicOnboardingPage } from "./pages/ClinicOnboardingPage";
import { ClinicDashboardPage } from "./pages/ClinicDashboardPage";
import { ClinicSchedulePage } from "./pages/ClinicSchedulePage";
import { ClinicPatientPage } from "./pages/ClinicPatientPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* === Client Routes === */}
            <Route path="/" element={<ClientLayout />}>
              <Route index element={<Navigate to="/client/login" replace />} />
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

            {/* === Clinic Routes === */}
            <Route
              path="/clinic"
              element={
                <ProtectedRoute fallback="/clinic/login" requireAdmin>
                  <ClinicLayout />
                </ProtectedRoute>
              }
            >
              <Route
                index
                element={<Navigate to="/clinic/dashboard" replace />} />
              <Route path="dashboard" element={<ClinicDashboardPage />} />
              <Route path="schedule" element={<ClinicSchedulePage />} />
              <Route path="patients" element={<ClinicPatientPage />} />
            </Route>

            {/* Clinic login/onboarding are "standalone" pages */}
            <Route
              path="/clinic/login"
              element={<ClinicOnboardingPage />}
            />
            <Route
              path="/onboarding"
              element={<ClinicOnboardingPage />}
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}