import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

interface RegisterForm {
  name: string;
  email: string;
  password: string;
  clinic_id?: number | null;
}

export function ClientRegisterPage() {
  const { register: formRegister, handleSubmit } = useForm<RegisterForm>({
    defaultValues: { name: "", email: "", password: "" },
  });
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const onSubmit = handleSubmit(async ({ name, email, password }) => {
    setSubmitting(true);
    setError(null);
    try {
      await registerUser(email, password, name);
      navigate("/client/booking", { replace: true });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to create your account.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="main-layout" style={{ alignItems: "stretch" }}>
      <div className="content" style={{ maxWidth: 480, margin: "0 auto" }}>
        <div className="card" style={{ marginTop: "8vh" }}>
          <h1>Create your Inter-Paws account</h1>
          <p style={{ color: "#4b5563", marginTop: "0.5rem" }}>
            Register to search for appointments, book visits, and view recommendations tailored for your pet.
          </p>
          {error ? (
            <div className="alert error" role="alert">
              {error}
            </div>
          ) : null}
          <form className="stack" onSubmit={onSubmit}>
            <label>
              <span>Full name</span>
              <input type="text" {...formRegister("name", { required: true })} placeholder="Alex Morgan" />
            </label>
            <label>
              <span>Email</span>
              <input type="email" {...formRegister("email", { required: true })} placeholder="you@example.com" />
            </label>
            <label>
              <span>Password</span>
              <input type="password" {...formRegister("password", { required: true, minLength: 6 })} placeholder="At least 6 characters" />
            </label>
            <button className="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating account..." : "Create account"}
            </button>
          </form>
          <p style={{ marginTop: "1.5rem", color: "#4b5563" }}>
            Already have an account? <Link to="/client/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
