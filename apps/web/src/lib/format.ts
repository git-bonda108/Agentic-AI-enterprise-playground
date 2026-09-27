/** Deterministic, locale-independent formatting for values rendered on the server: the same string in every browser, so hydration never disagrees. */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function parts(iso: string | Date): { d: Date; ok: boolean } {
  const d = iso instanceof Date ? iso : new Date(iso);
  return { d, ok: !Number.isNaN(d.getTime()) };
}

/** "27 Sep 2026, 15:44 UTC" */
export function formatWhen(iso: string | Date | null | undefined): string {
  if (!iso) return "";
  const { d, ok } = parts(iso);
  if (!ok) return String(iso);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${hh}:${mm} UTC`;
}

/** "27 Sep 2026" */
export function formatDay(iso: string | Date | null | undefined): string {
  if (!iso) return "";
  const { d, ok } = parts(iso);
  if (!ok) return String(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Thousands separated with commas regardless of the machine's locale. */
export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

/** "15:44:05 UTC" */
export function formatTime(iso: string | Date | null | undefined): string {
  if (!iso) return "";
  const { d, ok } = parts(iso);
  if (!ok) return String(iso);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}:${String(d.getUTCSeconds()).padStart(2, "0")} UTC`;
}
