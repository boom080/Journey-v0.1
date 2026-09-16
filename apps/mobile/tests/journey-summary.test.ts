import type { FoodRecord, JourneyDay, WeightRecord } from '@journey/contracts';

import { estimateEnergyEquivalent, summarizeJourneyDays } from '@/lib/journey-summary';

function weightRecord(id: string, measuredAt: string, weightKg: number): WeightRecord {
  return {
    id,
    measured_at: measuredAt,
    record_date: measuredAt.slice(0, 10),
    weight_kg: weightKg,
    note: null,
    source: 'manual',
    version: 1,
    created_at: measuredAt,
    updated_at: measuredAt,
  };
}

function foodRecord(): FoodRecord {
  return {
    id: 'food-1',
    recorded_at: '2026-09-02T04:00:00Z',
    record_date: '2026-09-02',
    meal_type: 'lunch',
    name: '午餐',
    energy_kcal: 1250,
    source: 'manual',
    version: 1,
    created_at: '2026-09-02T04:00:00Z',
    updated_at: '2026-09-02T04:00:00Z',
  };
}

function day(weights: WeightRecord[], withFood = false): JourneyDay {
  return {
    date: '2026-09-02',
    intake_kcal: withFood ? 1250 : 0,
    activity_kcal: withFood ? 500 : 0,
    net_kcal: withFood ? 750 : 0,
    food_records: withFood ? [foodRecord()] : [],
    activity_records: [],
    weight_records: weights,
  };
}

test('one weight measurement is insufficient to calculate a change', () => {
  expect(summarizeJourneyDays([day([
    weightRecord('weight-1', '2026-09-02T08:00:00Z', 85),
  ])]).weightChange).toBeNull();
});

test('weight change uses the earliest and latest measurements in the selected range', () => {
  expect(summarizeJourneyDays([day([
    weightRecord('weight-2', '2026-09-02T08:00:00Z', 84.2),
    weightRecord('weight-1', '2026-09-01T08:00:00Z', 85),
  ])]).weightChange).toBeCloseTo(-0.8);
});

test('energy equivalent uses only days with food records and does not claim body composition', () => {
  const estimate = estimateEnergyEquivalent([day([], true), day([])], 1865);
  expect(estimate).toEqual({
    balanceKcal: -1115,
    equivalentKg: -1115 / 7700,
    loggedDays: 1,
  });
  expect(estimateEnergyEquivalent([day([])], 1865)).toBeNull();
  expect(estimateEnergyEquivalent([day([], true)], null)).toBeNull();
});
