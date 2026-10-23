import React, { useState } from "react";
import { apiFetch } from "../api";

function Login({ onLogin, onRegister }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch("/api/login", { method: "POST", body: form, auth: false });
      onLogin(data.token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card form-card" onSubmit={handleLogin}>
      <h2>Login</h2>
      <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required />
      <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} required />
      {error && <p className="error">{error}</p>}
      <button className="btn" type="submit" disabled={loading}>{loading ? "Logging in..." : "Login"}</button>
      <p className="muted">
        New here? <span className="link" onClick={onRegister}>Create an account</span>
      </p>
    </form>
  );
}

export default Login;
