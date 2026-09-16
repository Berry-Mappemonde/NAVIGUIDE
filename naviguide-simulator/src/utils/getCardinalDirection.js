const DIRECTIONS = [
  "N", "NNE", "NE", "ENE",
  "E", "ESE", "SE", "SSE",
  "S", "SSO", "SO", "OSO",
  "O", "ONO", "NO", "NNO",
];

function degreesOf(input) {
  if (typeof input === "number") return input;
  if (input && typeof input === "object") return Number(input.degrees);
  return Number.NaN;
}

/** Cap cardinal. Accepte un nombre (App) ou `{ degrees }` (ancien contrat). */
export function getCardinalDirection(input) {
  const degrees = degreesOf(input);
  if (!Number.isFinite(degrees)) return "";
  const wrapped = ((degrees % 360) + 360) % 360;
  const index = Math.round(wrapped / 22.5) % 16;
  return DIRECTIONS[index];
}
