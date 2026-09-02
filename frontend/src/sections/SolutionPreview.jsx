import { motion, useInView, useReducedMotion } from "framer-motion";
import { useRef } from "react";
import SectionHeading from "../components/ui/SectionHeading.jsx";

const ease = [0.22, 1, 0.36, 1];
const hours = ["01:00", "02:00", "03:00", "04:00", "05:00"];

export default function SolutionPreview() {
  const reduceMotion = useReducedMotion();
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const play = reduceMotion || inView;

  return (
    <section className="section solution" id="solution">
      <div className="section-inner">
        <SectionHeading eyebrow="Solution" title="Place work in the free window">
          When a section is occupied, RailSync does not schedule a block. When a
          feasible gap exists, maintenance is placed there.
        </SectionHeading>

        <div className="timeline" ref={ref}>
          <div className="timeline-meta">
            <div>
              <strong>SEC03 · Palwal — Kosi Kalan</strong>
              Planning section
            </div>
            <div>
              <strong>01:00 — 05:00</strong>
              Horizon
            </div>
            <div>
              <strong>ENG017 · 120 min</strong>
              Rail Weld Inspection
            </div>
          </div>

          <div className="time-axis" aria-hidden="true">
            {hours.map((hour) => (
              <span key={hour}>{hour}</span>
            ))}
          </div>

          <div className="lane">
            <div className="lane-label">Train occupancy</div>
            <div className="lane-track">
              <motion.div
                className="block train"
                style={{ left: "0%", width: "26%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.55, ease, delay: reduceMotion ? 0 : 0.05 }}
              >
                TR104
              </motion.div>
              <motion.div
                className="block train"
                style={{ left: "74%", width: "26%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.55, ease, delay: reduceMotion ? 0 : 0.18 }}
              >
                TR118
              </motion.div>
            </div>
          </div>

          <div className="lane">
            <div className="lane-label">Maintenance demand</div>
            <div className="lane-track">
              <motion.div
                className="block demand"
                style={{ left: "4%", width: "28%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.5, ease, delay: reduceMotion ? 0 : 0.7 }}
              >
                ENG017
              </motion.div>
            </div>
          </div>

          <div className="lane">
            <div className="lane-label">Available window</div>
            <div className="lane-track">
              <motion.div
                className="block window"
                style={{ left: "28%", width: "44%" }}
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={play ? { opacity: 1 } : { opacity: 0 }}
                transition={{ duration: 0.5, ease, delay: reduceMotion ? 0 : 1.2 }}
              >
                Valid gap
              </motion.div>
            </div>
          </div>

          <div className="lane">
            <div className="lane-label">Integrated block</div>
            <div className="lane-track">
              <motion.div
                className="block placed"
                style={{ left: "30%", width: "40%" }}
                initial={
                  reduceMotion
                    ? { opacity: 1, x: 0, backgroundColor: "#2d6a4f" }
                    : { opacity: 0, x: -28, backgroundColor: "#b45309" }
                }
                animate={
                  play
                    ? {
                        opacity: 1,
                        x: 0,
                        backgroundColor: reduceMotion
                          ? "#2d6a4f"
                          : ["#b45309", "#b45309", "#2d6a4f"],
                      }
                    : { opacity: 0, x: -28, backgroundColor: "#b45309" }
                }
                transition={{
                  duration: reduceMotion ? 0 : 1.35,
                  ease,
                  delay: reduceMotion ? 0 : 1.7,
                  times: reduceMotion ? undefined : [0, 0.55, 1],
                }}
              >
                ENG017 + SNT004
              </motion.div>
            </div>
          </div>

          <motion.p
            className="confirmation"
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
            transition={{ duration: 0.45, ease, delay: reduceMotion ? 0 : 3.05 }}
          >
            <strong>Valid maintenance window</strong>
            No protected train conflict
          </motion.p>
        </div>

        <div className="solution-legend">
          <span>
            <i className="swatch train" /> Train occupancy
          </span>
          <span>
            <i className="swatch demand" /> Proposed maintenance
          </span>
          <span>
            <i className="swatch confirm" /> Confirmed block
          </span>
        </div>
      </div>
    </section>
  );
}
