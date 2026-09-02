import Button from "../components/ui/Button.jsx";

export default function FinalCTA({ onLaunchPlanner }) {
  return (
    <section className="final-cta">
      <div className="cta-track" aria-hidden="true" />
      <h2>Ready to coordinate your maintenance plan?</h2>
      <Button onClick={onLaunchPlanner}>Open Planning Workspace</Button>
    </section>
  );
}
