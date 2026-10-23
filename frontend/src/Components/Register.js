import React, { useState } from "react";
import { apiFetch } from "../api";

const EMPTY = { fullname: "", email: "", password: "", phone: "" };

function Register({ onBack }) {
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState({ type: "", text: "" });

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/api/register", { method: "POST", body: form, auth: false });
      setForm(EMPTY);
      setMessage({ type: "success", text: "Account created. You can log in now." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };

  return (
    <form className="card form-card" onSubmit={handleRegister}>
      <h2>Create Account</h2>
      <input name="fullname" placeholder="Full Name" value={form.fullname} onChange={handleChange} required />
      <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required />
      <input name="password" type="password" placeholder="Password (min 6 characters)" minLength={6}
        value={form.password} onChange={handleChange} required />
      <input name="phone" placeholder="Phone Number" value={form.phone} onChange={handleChange} required />
      {message.text && <p className={message.type}>{message.text}</p>}
      <button className="btn" type="submit">Register</button>
      <p className="muted">
        Already registered? <span className="link" onClick={onBack}>Login</span>
      </p>
    </form>
  );
}

export default Register;
