const FORMATTER = new Intl.RelativeTimeFormat(undefined, { numeric: "always" });

export function relativeTime(value: string): string {
  const elapsed = Date.now() - new Date(value).getTime();
  const seconds = Math.round(elapsed / 1000);
  if (seconds < 60) return FORMATTER.format(-seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return FORMATTER.format(-minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (hours < 24) return FORMATTER.format(-hours, "hour");
  if (hours < 48) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
}
