export function todayString() {
  return new Date().toISOString().slice(0, 10);
}

export function safeList(value) {
  return Array.isArray(value) ? value : [];
}

export function toErrorMessage(error, fallback) {
  return error?.message || fallback;
}
