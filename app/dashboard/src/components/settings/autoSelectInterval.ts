/** Convert existing Xray durations to seconds for the panel's numeric field. */
export const intervalToSeconds = (interval: string): string => {
  if (/^\d+$/.test(interval)) return interval;
  const parts = Array.from(interval.matchAll(/(\d+(?:\.\d+)?)(ms|s|m|h)/g));
  if (!parts.length || parts.map((p) => p[0]).join("") !== interval) return interval;
  const units: Record<string, number> = { ms: 0.001, s: 1, m: 60, h: 3600 };
  return String(parts.reduce((sum, p) => sum + Number(p[1]) * units[p[2]], 0));
};

export const validIntervalSeconds = (value: string): boolean =>
  /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) && Number(value) > 0;
