function pad2(value) {
  return String(value).padStart(2, "0");
}

export function formatDateString(date = new Date()) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

export function formatTimeString(date = new Date()) {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function todayString() {
  return formatDateString(new Date());
}

export function dateOffsetString(offsetDays = 0) {
  const date = new Date();
  date.setDate(date.getDate() + Number(offsetDays || 0));
  return formatDateString(date);
}

export function currentTimeString() {
  return formatTimeString(new Date());
}

export function safeList(value) {
  return Array.isArray(value) ? value : [];
}

export function toErrorMessage(error, fallback) {
  return error?.message || fallback;
}
