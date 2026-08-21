import type { HomeToday, JourneyProfile } from '@journey/contracts';

const FORMULA: HomeToday['resting_energy']['formula'] = 'mifflin-st-jeor-1990';

function ageOn(birthDate: string, onDate: string): number {
  const birth = birthDate.split('-').map(Number);
  const current = onDate.split('-').map(Number);
  let age = current[0]! - birth[0]!;
  if (current[1]! < birth[1]! || (current[1] === birth[1] && current[2]! < birth[2]!)) age -= 1;
  return age;
}

export function estimateRestingEnergy(
  profile: JourneyProfile,
  weightKg: number | null,
  onDate: string,
): HomeToday['resting_energy'] {
  const missing = [
    ['sex', profile.sex], ['birth_date', profile.birth_date],
    ['height_cm', profile.height_cm], ['weight_kg', weightKg],
  ].filter(([, value]) => value == null).map(([name]) => String(name));
  if (missing.length) return {
    status: 'missing_profile', kcal_per_day: null, formula: FORMULA, age_years: null,
    missing_fields: missing, note: '补充性别、生日、身高和体重后可生成静息消耗估算。',
  };
  if (profile.sex !== 'female' && profile.sex !== 'male') return {
    status: 'unsupported_profile', kcal_per_day: null, formula: FORMULA, age_years: null,
    missing_fields: [], note: '当前标准公式只提供女性/男性系数，因此不对该性别选项强行生成单一数值。',
  };
  const age = ageOn(profile.birth_date!, onDate);
  if (age < 19 || age > 78) return {
    status: 'unsupported_profile', kcal_per_day: null, formula: FORMULA, age_years: age,
    missing_fields: [], note: '该公式的原始健康成人样本年龄为 19—78 岁，当前不输出估算。',
  };
  const kcal = 10 * weightKg! + 6.25 * profile.height_cm! - 5 * age + (profile.sex === 'male' ? 5 : -161);
  return {
    status: 'available', kcal_per_day: Math.round(kcal * 100) / 100, formula: FORMULA,
    age_years: age, missing_fields: [],
    note: '静息能量消耗预测值，不是代谢测量，也不等于包含日常活动和食物热效应的 TDEE。',
  };
}
