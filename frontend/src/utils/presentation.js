/** Format a model confidence without changing the API value. */
export function formatConfidence(value) {
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return String(value);

  const percentage = numericValue >= 0 && numericValue <= 1
    ? numericValue * 100
    : numericValue;
  return `${percentage.toFixed(1)}%`;
}

export function observationText(value) {
  return typeof value === "string" && value.trim()
    ? value
    : "Not provided in submitted evidence.";
}
