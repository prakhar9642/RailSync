import { useEffect, useState } from "react";
import { getTerritories } from "../services/api.js";
import { territoryLabel } from "../utils/planningLabels.js";
import Navbar from "../components/layout/Navbar.jsx";
import Footer from "../components/layout/Footer.jsx";
import HeroSection from "../sections/HeroSection.jsx";
import ProblemSection from "../sections/ProblemSection.jsx";
import HowItWorks from "../sections/HowItWorks.jsx";
import CorridorPreview from "../sections/CorridorPreview.jsx";
import SolutionPreview from "../sections/SolutionPreview.jsx";
import FinalCTA from "../sections/FinalCTA.jsx";

export default function LandingPage({ onLaunchPlanner, initialTerritoryId }) {
  const [scrolled, setScrolled] = useState(false);
  const [territories, setTerritories] = useState([]);
  const [territoryId, setTerritoryId] = useState(initialTerritoryId);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getTerritories({ signal: controller.signal })
      .then((response) => setTerritories(response.territories ?? []))
      .catch(() => setTerritories([]));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (!id) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="landing">
      <Navbar
        overlay
        scrolled={scrolled}
        onLaunchPlanner={onLaunchPlanner}
        onHome={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      />
      <HeroSection onLaunchPlanner={() => onLaunchPlanner(territoryId)} />
      <section className="landing-territory-launcher" aria-labelledby="territory-launch-heading">
        <div><span>Three public timetable territories</span><h2 id="territory-launch-heading">Choose a corridor, then keep one planning session through decision and recovery.</h2></div>
        <label>Public corridor<select value={territoryId} onChange={(event) => setTerritoryId(event.target.value)}>{territories.map((territory) => <option key={territory.territory_id} value={territory.territory_id}>{territoryLabel(territory)}</option>)}</select></label>
        <button type="button" onClick={() => onLaunchPlanner(territoryId)}>Open Planning Workspace</button>
      </section>
      <ProblemSection />
      <HowItWorks />
      <CorridorPreview />
      <SolutionPreview />
      <FinalCTA onLaunchPlanner={() => onLaunchPlanner(territoryId)} />
      <Footer />
    </div>
  );
}
