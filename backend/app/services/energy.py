from datetime import date

from app.schemas.aggregates import RestingEnergyEstimate

FORMULA_VERSION = "mifflin-st-jeor-1990"
SUPPORTED_MIN_AGE = 19
SUPPORTED_MAX_AGE = 78


def age_on(birth_date: date, on_date: date) -> int:
    return on_date.year - birth_date.year - (
        (on_date.month, on_date.day) < (birth_date.month, birth_date.day)
    )


def estimate_resting_energy(
    *,
    sex: str | None,
    birth_date: date | None,
    height_cm: float | None,
    weight_kg: float | None,
    on_date: date,
) -> RestingEnergyEstimate:
    """Return an explainable REE estimate; never silently invent profile inputs."""

    missing_fields = [
        name
        for name, value in (
            ("sex", sex),
            ("birth_date", birth_date),
            ("height_cm", height_cm),
            ("weight_kg", weight_kg),
        )
        if value is None
    ]
    if missing_fields:
        return RestingEnergyEstimate(
            status="missing_profile",
            formula=FORMULA_VERSION,
            missing_fields=missing_fields,
            note="补充性别、生日、身高和体重后可生成静息消耗估算。",
        )

    if sex not in {"female", "male"}:
        return RestingEnergyEstimate(
            status="unsupported_profile",
            formula=FORMULA_VERSION,
            missing_fields=[],
            note="当前标准公式只提供女性/男性系数，因此不对该性别选项强行生成单一数值。",
        )

    assert birth_date is not None
    assert height_cm is not None
    assert weight_kg is not None
    age_years = age_on(birth_date, on_date)
    if not SUPPORTED_MIN_AGE <= age_years <= SUPPORTED_MAX_AGE:
        return RestingEnergyEstimate(
            status="unsupported_profile",
            formula=FORMULA_VERSION,
            age_years=age_years,
            missing_fields=[],
            note=f"该公式的原始健康成人样本年龄为 {SUPPORTED_MIN_AGE}—{SUPPORTED_MAX_AGE} 岁，当前不输出估算。",
        )

    sex_constant = 5 if sex == "male" else -161
    kcal_per_day = 10 * weight_kg + 6.25 * height_cm - 5 * age_years + sex_constant
    return RestingEnergyEstimate(
        status="available",
        formula=FORMULA_VERSION,
        kcal_per_day=round(kcal_per_day, 2),
        age_years=age_years,
        missing_fields=[],
        note="静息能量消耗预测值，不是代谢测量，也不等于包含日常活动和食物热效应的 TDEE。",
    )
