import { normalizeProfile } from "./profile";

const DEFAULT_ACTIVITY_FACTOR = 1.35;

function roundKcal(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? Math.max(0, Math.round(amount)) : 0;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function estimateLeanMassWithBodyFat(weightKg, bodyFatRate) {
  const normalizedRate = clamp(Number(bodyFatRate || 0), 0, 70);
  return weightKg * (1 - normalizedRate / 100);
}

function estimateLeanMassWithHume(heightCm, weightKg, gender) {
  if (gender === "female") {
    return 0.29569 * weightKg + 0.41813 * heightCm - 43.2933;
  }

  return 0.3281 * weightKg + 0.33929 * heightCm - 29.5336;
}

export function calculateDailyEnergy(profile, options = {}) {
  const normalizedProfile = normalizeProfile(profile) || {};
  const weightKg = Number(normalizedProfile.weight || 0);
  const heightCm = Number(normalizedProfile.height || 0);
  const bodyFatRate = Number(normalizedProfile.body_fat_rate || 0);
  const gender = normalizedProfile.gender || "";
  const activityFactor = Number(options.activityFactor) || DEFAULT_ACTIVITY_FACTOR;

  if (!weightKg) {
    return {
      valid: false,
      method: "insufficient_data",
      method_label: "待补充资料",
      bmr_kcal: 0,
      daily_energy_kcal: 0,
      activity_factor: activityFactor
    };
  }

  let leanMassKg = 0;
  let method = "weight_only";
  let methodLabel = "体重估算";

  if (bodyFatRate > 0 && bodyFatRate < 70) {
    leanMassKg = estimateLeanMassWithBodyFat(weightKg, bodyFatRate);
    method = "katch_mcardle";
    methodLabel = "Katch-McArdle";
  } else if (heightCm > 0) {
    leanMassKg = estimateLeanMassWithHume(heightCm, weightKg, gender);
    method = "hume_katch";
    methodLabel = "Hume + Katch-McArdle";
  } else {
    leanMassKg = gender === "female" ? weightKg * 0.68 : weightKg * 0.8;
  }

  const safeLeanMassKg = Math.max(weightKg * 0.45, leanMassKg);
  const bmrKcal = 370 + 21.6 * safeLeanMassKg;
  const dailyEnergyKcal = bmrKcal * activityFactor;

  return {
    valid: true,
    method,
    method_label: methodLabel,
    bmr_kcal: roundKcal(bmrKcal),
    daily_energy_kcal: roundKcal(dailyEnergyKcal),
    activity_factor: activityFactor
  };
}

export function applyDailyEnergyToSummary(summary, profile) {
  const intakeKcal = Number(summary?.intake_kcal || 0);
  const activityKcal = Number(summary?.activity_kcal || 0);
  const dailyEnergy = calculateDailyEnergy(profile);
  const serverNetKcal = Number(summary?.net_kcal || 0);
  const totalBurnKcal = activityKcal + dailyEnergy.daily_energy_kcal;
  const netKcal = intakeKcal - totalBurnKcal;

  return {
    ...(summary || {}),
    intake_kcal: intakeKcal,
    activity_kcal: activityKcal,
    net_kcal: netKcal,
    daily_energy_kcal: dailyEnergy.daily_energy_kcal,
    total_burn_kcal: totalBurnKcal,
    extra: {
      ...(summary?.extra || {}),
      server_net_kcal: serverNetKcal,
      daily_energy: dailyEnergy
    }
  };
}
