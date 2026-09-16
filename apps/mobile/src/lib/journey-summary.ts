import type { JourneyDay } from '@journey/contracts';

const KCAL_PER_KG_ENERGY_EQUIVALENT = 7700;

export type EnergyEquivalentEstimate = {
  balanceKcal: number;
  equivalentKg: number;
  loggedDays: number;
};

export function summarizeJourneyDays(days: JourneyDay[]) {
  const totals = days.reduce((acc, day) => ({
    intake: acc.intake + day.intake_kcal,
    activity: acc.activity + day.activity_kcal,
    records: acc.records + day.food_records.length + day.activity_records.length + day.weight_records.length,
  }), { intake: 0, activity: 0, records: 0 });
  const weights = days
    .flatMap((day) => day.weight_records)
    .sort((left, right) => new Date(left.measured_at).getTime() - new Date(right.measured_at).getTime());
  const firstWeight = weights[0];
  const latestWeight = weights.at(-1);
  return {
    ...totals,
    weightChange: weights.length >= 2 && firstWeight && latestWeight
      ? latestWeight.weight_kg - firstWeight.weight_kg
      : null,
  };
}

export function estimateEnergyEquivalent(
  days: JourneyDay[],
  restingEnergyKcalPerDay: number | null | undefined,
): EnergyEquivalentEstimate | null {
  if (restingEnergyKcalPerDay == null) return null;
  const loggedDays = days.filter((day) => day.food_records.length > 0);
  if (!loggedDays.length) return null;
  const balanceKcal = loggedDays.reduce(
    (total, day) => total + day.intake_kcal - day.activity_kcal - restingEnergyKcalPerDay,
    0,
  );
  return {
    balanceKcal,
    equivalentKg: balanceKcal / KCAL_PER_KG_ENERGY_EQUIVALENT,
    loggedDays: loggedDays.length,
  };
}
