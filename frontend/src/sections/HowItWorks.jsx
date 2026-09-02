import { useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useInView,
  useReducedMotion,
} from "framer-motion";
import SectionHeading from "../components/ui/SectionHeading.jsx";

const STAGE_HOLD_MS = 5000;
const COMPLETE_HOLD_MS = 5500;

const STAGES = [
  {
    index: "01",
    category: "Operational input",
    title: "Train Occupancy",
    description:
      "Timetable movements reveal when every corridor section is already occupied and unavailable for maintenance.",
    tone: "train",
    icon: "train",
  },
  {
    index: "02",
    category: "Engineering input",
    title: "Maintenance Demand",
    description:
      "Engineering, S&T and TRD tasks arrive with their section, duration and crew requirements.",
    tone: "maintenance",
    icon: "maintenance",
  },
  {
    index: "03",
    category: "Constraint solver",
    title: "CP-SAT Optimization",
    description:
      "The solver tests feasible windows against train occupancy, task rules and shared operational constraints.",
    tone: "solver",
    icon: "solver",
  },
  {
    index: "04",
    category: "Coordinated output",
    title: "Integrated Block Plan",
    description:
      "Compatible work is combined into one conflict-free sequence of coordinated maintenance blocks.",
    tone: "result",
    icon: "result",
  },
];

const COMPLETE_PHASE = STAGES.length;
const ease = [0.22, 1, 0.36, 1];
const stageMotion = {
  initial: { opacity: 0, x: 40 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -40 },
};

function StageIcon({ type }) {
  if (type === "train") {
    return (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <rect x="15" y="10" width="34" height="38" rx="7" />
        <path d="M22 18h20M20 31h24M23 48l-5 7M41 48l5 7" />
        <circle cx="23" cy="39" r="2" />
        <circle cx="41" cy="39" r="2" />
      </svg>
    );
  }

  if (type === "maintenance") {
    return (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path d="M38 12a12 12 0 0 0-14 15L11 40a5 5 0 0 0 7 7l13-13a12 12 0 0 0 15-14l-8 8-7-2-2-7 9-7Z" />
        <path d="m38 41 12 12M44 35l9 9" />
      </svg>
    );
  }

  if (type === "solver") {
    return (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="14" cy="18" r="5" />
        <circle cx="14" cy="46" r="5" />
        <circle cx="32" cy="32" r="6" />
        <circle cx="50" cy="18" r="5" />
        <circle cx="50" cy="46" r="5" />
        <path d="m18 20 9 8m-9 16 9-8m10-8 9-8m-9 16 9 8" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <rect x="11" y="13" width="42" height="38" rx="3" />
      <path d="M11 24h42M21 8v10M43 8v10m-23 19 7 7 17-17" />
    </svg>
  );
}

function StageCard({ stage }) {
  return (
    <motion.article
      className={`pipeline-stage stage-${stage.tone}`}
      {...stageMotion}
      transition={{ duration: 0.6, ease }}
    >
      <div className="pipeline-stage-copy">
        <div className="pipeline-stage-meta">
          <span className="pipeline-stage-index">{stage.index}</span>
          <span className="pipeline-stage-category">{stage.category}</span>
        </div>
        <span className="pipeline-stage-rule" aria-hidden="true" />
        <h3>{stage.title}</h3>
        <p>{stage.description}</p>
      </div>
      <div className="pipeline-stage-icon">
        <StageIcon type={stage.icon} />
      </div>
    </motion.article>
  );
}

function CompactStage({ stage }) {
  return (
    <div className={`pipeline-complete-card stage-${stage.tone}`}>
      <StageIcon type={stage.icon} />
      <span>
        {stage.index} · {stage.category}
      </span>
      <strong>{stage.title}</strong>
    </div>
  );
}

function FlowConnector({ delay, reduceMotion }) {
  return (
    <motion.svg
      className="pipeline-flow-connector"
      viewBox="0 0 64 24"
      aria-hidden="true"
    >
      <motion.path
        d="M3 12h54"
        initial={reduceMotion ? false : { pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.75, delay, ease }}
      />
      <motion.path
        d="m50 5 7 7-7 7"
        initial={reduceMotion ? false : { pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.35, delay: delay + 0.55, ease }}
      />
    </motion.svg>
  );
}

function CompletePipeline({ reduceMotion }) {
  return (
    <motion.div
      className="pipeline-complete"
      {...stageMotion}
      transition={{ duration: 0.6, ease }}
      aria-label="Complete RailSync pipeline"
    >
      <div className="pipeline-inputs">
        <CompactStage stage={STAGES[0]} />
        <span className="pipeline-plus" aria-hidden="true">
          +
        </span>
        <CompactStage stage={STAGES[1]} />
      </div>
      <FlowConnector delay={0.45} reduceMotion={reduceMotion} />
      <CompactStage stage={STAGES[2]} />
      <FlowConnector delay={1.15} reduceMotion={reduceMotion} />
      <CompactStage stage={STAGES[3]} />
    </motion.div>
  );
}

export default function HowItWorks() {
  const reduceMotion = useReducedMotion();
  const ref = useRef(null);
  const inView = useInView(ref, { amount: 0.35 });
  const [phase, setPhase] = useState(0);
  const complete = reduceMotion || phase === COMPLETE_PHASE;

  useEffect(() => {
    if (reduceMotion || !inView) return undefined;

    const hold = phase === COMPLETE_PHASE ? COMPLETE_HOLD_MS : STAGE_HOLD_MS;
    const id = window.setTimeout(() => {
      setPhase((current) =>
        current === COMPLETE_PHASE ? 0 : current + 1,
      );
    }, hold);

    return () => window.clearTimeout(id);
  }, [inView, phase, reduceMotion]);

  const progress = complete
    ? 100
    : (phase / (STAGES.length - 1)) * 100;

  return (
    <section className="section how" id="how-it-works">
      <div className="section-inner pipeline-wrap">
        <SectionHeading eyebrow="Method" title="How RailSync works">
          Occupancy and maintenance demand move through CP-SAT constraint
          optimization to produce an integrated block plan.
        </SectionHeading>

        <div className="pipeline" ref={ref}>
          <div className="pipeline-progress-wrap">
            <motion.span
              className="pipeline-progress-fill"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.65, ease }}
              aria-hidden="true"
            />
            <ol className="pipeline-progress" aria-label="RailSync workflow stages">
              {STAGES.map((stage, index) => {
                const active = !complete && phase === index;
                const completed = complete || phase > index;
                return (
                  <li
                    key={stage.title}
                    className={`stage-${stage.tone} ${active ? "is-active" : ""} ${
                      completed ? "is-complete" : ""
                    }`}
                    aria-current={active ? "step" : undefined}
                  >
                    <span className="pipeline-progress-dot" aria-hidden="true" />
                    <span className="pipeline-progress-label">{stage.title}</span>
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="pipeline-stage-viewport" aria-live="polite">
            <AnimatePresence mode="wait" initial={false}>
              {complete ? (
                <CompletePipeline key="complete" reduceMotion={reduceMotion} />
              ) : (
                <StageCard key={STAGES[phase].index} stage={STAGES[phase]} />
              )}
            </AnimatePresence>
          </div>

          <p className="pipeline-caption">
            {complete
              ? "Complete flow · inputs connect to the solver and coordinated plan."
              : `Stage ${STAGES[phase].index} of 04 · ${STAGES[phase].category}`}
          </p>
        </div>
      </div>
    </section>
  );
}
