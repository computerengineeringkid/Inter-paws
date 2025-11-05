import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate, Location } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

interface LoginForm {
  email: string;
  password: string;
}

interface ClientLoginPageProps {
  mode?: "client" | "clinic";
}

const headings = {
  client: {
    title: "Sign in to book care",
    subtitle: "Pick the best appointment, see your pet's history, and get smart follow-ups tailored to your clinic.",
    registerPath: "/client/register",
    bullets: [
      "Instantly compare the best appointment matches for your pet",
      "Syncs with clinic teams for real-time availability",
      "Track visits, prescriptions, and follow-up reminders",
    ],
  },
  clinic: {
    title: "Clinic staff sign in",
    subtitle: "Coordinate doctors, rooms, and priorities—all optimized by Inter-Paws.",
    registerPath: "/client/register",
    bullets: [
      "One view of today's schedule, rooms, and cases",
      "AI triage helps staff focus on urgent visits first",
      "Invite new team members in a few clicks",
    ],
  },
};

export function ClientLoginPage({ mode = "client" }: ClientLoginPageProps) {
  const { register: formRegister, handleSubmit } = useForm<LoginForm>({
    defaultValues: { email: "", password: "" },
  });
  const { login, isAuthenticated, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);
  const heading = headings[mode];

  if (isAuthenticated) {
    return <Navigate to={mode === "clinic" && isAdmin ? "/clinic/dashboard" : "/client/booking"} replace />;
  }

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    setError(null);
    try {
      const loginUrl = mode === "clinic" ? "/api/auth/clinic/login" : undefined;
      await login(values.email, values.password, loginUrl);
      if (mode === "clinic") {
        navigate("/clinic/dashboard");
      } else {
        const redirectPath = (location.state as { from?: Location } | undefined)?.from?.pathname;
        navigate(redirectPath ?? "/client/booking", { replace: true });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to sign in. Check your credentials.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="app-shell">
      <div className="auth-page">
        <section className="auth-hero">
          <span className="auth-hero-badge">Inter-Paws smart scheduling</span>
          <h1>{heading.title}</h1>
          <p>{heading.subtitle}</p>
          <ul>
            {heading.bullets.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section className="auth-card">
          <header>
            <h2>Welcome back</h2>
            <p>Sign in with your registered email to continue.</p>
          </header>

          {error ? (
            <div className="alert error" role="alert">
              {error}
            </div>
          ) : null}

          <div className="form-surface">
            <form className="stack" onSubmit={onSubmit}>
              <label>
                <span>Email</span>
                <div className="input-affordance">
                  <span className="input-icon" aria-hidden>✉️</span>
                  <input
                    type="email"
                    autoComplete="email"
                    {...formRegister("email", { required: true })}
                    placeholder="you@example.com"
                  />
                </div>
              </label>

              <label>
                <span>Password</span>
                <div className="input-affordance">
                  <span className="input-icon" aria-hidden>🔒</span>
                  <input
                    type="password"
                    autoComplete="current-password"
                    {...formRegister("password", { required: true })}
                    placeholder="••••••••"
                  />
                </div>
              </label>

              <div className="login-meta">
                <label style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                  <input type="checkbox" defaultChecked aria-label="Stay signed in" />
                  <span>Stay signed in</span>
                </label>
                <a href="mailto:support@interpaws.com">Need help?</a>
              </div>

              <button className="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Signing in..." : "Sign in"}
              </button>
            </form>
          </div>

          <div className="auth-footer">
            <span>New here? </span>
            <Link to={heading.registerPath}>Create an account</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
