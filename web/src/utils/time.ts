const SERVICE_TIME_ZONE = "Asia/Taipei";

const DATE_TIME_FORMAT = new Intl.DateTimeFormat("zh-TW", {
  timeZone: SERVICE_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const TIME_FORMAT = new Intl.DateTimeFormat("zh-TW", {
  timeZone: SERVICE_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

function parts(formatter: Intl.DateTimeFormat, date: Date): Record<string, string> {
  return Object.fromEntries(
    formatter
      .formatToParts(date)
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value]),
  );
}

export function formatServiceDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const p = parts(DATE_TIME_FORMAT, date);
  return `${p.year}/${p.month}/${p.day} ${p.hour}:${p.minute}`;
}

export function formatServiceTime(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const p = parts(TIME_FORMAT, date);
  return `${p.hour}:${p.minute}:${p.second}`;
}
