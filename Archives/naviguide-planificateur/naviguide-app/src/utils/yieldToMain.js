/** Cède le thread principal entre lots de travail (segments, parsing). */
export function yieldToMain({ timeout = 48 } = {}) {
  return new Promise((resolve) => {
    if (typeof requestIdleCallback === "function") {
      requestIdleCallback(() => resolve(), { timeout });
    } else {
      setTimeout(resolve, 0);
    }
  });
}
