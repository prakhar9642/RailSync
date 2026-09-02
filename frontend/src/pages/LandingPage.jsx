import { useEffect, useState } from "react";
import Navbar from "../components/layout/Navbar.jsx";
import Footer from "../components/layout/Footer.jsx";
import HeroSection from "../sections/HeroSection.jsx";
import ProblemSection from "../sections/ProblemSection.jsx";
import HowItWorks from "../sections/HowItWorks.jsx";
import CorridorPreview from "../sections/CorridorPreview.jsx";
import SolutionPreview from "../sections/SolutionPreview.jsx";
import FinalCTA from "../sections/FinalCTA.jsx";

export default function LandingPage({ onLaunchPlanner }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
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
      <HeroSection onLaunchPlanner={onLaunchPlanner} />
      <ProblemSection />
      <HowItWorks />
      <CorridorPreview />
      <SolutionPreview />
      <FinalCTA onLaunchPlanner={onLaunchPlanner} />
      <Footer />
    </div>
  );
}
