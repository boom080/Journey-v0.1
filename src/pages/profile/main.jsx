import React, { useState } from "react";
import Taro, { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import { getJourneyDays } from "../../services/journey";
import { getMyProfile, updateMyProfile } from "../../services/profile";
import {
  clearAllSessionData,
  getCachedJourney,
  getCachedProfile,
  getSession,
  saveCachedJourney,
  saveCachedProfile
} from "../../store/session";
import { safeList, toErrorMessage } from "../../utils/day";
import { calculateDailyEnergy } from "../../utils/daily-energy";
import {
  DEFAULT_PROFILE_GOAL,
  getGenderLabel,
  PROFILE_GENDER_OPTIONS
} from "../../utils/profile";
import { ROUTES, relaunchTo } from "../../utils/router";
import { usePageGuardState } from "../../utils/use-page-guard";
import { formatWeightDelta, getYesterdayWeightTrend } from "../../utils/weight-trend";

const goals = ["减脂", "增肌", DEFAULT_PROFILE_GOAL];

function formatDisplayValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "未填写";
  }

  return suffix ? `${value}${suffix}` : value;
}

function formatDailyEnergy(dailyEnergy) {
  return dailyEnergy.daily_energy_kcal > 0
    ? `${dailyEnergy.daily_energy_kcal} kcal/天`
    : "补充身高体重后自动计算";
}

function formatWeightValue(value) {
  const amount = Number(value);
  return Number.isFinite(amount) && amount > 0 ? `${amount.toFixed(1)} kg` : "未填写";
}

function buildJourneySnapshot(payload) {
  return {
    items: safeList(payload?.items),
    nextCursor: payload?.next_cursor || "",
    hasMore: Boolean(payload?.has_more)
  };
}

export default function ProfilePage() {
  const guard = usePageGuardState("activated");
  const [form, setForm] = useState(getCachedProfile() || {});
  const [journey, setJourney] = useState(getCachedJourney());
  const [session] = useState(getSession());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saveNotice, setSaveNotice] = useState("");
  const [isEditingProfile, setIsEditingProfile] = useState(false);

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function loadProfile() {
    try {
      setLoading(true);
      setError("");
      setSaveNotice("");

      const [profileResult, journeyResult] = await Promise.allSettled([
        getMyProfile(),
        getJourneyDays({ page_size: 7 })
      ]);

      if (profileResult.status !== "fulfilled") {
        throw profileResult.reason;
      }

      const profile = profileResult.value;
      setForm(profile);
      saveCachedProfile(profile);
      setIsEditingProfile(false);

      if (journeyResult.status === "fulfilled") {
        const nextJourney = buildJourneySnapshot(journeyResult.value);
        setJourney(nextJourney);
        saveCachedJourney(nextJourney);
      } else {
        setJourney(getCachedJourney());
      }
    } catch (err) {
      setError(toErrorMessage(err, "资料拉取失败，已展示缓存"));
    } finally {
      setLoading(false);
    }
  }

  useDidShow(() => {
    if (guard.ready) {
      loadProfile();
    }
  });

  function handleStartEditing() {
    setError("");
    setSaveNotice("");
    setIsEditingProfile(true);
  }

  function handleCancelEditing() {
    setForm(getCachedProfile() || {});
    setError("");
    setSaveNotice("");
    setIsEditingProfile(false);
  }

  async function handleSave() {
    try {
      setSaving(true);
      setError("");
      setSaveNotice("");
      const payload = await updateMyProfile(form);
      setForm(payload);
      saveCachedProfile(payload);
      setIsEditingProfile(false);
      setSaveNotice("资料已保存，下次进入也会按这份资料展示。");
      Taro.showToast({
        title: "资料已保存",
        icon: "success"
      });
    } catch (err) {
      setError(toErrorMessage(err, "资料保存失败"));
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    clearAllSessionData();
    relaunchTo(ROUTES.auth);
  }

  const dailyEnergy = calculateDailyEnergy(form);
  const yesterdayTrend = getYesterdayWeightTrend(journey);
  const expectedWeightChange = yesterdayTrend.valid
    ? formatWeightDelta(yesterdayTrend.delta_kg)
    : "暂无昨日数据";

  if (!guard.ready) {
    return (
      <View className="page-status-shell">
        <View className="page-status-card">
          <Text className="page-status-title">正在准备资料页</Text>
          <Text className="page-status-message">{guard.message || "正在同步账号与资料状态..."}</Text>
        </View>
      </View>
    );
  }

  return (
    <View className="page">
      <View className="page-shell">
        <View className="hero-card hero-card--subpage">
          <Text className="eyebrow">身体概况</Text>
          <View className="profile-hero-grid">
            <View className="profile-hero-metric">
              <Text className="profile-hero-label">当前体重</Text>
              <Text className="profile-hero-value">{formatWeightValue(form.weight)}</Text>
            </View>
            <View className="profile-hero-metric">
              <Text className="profile-hero-label">预计今日变化</Text>
              <Text className="profile-hero-value">{expectedWeightChange}</Text>
            </View>
          </View>
          <Text className="profile-hero-note">按昨日热量结余折算，仅作参考</Text>
          <View className="hero-pill-row">
            <Text className="hero-badge">当前目标：{form.goal || DEFAULT_PROFILE_GOAL}</Text>
            <Text className="hero-badge">日常消耗：{formatDailyEnergy(dailyEnergy)}</Text>
          </View>
        </View>

        <View className="section-card profile-block">
          <View className="section-heading section-heading--between">
            <View>
              <Text className="record-panel-title">基础资料</Text>
              <Text className="section-desc">默认展示已保存资料，需要时再进入编辑。</Text>
            </View>
            <Text className={`status-pill ${isEditingProfile ? "status-pill--accent" : "status-pill--surface"}`}>
              {isEditingProfile ? "编辑态" : "查看态"}
            </Text>
          </View>

          {isEditingProfile ? (
            <View className="form-shell">
              <View className="field-group">
                <Text className="field-label">昵称</Text>
                <Input
                  className="field-input"
                  value={form.nickname || ""}
                  disabled={saving}
                  placeholder="请输入昵称"
                  onInput={(e) => updateField("nickname", e.detail.value)}
                />
              </View>

              <View className="field-group">
                <Text className="field-label">目标</Text>
                <View className="inline-chip-row">
                  {goals.map((goal) => (
                    <Text
                      key={goal}
                      className={`chip ${form.goal === goal ? "chip-active" : ""}`}
                      onClick={() => {
                        if (!saving) {
                          updateField("goal", goal);
                        }
                      }}
                    >
                      {goal}
                    </Text>
                  ))}
                </View>
              </View>

              <View className="field-group">
                <Text className="field-label">性别</Text>
                <View className="inline-chip-row">
                  {PROFILE_GENDER_OPTIONS.map((item) => (
                    <Text
                      key={item.value}
                      className={`chip ${form.gender === item.value ? "chip-active" : ""}`}
                      onClick={() => {
                        if (!saving) {
                          updateField("gender", item.value);
                        }
                      }}
                    >
                      {item.label}
                    </Text>
                  ))}
                </View>
              </View>

              <View className="field-group">
                <Text className="field-label">身高</Text>
                <Input
                  className="field-input"
                  type="number"
                  value={String(form.height || "")}
                  disabled={saving}
                  placeholder="请输入身高（cm）"
                  onInput={(e) => updateField("height", e.detail.value)}
                />
              </View>

              <View className="field-group">
                <Text className="field-label">体重</Text>
                <Input
                  className="field-input"
                  type="number"
                  value={String(form.weight || "")}
                  disabled={saving}
                  placeholder="请输入当前体重（kg）"
                  onInput={(e) => updateField("weight", e.detail.value)}
                />
              </View>

              <View className="field-group">
                <Text className="field-label">体脂率</Text>
                <Input
                  className="field-input"
                  type="digit"
                  value={String(form.body_fat_rate || "")}
                  disabled={saving}
                  placeholder="可选，例如 18.5"
                  onInput={(e) => updateField("body_fat_rate", e.detail.value)}
                />
                <Text className="helper-text">选填。填写后会优先按体脂率估算日常消耗。</Text>
              </View>
            </View>
          ) : (
            <View className="profile-display-list">
              <View className="profile-display-row">
                <Text className="field-label">昵称</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDisplayValue(form.nickname)}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">目标</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDisplayValue(form.goal)}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">性别</Text>
                <View className="readonly-box">
                  <Text className="field-value">{getGenderLabel(form.gender)}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">身高</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDisplayValue(form.height, " cm")}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">体重</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDisplayValue(form.weight, " kg")}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">体脂率</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDisplayValue(form.body_fat_rate, " %")}</Text>
                </View>
              </View>

              <View className="profile-display-row">
                <Text className="field-label">日常消耗</Text>
                <View className="readonly-box">
                  <Text className="field-value">{formatDailyEnergy(dailyEnergy)}</Text>
                </View>
              </View>
            </View>
          )}

          {loading ? <Text className="hint-text">资料同步中...</Text> : null}
          {error ? <Text className="error-text">{error}</Text> : null}
          {saveNotice ? (
            <View className="info-banner">
              <Text className="hint-text">{saveNotice}</Text>
            </View>
          ) : null}

          <View className="section-actions">
            {isEditingProfile ? (
              <>
                <Button className="secondary-button" disabled={saving} onClick={handleCancelEditing}>
                  取消修改
                </Button>
                <Button className="primary-button" loading={saving} disabled={saving} onClick={handleSave}>
                  保存资料
                </Button>
              </>
            ) : (
              <Button className="secondary-button button-block" onClick={handleStartEditing}>
                修改资料
              </Button>
            )}
          </View>
        </View>

        <View className="section-card">
          <View className="section-heading">
            <Text className="record-panel-title">账号操作</Text>
            <Text className="section-desc">
              当前账号已{session.isActivated ? "完成激活" : "未激活"}。退出后会清理本地登录和缓存数据。
            </Text>
          </View>
          <View className="button-row">
            <Button className="danger-button" onClick={handleLogout}>
              退出登录
            </Button>
          </View>
        </View>
      </View>
    </View>
  );
}
