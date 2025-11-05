import { useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface DoctorFormValue {
  display_name: string;
  specialty?: string;
  license_number?: string;
}

interface RoomFormValue {
  name: string;
  room_type?: string;
  capacity?: number | null;
  notes?: string;
}

interface OperatingHourFormValue {
  day: string;
  start: string;
  end: string;
  notes?: string;
}

interface OnboardingForm {
  clinic: {
    name: string;
    email?: string;
    phone_number?: string;
    address?: string;
  };
  doctors: DoctorFormValue[];
  rooms: RoomFormValue[];
  schedule_rules: {
    operating_hours: OperatingHourFormValue[];
  };
}

function ClinicOnboardingPage() {
  const { token, logout } = useAuth();
  const form = useForm<OnboardingForm>({
    defaultValues: {
      clinic: { name: "" },
      doctors: [{ display_name: "" }],
      rooms: [{ name: "", room_type: "exam" }],
      schedule_rules: {
        operating_hours: [
          { day: "Monday", start: "09:00", end: "17:00" },
          { day: "Tuesday", start: "09:00", end: "17:00" },
        ],
      },
    },
  });

  const doctorFieldArray = useFieldArray({ control: form.control, name: "doctors" });
  const roomFieldArray = useFieldArray({ control: form.control, name: "rooms" });
  const hoursFieldArray = useFieldArray({ control: form.control, name: "schedule_rules.operating_hours" });

  const onboardingQuery = useQuery({
    queryKey: ["clinic-onboarding"],
    queryFn: async () => {
      const response = await apiFetch<OnboardingForm>("/clinic/onboarding", {
        method: "GET",
        token,
      });
      return response;
    },
  });

  const submitMutation = useMutation({
    mutationFn: async (values: OnboardingForm) => {
      return apiFetch("/clinic/onboarding", {
        method: "POST",
        token,
        body: JSON.stringify(values),
      });
    },
    onSuccess: () => onboardingQuery.refetch(),
  });

  useEffect(() => {
    if (onboardingQuery.data) {
      form.reset(onboardingQuery.data);
    }
  }, [onboardingQuery.data, form]);

  return (
    <div className="main-layout">
      <aside className="sidebar">
        <h2>Clinic HQ</h2>
        <a href="/clinic/dashboard">Dashboard</a>
        <a href="/clinic/schedule">Schedule</a>
        <a href="/clinic/patients">Patients</a>
        <a href="/clinic/onboarding">Onboarding</a>
        <button className="secondary" style={{ marginTop: "2rem" }} onClick={logout}>
          Sign out
        </button>
      </aside>
      <main className="content">
        <div className="card">
          <h1>Clinic onboarding</h1>
          <p style={{ color: "#4b5563" }}>
            Define your clinic profile, staff, and resources. This information powers availability suggestions across the platform.
          </p>
        </div>
        <form
          className="stack"
          onSubmit={form.handleSubmit(async (values) => {
            await submitMutation.mutateAsync(values);
          })}
        >
          <div className="card">
            <h2>Clinic details</h2>
            <div className="form-grid two-column">
              <label>
                <span>Name</span>
                <input type="text" {...form.register("clinic.name", { required: true })} />
              </label>
              <label>
                <span>Email</span>
                <input type="email" {...form.register("clinic.email")} />
              </label>
              <label>
                <span>Phone</span>
                <input type="tel" {...form.register("clinic.phone_number")} />
              </label>
              <label>
                <span>Address</span>
                <input type="text" {...form.register("clinic.address")} />
              </label>
            </div>
          </div>
          <div className="card">
            <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
              <h2>Doctors</h2>
              <button
                type="button"
                className="secondary"
                onClick={() => doctorFieldArray.append({ display_name: "" })}
              >
                Add doctor
              </button>
            </div>
            <div className="stack">
              {doctorFieldArray.fields.map((field, index) => (
                <div key={field.id} className="form-grid two-column">
                  <label>
                    <span>Display name</span>
                    <input type="text" {...form.register(`doctors.${index}.display_name` as const, { required: true })} />
                  </label>
                  <label>
                    <span>Specialty</span>
                    <input type="text" {...form.register(`doctors.${index}.specialty` as const)} />
                  </label>
                  <label>
                    <span>License</span>
                    <input type="text" {...form.register(`doctors.${index}.license_number` as const)} />
                  </label>
                  <div style={{ alignSelf: "center" }}>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => doctorFieldArray.remove(index)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
              <h2>Rooms</h2>
              <button type="button" className="secondary" onClick={() => roomFieldArray.append({ name: "" })}>
                Add room
              </button>
            </div>
            <div className="stack">
              {roomFieldArray.fields.map((field, index) => (
                <div key={field.id} className="form-grid two-column">
                  <label>
                    <span>Name</span>
                    <input type="text" {...form.register(`rooms.${index}.name` as const, { required: true })} />
                  </label>
                  <label>
                    <span>Type</span>
                    <input type="text" {...form.register(`rooms.${index}.room_type` as const)} />
                  </label>
                  <label>
                    <span>Capacity</span>
                    <input type="number" {...form.register(`rooms.${index}.capacity` as const, { valueAsNumber: true })} />
                  </label>
                  <label>
                    <span>Notes</span>
                    <input type="text" {...form.register(`rooms.${index}.notes` as const)} />
                  </label>
                  <div style={{ alignSelf: "center" }}>
                    <button type="button" className="secondary" onClick={() => roomFieldArray.remove(index)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="stack horizontal" style={{ justifyContent: "space-between" }}>
              <h2>Operating hours</h2>
              <button
                type="button"
                className="secondary"
                onClick={() => hoursFieldArray.append({ day: "Friday", start: "09:00", end: "17:00" })}
              >
                Add window
              </button>
            </div>
            <div className="stack">
              {hoursFieldArray.fields.map((field, index) => (
                <div key={field.id} className="form-grid two-column">
                  <label>
                    <span>Day</span>
                    <input type="text" {...form.register(`schedule_rules.operating_hours.${index}.day` as const, { required: true })} />
                  </label>
                  <label>
                    <span>Start</span>
                    <input type="time" {...form.register(`schedule_rules.operating_hours.${index}.start` as const, { required: true })} />
                  </label>
                  <label>
                    <span>End</span>
                    <input type="time" {...form.register(`schedule_rules.operating_hours.${index}.end` as const, { required: true })} />
                  </label>
                  <div style={{ alignSelf: "center" }}>
                    <button type="button" className="secondary" onClick={() => hoursFieldArray.remove(index)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <button className="primary" type="submit" disabled={submitMutation.isPending}>
              {submitMutation.isPending ? "Saving..." : "Save onboarding"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default ClinicOnboardingPage;
