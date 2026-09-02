import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";

export default function AmbientVideo({ src, className }) {
  const ref = useRef(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const video = ref.current;
    if (!video) return;

    if (reduceMotion) {
      video.pause();
      video.currentTime = 0;
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          video.play().catch(() => {});
        } else {
          video.pause();
        }
      },
      { threshold: 0.2 },
    );

    observer.observe(video);
    return () => observer.disconnect();
  }, [reduceMotion, src]);

  return (
    <video
      ref={ref}
      className={className}
      src={src}
      muted
      loop
      playsInline
      autoPlay={!reduceMotion}
      aria-hidden="true"
    />
  );
}
