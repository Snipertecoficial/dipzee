import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';

// Scroll-reveal (fade + slight rise) for the landing page. Trust-first and
// restrained — no parallax/particles. Critically, it respects
// prefers-reduced-motion: when the visitor asks for less motion, children
// render immediately with no transform/animation at all.
export function Reveal({ children, className = '', delay = 0 }) {
  const reduce = useReducedMotion();
  if (reduce) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 16 },
        show: { opacity: 1, y: 0, transition: { duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] } },
      }}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: '-60px' }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
