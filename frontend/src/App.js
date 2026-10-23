import React, { useCallback, useState } from "react";
import "./App.css";
import { clearSession, loadSession, saveSession } from "./api";
import Dashboard from "./Dashboard";

import Assistant from "./Components/Assistant";
import CheckOrder from "./Components/CheckOrder";
import Contact from "./Components/Contact";
import Home from "./Components/Home";
import Login from "./Components/Login";
import Navbar from "./Components/Navbar";
import Profile from "./Components/Profile";
import Register from "./Components/Register";

// Pages that need a logged-in user
const PROTECTED = ["dashboard", "checkorder", "assistant", "profile"];

function App() {
  const [session, setSession] = useState(loadSession);
  const [page, setPage] = useState("home");

  const handleLogin = (token, user) => {
    saveSession(token, user);
    setSession({ token, user });
    setPage("dashboard");
  };

  const handleLogout = () => {
    clearSession();
    setSession(null);
    setPage("home");
  };

  // Called when the API says the token is invalid or expired.
  // useCallback keeps it stable so the Dashboard's polling effect doesn't restart.
  const handleAuthError = useCallback(() => {
    clearSession();
    setSession(null);
    setPage("login");
  }, []);

  const current = PROTECTED.includes(page) && !session ? "login" : page;

  return (
    <>
      <Navbar page={current} onNavigate={setPage} isLoggedIn={!!session} onLogout={handleLogout} />

      <main className="container">
        {current === "home" && <Home onGetStarted={() => setPage(session ? "dashboard" : "login")} />}
        {current === "login" && <Login onLogin={handleLogin} onRegister={() => setPage("register")} />}
        {current === "register" && <Register onBack={() => setPage("login")} />}
        {current === "dashboard" && <Dashboard onAuthError={handleAuthError} />}
        {current === "checkorder" && <CheckOrder onAuthError={handleAuthError} />}
        {current === "assistant" && <Assistant onAuthError={handleAuthError} />}
        {current === "profile" && <Profile user={session.user} />}
        {current === "contact" && <Contact />}
      </main>
    </>
  );
}

export default App;
