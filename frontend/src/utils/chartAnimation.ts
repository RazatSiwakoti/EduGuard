import { useEffect, useState } from "react";

/**
 * Let a chart animate in once, on first paint, and never again.
 *
 * WHY NOT SIMPLY `isAnimationActive`.
 * Recharts' flag is all-or-nothing. Leave it on and every chart replays
 * its full grow-in each time a filter changes, which turns a two-click
 * comparison into several seconds of movement and makes the dashboard
 * feel slower than one with no animation at all. Leave it off — which
 * is where this project started, `isAnimationActive={false}` on all six
 * charts — and the bars appear fully formed, which is instant but says
 * nothing about how the values relate. Animating once gets both.
 *
 * A NOTE ON MEASURING THIS, because it cost real time.
 * A first-paint animation is over before Playwright's `goto()` returns
 * if anything holds the `load` event open — here, three Google Fonts
 * requests failing in a sandbox with no network added about a second.
 * Sampling after `load` therefore showed the bars perfectly static and
 * led to the confident, wrong conclusion that Recharts 3 does not
 * animate stacked bars at all. It does. Measure from `commit`, not
 * `load`, or you will "prove" that any intro animation is broken.
 *
 * REDUCED MOTION is honoured up front rather than after the fact. A bar
 * chart growing from the baseline is exactly the large-area movement
 * that triggers vestibular symptoms, and the motion carries no
 * information the settled chart lacks, so switching it off costs the
 * reader nothing.
 */
export function useChartIntroAnimation(durationMs = 700): {
  isAnimationActive: boolean;
  animationDuration: number;
} {
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const [active, setActive] = useState(!prefersReducedMotion);

  useEffect(() => {
    if (!active) return;
    // A little past the animation's own length, so the final frame has
    // landed before the prop flips and Recharts stops interpolating.
    const timer = window.setTimeout(() => setActive(false), durationMs + 150);
    return () => window.clearTimeout(timer);
    // Runs once: `active` only ever goes true -> false, and re-arming on
    // that transition would schedule a timer with nothing left to do.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { isAnimationActive: active, animationDuration: durationMs };
}