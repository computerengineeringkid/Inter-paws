// frontend/src/types.ts

// API & Data Models
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "client" | "admin";
  clinic_id?: number;
  pets?: Pet[];
}

export interface Pet {
  id: number;
  user_id: number;
  name: string;
  species: string;
  breed: string;
  birth_date: string;
  notes?: string;
}

export interface Doctor {
  id: number;
  clinic_id: number;
  full_name: string;
  specialty?: string;
  is_active: boolean;
}

export interface Room {
  id: number;
  clinic_id: number;
  name: string;
  room_type: string;
  is_active: boolean;
}

export interface Appointment {
  id: number;
  start_time: string;
  end_time: string;
  reason_for_visit: string;
  pet_name?: string;
  user_email?: string;
  doctor_name?: string;
  room_name?: string;
}

// Scheduler & Recommendations
export interface RecommendedSlot {
  doctor_id: number;
  room_id: number;
  start_time: string;
  end_time: string;
  rank: number;
  score: number;
  rationale: string;
}

export interface AppointmentRequest {
  start: string;
  end: string;
  duration_minutes: number;
  reason_for_visit: string;
  urgency: string;
  clinic_id: number;
}

// Auth
export interface AuthUser {
  email: string;
  full_name: string;
  role: "client" | "admin";
  clinicId?: number;
  pets: Pet[];
}

export interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (
    email: string,
    password: string,
    url?: string
  ) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string
  ) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}
