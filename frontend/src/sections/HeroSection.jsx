import { motion, useReducedMotion } from "framer-motion";
import AmbientVideo from "../components/ui/AmbientVideo.jsx";
import Button from "../components/ui/Button.jsx";

export default function HeroSection({ onLaunchPlanner }) {
  const reduceMotion = useReducedMotion();
  const ease = [0.22, 1, 0.36, 1];

  const item = reduceMotion
    ? {
        hidden: { opacity: 1, y: 0 },
        show: { opacity: 1, y: 0 },
      }
    : {
        hidden: { opacity: 0, y: 14 },
        show: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.75, ease },
        },
      };

  return (
    <section className="hero" id="hero">
      <AmbientVideo className="hero-video" src="/videos/railway-hero.mp4" />
      <div className="hero-overlay" />

      <motion.div
        className="hero-copy"
        initial="hidden"
        animate="show"
        variants={{
          hidden: {},
          show: {
            transition: {
              staggerChildren: reduceMotion ? 0 : 0.18,
              delayChildren: reduceMotion ? 0 : 0.12,
            },
          },
        }}
      >
        <motion.h1 variants={item}>RailSync</motion.h1>
        <motion.h2 variants={item}>
          Integrated Maintenance Planning for Indian Railways
        </motion.h2>
        <motion.p variants={item}>
          RailSync coordinates train movement with Engineering, S&amp;T and TRD
          maintenance requirements to generate practical maintenance block plans
          using constraint optimization.
        </motion.p>
        <motion.div className="hero-actions" variants={item}>
          <Button onClick={onLaunchPlanner}>Launch Planner</Button>
          <Button variant="secondary" href="#how-it-works">
            See How It Works
          </Button>
        </motion.div>
      </motion.div>
    </section>
  );
}
