import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import SectionHeading from "../components/ui/SectionHeading.jsx";

const HOLD_MS = 5000;
const STEP_COUNT = 4;
const OVERVIEW = 4;

const STEPS = [
  {
    index: "01",
    role: "Input",
    title: "Train Occupancy",
    input: "Timetable occupancy for each section.",
    action: "Marks when a line is already in use.",
    output: "Occupied intervals the solver must avoid.",
  },
  {
    index: "02",
    role: "Input",
    title: "Maintenance Demand",
    input: "Engineering, S&T and TRD tasks.",
    action: "Captures duration, section and crew need.",
    output: "Work that must be placed into a block.",
  },
  {
    index: "03",
    role: "Solver",
    title: "CP-SAT Optimization",
    input: "Occupancy plus maintenance demand.",
    action: "Searches feasible windows under operational rules.",
    output: "Candidate blocks without protected-train conflict.",
  },
  {
    index: "04",
    role: "Output",
    title: "Integrated Block Plan",
    input: "Feasible candidate blocks.",
    action: "Combines compatible work into shared windows.",
    output: "One coordinated maintenance plan.",
  },
];

const ease = [0.22, 1, 0.36, 1];

export default function HowItWorks() {
  const reduceMotion = useReducedMotion();
  const ref = useRef(null);
  const inView = useInView(ref, { amount: 0.35 });
  const [phase, setPhase] = useState(reduceMotion ? OVERVIEW : 0);
  const overview = reduceMotion || phase === OVERVIEW;

  useEffect(() => {
    if (reduceMotion) {
      setPhase(OVERVIEW);
      return undefined;
    }
    if (!inView) return undefined;

    const id = window.setInterval(() => {
      setPhase((current) => (current + 1) % (STEP_COUNT + 1));
    }, HOLD_MS);

    return () => window.clearInterval(id);
  }, [inView, reduceMotion]);

  const markerLeft = overview ? "50%" : `${((phase + 0.5) / STEP_COUNT) * 100}%`;
  const markerWidth = overview ? "100%" : "18%";

  return (
    <section className="section how" id="how-it-works">
      <div className="section-inner pipeline-wrap">
        <SectionHeading eyebrow="Method" title="How RailSync works">
          Occupancy and maintenance demand move through CP-SAT constraint
          optimization to produce an integrated block plan.
        </SectionHeading>

        <div
          className={`pipeline ${overview ? "is-overview" : "is-focus"}`}
          ref={ref}
          aria-live="polite"
        >
          <div className="pipeline-rail" aria-hidden="true">
            <motion.span
              className="pipeline-marker"
              animate={{
                left: markerLeft,
                width: markerWidth,
                x: "-50%",
              }}
              transition={{ duration: 0.55, ease }}
            />
          </div>

          <div className="pipeline-steps">
            {STEPS.map((step, index) => (
              <div key={step.title} className="pipeline-cell">
                {index > 0 ? (
                  <span
                    className={`pipeline-connector ${
                      overview || phase >= index ? "on" : ""
                    }`}
                    aria-hidden="true"
                  />
                ) : null}

                <motion.article
                  className={[
                    "pipeline-step",
                    overview || phase === index ? "active" : "",
                    overview ? "overview" : "",
                    index === 2 ? "solver" : "",
                    index === 3 ? "result" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  animate={{
                    opacity: overview || phase === index ? 1 : 0.26,
                  }}
                  transition={{ duration: 0.45, ease }}
                >
                  <span className="pipeline-index">{step.index}</span>
                  <span className="pipeline-role">{step.role}</span>
                  <h3>{step.title}</h3>
                  <dl>
                    <div>
                      <dt>In</dt>
                      <dd>{step.input}</dd>
                    </div>
                    <div>
                      <dt>{index === 2 ? "Solver" : "Does"}</dt>
                      <dd>{step.action}</dd>
                    </div>
                    <div>
                      <dt>Out</dt>
                      <dd>{step.output}</dd>
                    </div>
                  </dl>
                </motion.article>
              </div>
            ))}
          </div>

          <p className="pipeline-caption">
            {overview
              ? "Full pipeline: occupancy and demand enter, CP-SAT solves, one block plan leaves."
              : `${STEPS[phase].title} · ${STEPS[phase].role}`}
          </p>
        </div>
      </div>
    </section>
  );
}
