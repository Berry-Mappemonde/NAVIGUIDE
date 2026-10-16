/**
 * Reporte du travail non critique après le premier paint (requestIdleCallback).
 * @param {() => void} fn
 * @param {{ timeout?: number }} [opts]
 * @returns {() => void} annulation
 */
export function scheduleIdle(fn, { timeout = 3000 } = {}) {
  if (typeof requestIdleCallback === "function") {
    const id = requestIdleCallback(() => fn(), { timeout });
    return () => cancelIdleCallback(id);
  }
  const id = setTimeout(fn, Math.min(timeout, 1500));
  return () => clearTimeout(id);
}
