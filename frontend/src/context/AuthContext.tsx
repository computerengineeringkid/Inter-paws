// frontend/src/context/AuthContext.tsx
import {
  createContext,
  useState,
  useContext,
  PropsWithChildren,
  useEffect,
  useCallback,
} from "react";
import { apiFetch, apiFetchWithBody } from "../utils/api";
import { AuthContextValue, AuthUser } from "../types";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const refreshProfile = useCallback(async () => {
    try {
      const data = await apiFetch("/api/auth/profile");
      setUser(data.user);
      setIsAuthenticated(true);
      setIsAdmin(data.user.role === "admin");
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
      setIsAdmin(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  const login = async (
    email: string,
    password: string,
    loginUrl = "/api/auth/login" // Default login URL
  ) => {
    await apiFetchWithBody(loginUrl, "POST", { email, password });
    await refreshProfile();
  };

  const register = async (
    email: string,
    password: string,
    fullName: string
  ) => {
    await apiFetchWithBody("/api/auth/register", "POST", {
      email,
      password,
      full_name: fullName,
    });
    await refreshProfile();
  };

  const logout = async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    setUser(null);
    setIsAuthenticated(false);
    setIsAdmin(false);
  };

  const value = {
    user,
    isAuthenticated,
    isAdmin,
    login,
    register,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
