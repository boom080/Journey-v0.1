export const DEFAULT_PROFILE_GOAL = "维持";

export const PROFILE_GENDER_OPTIONS = [
  { label: "男", value: "male" },
  { label: "女", value: "female" }
];

const GENDER_ALIASES = {
  male: "male",
  man: "male",
  m: "male",
  "男": "male",
  female: "female",
  woman: "female",
  f: "female",
  "女": "female"
};

function toPositiveNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return "";
  }

  const normalized = Number(value);
  return Number.isFinite(normalized) && normalized > 0 ? normalized : "";
}

function resolveBodyFatRate(profile = {}) {
  return [
    profile.body_fat_rate,
    profile.bodyFatRate,
    profile.body_fat,
    profile.bodyFat
  ]
    .map(toPositiveNumber)
    .find((value) => value !== "") || "";
}

export function normalizeGender(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }

  return GENDER_ALIASES[String(value).trim().toLowerCase()] || "";
}

export function getGenderLabel(value) {
  if (value === "male") {
    return "男";
  }

  if (value === "female") {
    return "女";
  }

  return "未填写";
}

export function normalizeProfile(profile) {
  if (!profile) {
    return null;
  }

  const gender = normalizeGender(profile.gender ?? profile.sex);
  const bodyFatRate = resolveBodyFatRate(profile);

  return {
    ...profile,
    nickname: profile.nickname || "",
    goal: profile.goal || DEFAULT_PROFILE_GOAL,
    gender,
    height: toPositiveNumber(profile.height),
    weight: toPositiveNumber(profile.weight),
    body_fat_rate: bodyFatRate
  };
}

export function buildProfilePayload(form = {}) {
  const normalized = normalizeProfile(form) || {};

  return {
    nickname: normalized.nickname || "",
    goal: normalized.goal || DEFAULT_PROFILE_GOAL,
    gender: normalized.gender || "",
    height: Number(normalized.height) || 0,
    weight: Number(normalized.weight) || 0,
    body_fat_rate: normalized.body_fat_rate === "" ? null : Number(normalized.body_fat_rate)
  };
}

export function mergeProfileSnapshot(form, payload) {
  return normalizeProfile({
    ...(form || {}),
    ...(payload || {})
  });
}
