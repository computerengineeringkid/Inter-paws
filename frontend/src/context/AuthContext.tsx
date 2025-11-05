import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import { apiFetch } from "../utils/api";

type Mode = "client" | "clinic";

export interface UserProfile {
  id: number;
  email: string;
  full_name?: string | null;
  role: string;
  clinic_id?: number | null;
}

interface AuthContextValue {
  token: string | null;
  profile: UserProfile | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (payload: { email: string; password: string }, mode?: Mode) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    role?: string;
    clinic_id?: number | null;
  }) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  setTokenForMode: (token: string | null, mode?: Mode) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = "inter-paws-token";
const STORAGE_MODE_KEY = "inter-paws-mode";

type AuthResponse = {
  access_token: string;
};

type ProfileResponse = {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  clinic_id: number | null;
};

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });
  const [mode, setMode] = useState<Mode | null>(() => {
    const stored = localStorage.getItem(STORAGE_MODE_KEY);
    return stored === "clinic" ? "clinic" : stored === "client" ? "client" : null;
  });
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const isAuthenticated = Boolean(token);
  const isAdmin = (profile?.role || "").toLowerCase() === "admin";

  const setTokenForMode = useCallback((value: string | null, nextMode: Mode = "client") => {
    if (value) {
      localStorage.setItem(STORAGE_KEY, value);
      localStorage.setItem(STORAGE_MODE_KEY, nextMode);
    } else {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_MODE_KEY);
    }
    setToken(value);
    setMode(value ? nextMode : null);
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!token) {
      setProfile(null);
      return;
    }
    try {
      const response = await apiFetch<ProfileResponse>("/auth/me", {
        method: "GET",
        token,
      });
      setProfile(response);
    } catch (error) {
      console.error("Failed to load profile", error);
      setTokenForMode(null);
      setProfile(null);
    }
  }, [token, setTokenForMode]);

  const login = useCallback(
    async ({ email, password }: { email: string; password: string }, nextMode: Mode = "client") => {
      const response = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setTokenForMode(response.access_token, nextMode);
      await refreshProfile();
    },
    [refreshProfile, setTokenForMode]
  );

  const register = useCallback(
    async ({ email, password, name, role = "client", clinic_id }: {
      email: string;
      password: string;
      name: string;
      role?: string;
      clinic_id?: number | null;
    }) => {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, name, role, clinic_id }),
      });
      const response = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setTokenForMode(response.access_token, role === "admin" ? "clinic" : "client");
      await refreshProfile();
    },
    [refreshProfile, setTokenForMode]
  );

  const logout = useCallback(() => {
    setTokenForMode(null);
    setProfile(null);
  }, [setTokenForMode]);

  useEffect(() => {
    if (token) {
      refreshProfile().catch((error) => console.error(error));
    }
  }, [token, refreshProfile]);

  const value = useMemo(
    () => ({
      token,
      profile,
      isAuthenticated,
      isAdmin,
      login,
      register,
      logout,
      refreshProfile,
      setTokenForMode,
    }),
    [token, profile, isAuthenticated, isAdmin, login, register, logout, refreshProfile, setTokenForMode]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
