const LINKS = [
  { id: "home", label: "Home" },
  { id: "dashboard", label: "Dashboard", auth: true },
  { id: "checkorder", label: "Check Order", auth: true },
  { id: "assistant", label: "Ops Copilot", auth: true },
  { id: "contact", label: "Contact" },
];

function Navbar({ page, onNavigate, isLoggedIn, onLogout }) {
  const button = (id, label) => (
    <button key={id} className={page === id ? "nav-link active" : "nav-link"} onClick={() => onNavigate(id)}>
      {label}
    </button>
  );

  return (
    <nav className="navbar">
      <span className="brand" onClick={() => onNavigate("home")}>🚚 IntelliChain</span>

      <div className="nav-links">
        {LINKS.filter((l) => !l.auth || isLoggedIn).map((l) => button(l.id, l.label))}

        {!isLoggedIn && button("login", "Login")}
        {!isLoggedIn && button("register", "Register")}

        {isLoggedIn && button("profile", "Profile")}
        {isLoggedIn && <button className="nav-link" onClick={onLogout}>Logout</button>}
      </div>
    </nav>
  );
}

export default Navbar;
