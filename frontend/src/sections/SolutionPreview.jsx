import { motion, useInView, useReducedMotion } from "framer-motion";
import { useRef } from "react";
import SectionHeading from "../components/ui/SectionHeading.jsx";

const ease = [0.22, 1, 0.36, 1];
const hours = ["03:30", "04:38", "05:45", "06:53", "08:00"];

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
              <strong>SKM_SEC01 · Saktigarh — Palsit</strong>
              Planning section
            </div>
            <div>
              <strong>03:30 — 08:00</strong>
              Horizon
            </div>
            <div>
              <strong>SKM_ENG001 · 10 min</strong>
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
                style={{ left: "5.6%", width: "2%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.4, ease, delay: 0 }}
              >
                37786
              </motion.div>
              <motion.div
                className="block train"
                style={{ left: "17%", width: "2%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.4, ease, delay: 0 }}
              >
                37814
              </motion.div>
            </div>
          </div>

          <div className="lane">
            <div className="lane-label">Maintenance demand</div>
            <div className="lane-track">
              <motion.div
                className="block demand"
                style={{ left: "28%", width: "9.3%" }}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
                transition={{ duration: 0.4, ease, delay: 0 }}
              >
                SKM_ENG001
              </motion.div>
            </div>
          </div>

          <div className="lane">
            <div className="lane-label">Available window</div>
            <div className="lane-track">
              <motion.div
                className="block window"
                style={{ left: "19%", width: "33%" }}
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={play ? { opacity: 1 } : { opacity: 0 }}
                transition={{ duration: 0.4, ease, delay: 0 }}
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
                style={{ left: "28%", width: "9.3%" }}
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
                  duration: reduceMotion ? 0 : 0.4,
                  ease,
                  delay: 0,
                  times: reduceMotion ? undefined : [0, 0.55, 1],
                }}
              >
                SKM_ENG001 + SKM_SNT001
              </motion.div>
            </div>
          </div>

          <motion.p
            className="confirmation"
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={play ? { opacity: 1, y: 0 } : { opacity: 0, y: 8 }}
            transition={{ duration: 0.45, ease, delay: 0 }}
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
