import { useState } from "react";
import Button from "../ui/Button.jsx";

export default function Navbar({
  overlay = false,
  scrolled = false,
  onLaunchPlanner,
  onHome,
}) {
  const [open, setOpen] = useState(false);

  const goHomeSection = (id) => (event) => {
    event.preventDefault();
    setOpen(false);

    if (!overlay) {
      window.location.hash = id;
      onHome?.();
      return;
    }

    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const classes = [
    "navbar",
    overlay ? "navbar-overlay" : "navbar-solid",
    scrolled ? "scrolled" : "",
    open ? "open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <header className={classes}>
      <button className="nav-brand" type="button" onClick={onHome}>
        <span className="nav-mark" aria-hidden="true" />
        RailSync
      </button>

      <div className={`nav-panel ${open ? "open" : ""}`}>
        <ul className="nav-links">
          <li>
            <a href="#solution" onClick={goHomeSection("solution")}>
              Solution
            </a>
          </li>
          <li>
            <a href="#how-it-works" onClick={goHomeSection("how-it-works")}>
              How It Works
            </a>
          </li>
          <li>
            <a href="#impact" onClick={goHomeSection("impact")}>
              Impact
            </a>
          </li>
          <li>
            <button
              className="link"
              type="button"
              onClick={() => {
                setOpen(false);
                onLaunchPlanner();
              }}
            >
              Planner
            </button>
          </li>
        </ul>
        <Button
          onClick={() => {
            setOpen(false);
            onLaunchPlanner();
          }}
        >
          Launch Planner
        </Button>
      </div>

      <button
        className="nav-toggle"
        type="button"
        aria-label="Menu"
        onClick={() => setOpen((value) => !value)}
      >
        <span />
        <span />
        <span />
      </button>
    </header>
  );
}
