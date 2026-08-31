// System-local datetime utilities for consistent formatting across the app

export function getSystemTimeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return undefined;
  }
}

export function toDate(value: string | number | Date): Date {
  return value instanceof Date ? value : new Date(value);
}

export function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function relativeDayLabel(d: Date): string {
  const now = new Date();
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const emailDay = startOfDay(d);

  if (emailDay.getTime() === today.getTime()) return 'Today';
  if (emailDay.getTime() === yesterday.getTime()) return 'Yesterday';

  // Month or Month YYYY
  const sameYear = d.getFullYear() === now.getFullYear();
  return d.toLocaleDateString(undefined, {
    year: sameYear ? undefined : 'numeric',
    month: 'long',
  });
}

export function formatLocalTime(d: Date): string {
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
}

export function formatLocalDateTime(d: Date): string {
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatRelativeTimestamp(value: string | number | Date): string {
  const date = toDate(value);
  if (isNaN(date.getTime())) return 'Invalid date';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  const label = relativeDayLabel(date);
  if (label === 'Today') {
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
    if (diffHr < 24) return `${diffHr} hour${diffHr === 1 ? '' : 's'} ago`;
    return `Today at ${formatLocalTime(date)}`;
  }
  if (label === 'Yesterday') {
    return `Yesterday at ${formatLocalTime(date)}`;
  }
  if (diffDay < 7) {
    return `${date.toLocaleDateString(undefined, { weekday: 'long' })} at ${formatLocalTime(date)}`;
  }
  return formatLocalDateTime(date);
}


