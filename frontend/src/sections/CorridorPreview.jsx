import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import SectionHeading from "../components/ui/SectionHeading.jsx";

export const CORRIDOR_STATIONS = [
  { id: "NDLS", name: "New Delhi" },
  { id: "NZM", name: "Hazrat Nizamuddin" },
  { id: "FDB", name: "Faridabad" },
  { id: "PWL", name: "Palwal" },
  { id: "KSV", name: "Kosi Kalan" },
  { id: "MTJ", name: "Mathura Junction" },
  { id: "CHT", name: "Chata" },
  { id: "RKM", name: "Raja Ki Mandi" },
  { id: "AGC", name: "Agra Cantt" },
];

export const CORRIDOR_SECTIONS = [
  "SEC01",
  "SEC02",
  "SEC03",
  "SEC04",
  "SEC05",
  "SEC06",
  "SEC07",
  "SEC08",
];

function StationMarker({ x, y, active, terminus }) {
  const fill = active ? "#1e5a8a" : "#fcfcfa";
  const stroke = active ? "#1e5a8a" : "#0c1d32";
  const scale = terminus ? 1.12 : 1;

  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <path
        d="M-8 3 L0 -11 L8 3 Z"
        fill={fill}
        stroke={stroke}
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <rect
        x="-5.5"
        y="3"
        width="11"
        height="8"
        fill={fill}
        stroke={stroke}
        strokeWidth="1.6"
      />
      <rect x="-1.6" y="6.5" width="3.2" height="4.5" fill={stroke} />
    </g>
  );
}

export default function CorridorPreview({
  stations = CORRIDOR_STATIONS,
  sections = CORRIDOR_SECTIONS,
}) {
  const reduceMotion = useReducedMotion();
  const [active, setActive] = useState(null);
  const count = stations.length;
  const pad = 42;
  const width = 1100;
  const y = 92;
  const inner = width - pad * 2;
  const xAt = (index) => pad + (inner * index) / (count - 1);
  const ease = [0.22, 1, 0.36, 1];
  const sleepers = Array.from({ length: 24 }, (_, index) => pad + (inner * index) / 23);

  return (
    <section className="section corridor" id="corridor">
      <div className="section-inner">
        <SectionHeading eyebrow="Corridor" title="One planning corridor">
          A single Delhi–Agra alignment. Stations and section IDs can later be
          replaced with timetable-backed data.
        </SectionHeading>

        <div className="corridor-track">
          <svg
            className="corridor-svg"
            viewBox={`0 0 ${width} 210`}
            role="img"
            aria-label="Rail corridor from New Delhi to Agra Cantt"
          >
            {sleepers.map((x) => (
              <line
                key={x}
                x1={x}
                y1={y - 6}
                x2={x}
                y2={y + 14}
                stroke="#ddd9d0"
                strokeWidth="2"
              />
            ))}

            <motion.line
              x1={pad}
              y1={y}
              x2={width - pad}
              y2={y}
              stroke="#0c1d32"
              strokeWidth="3.5"
              initial={{ pathLength: reduceMotion ? 1 : 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 1.15, ease }}
            />
            <motion.line
              x1={pad}
              y1={y + 8}
              x2={width - pad}
              y2={y + 8}
              stroke="#1e5a8a"
              strokeWidth="1.75"
              initial={{ pathLength: reduceMotion ? 1 : 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 1.15, delay: reduceMotion ? 0 : 0.08, ease }}
            />

            {sections.map((sectionId, index) => {
              const x1 = xAt(index);
              const x2 = xAt(index + 1);
              const mid = (x1 + x2) / 2;
              const highlighted = active === sectionId;
              return (
                <g
                  key={sectionId}
                  className="section-hit"
                  onMouseEnter={() => setActive(sectionId)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(sectionId)}
                  onBlur={() => setActive(null)}
                >
                  <rect
                    x={x1 + 10}
                    y={y - 36}
                    width={x2 - x1 - 20}
                    height="58"
                    fill="transparent"
                    tabIndex="0"
                  />
                  <line
                    x1={x1 + 12}
                    y1={y + 4}
                    x2={x2 - 12}
                    y2={y + 4}
                    stroke={highlighted ? "#1e5a8a" : "transparent"}
                    strokeWidth="12"
                    opacity="0.16"
                  />
                  <motion.text
                    x={mid}
                    y={y - 24}
                    textAnchor="middle"
                    className="section-id"
                    fill={highlighted ? "#1e5a8a" : "#8a8380"}
                    initial={reduceMotion ? false : { opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true, amount: 0.4 }}
                    transition={{ duration: 0.35, delay: reduceMotion ? 0 : 0.95 + index * 0.05 }}
                  >
                    {sectionId}
                  </motion.text>
                </g>
              );
            })}

            {stations.map((station, index) => {
              const highlighted =
                active === station.id ||
                active === sections[index] ||
                active === sections[index - 1];
              const terminus = index === 0 || index === count - 1;
              return (
                <g
                  key={station.id}
                  className="station-hit"
                  tabIndex="0"
                  onMouseEnter={() => setActive(station.id)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(station.id)}
                  onBlur={() => setActive(null)}
                >
                  <motion.g
                    initial={reduceMotion ? false : { opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true, amount: 0.4 }}
                    transition={{
                      duration: 0.3,
                      delay: reduceMotion ? 0 : 0.55 + index * 0.07,
                    }}
                  >
                    <StationMarker
                      x={xAt(index)}
                      y={y - 2}
                      active={highlighted}
                      terminus={terminus}
                    />
                  </motion.g>
                  <motion.text
                    x={xAt(index)}
                    y={y + 36}
                    textAnchor="middle"
                    className="station-code"
                    fill="#0c1d32"
                    initial={reduceMotion ? false : { opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true, amount: 0.4 }}
                    transition={{
                      duration: 0.3,
                      delay: reduceMotion ? 0 : 0.85 + index * 0.07,
                    }}
                  >
                    {station.id}
                  </motion.text>
                </g>
              );
            })}
          </svg>

          <div className="station-list">
            {stations.map((station, index) => (
              <motion.span
                key={station.id}
                className={active === station.id ? "is-active" : ""}
                initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.35 }}
                transition={{
                  duration: 0.35,
                  delay: reduceMotion ? 0 : 0.9 + index * 0.06,
                  ease,
                }}
              >
                {station.name}
              </motion.span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
