import { Navigate, useLocation } from "react-router-dom";
import { PropsWithChildren, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

interface ProtectedRouteProps extends PropsWithChildren {
  fallback: string;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, fallback, requireAdmin = false }: ProtectedRouteProps) {
  const { isAuthenticated, isAdmin, refreshProfile } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (isAuthenticated) {
      refreshProfile().catch((error) => console.error("Profile refresh failed", error));
    }
  }, [isAuthenticated, refreshProfile]);

  if (!isAuthenticated) {
    return <Navigate to={fallback} state={{ from: location }} replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/client/booking" replace />;
  }

  return <>{children}</>;
}
