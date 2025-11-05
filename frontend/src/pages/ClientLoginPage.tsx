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
    subtitle: "Access recommendations, manage pets, and track visits.",
    registerPath: "/client/register",
  },
  clinic: {
    title: "Clinic staff sign in",
    subtitle: "Manage your team, rooms, and live schedule.",
    registerPath: "/client/register",
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
    <div className="main-layout" style={{ alignItems: "stretch" }}>
      <div className="content" style={{ maxWidth: 420, margin: "0 auto" }}>
        <div className="card" style={{ marginTop: "10vh" }}>
          <h1>{heading.title}</h1>
          <p style={{ color: "#4b5563", marginTop: "0.5rem" }}>{heading.subtitle}</p>
          {error ? (
            <div className="alert error" role="alert">
              {error}
            </div>
          ) : null}
          <form className="stack" onSubmit={onSubmit}>
            <label>
              <span>Email</span>
              <input type="email" {...formRegister("email", { required: true })} placeholder="you@example.com" />
            </label>
            <label>
              <span>Password</span>
              <input type="password" {...formRegister("password", { required: true })} placeholder="••••••" />
            </label>
            <button className="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
          <p style={{ marginTop: "1.5rem", color: "#4b5563" }}>
            New here? <Link to={heading.registerPath}>Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
