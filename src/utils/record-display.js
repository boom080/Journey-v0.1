function cleanText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatDateTimeValue(value) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return `${pad2(parsed.getHours())}:${pad2(parsed.getMinutes())}`;
}

export function getRecordTime(record) {
  const explicitTime = cleanText(record?.time_text || record?.timeText);
  if (explicitTime) {
    return explicitTime;
  }

  const fallbackDateTime =
    record?.record_time ||
    record?.recorded_at ||
    record?.created_at ||
    record?.updated_at ||
    "";

  return formatDateTimeValue(fallbackDateTime);
}

export function getRecordTimeLabel(record, fallback = "未记录时间") {
  const recordTime = getRecordTime(record);
  return recordTime ? `记录于 ${recordTime}` : fallback;
}

export function getUpdateTimeLabel(record, fallback = "时间未填写") {
  const recordTime = getRecordTime(record);
  return recordTime ? `记录于 ${recordTime}` : fallback;
}
