import { motion, useReducedMotion } from "framer-motion";
import AmbientVideo from "../components/ui/AmbientVideo.jsx";

const items = [
  {
    title: "Fragmented Planning",
    body: "Engineering, S&T and TRD maintenance requirements are handled separately.",
  },
  {
    title: "Repeated Closures",
    body: "Compatible maintenance activities may require multiple block windows.",
  },
  {
    title: "Operational Disruption",
    body: "Additional block time can reduce asset availability and interfere with train movement.",
  },
];

export default function ProblemSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="problem" id="impact">
      <div className="problem-grid">
        <div className="problem-visual">
          <AmbientVideo src="/videos/railway-maintenance.mp4" />
        </div>

        <div className="problem-copy">
          <span className="section-eyebrow">Impact</span>
          <h2>Maintenance still planned in fragments</h2>

          {items.map((item, index) => (
            <motion.article
              className="problem-item"
              key={item.title}
              initial={reduceMotion ? false : { opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.45 }}
              transition={{
                duration: 0.55,
                delay: reduceMotion ? 0 : index * 0.14,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              <span className="problem-index">0{index + 1}</span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
