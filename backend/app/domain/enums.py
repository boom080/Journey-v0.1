from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class IdentityKind(StrEnum):
    EMAIL = "email"
    USERNAME = "username"
    PHONE = "phone"


class GoalKind(StrEnum):
    LOSE_FAT = "lose_fat"
    GAIN_MUSCLE = "gain_muscle"
    MAINTAIN = "maintain"


class RecordSource(StrEnum):
    MANUAL = "manual"
    AGENT = "agent"
    IMAGE = "image"
    IMPORT = "import"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    OTHER = "other"


class ActivityIntensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"
