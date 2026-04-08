import React, { useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import { getMyProfile, updateMyProfile } from "../../services/profile";
import { clearAllSessionData, getCachedProfile, getSession, saveCachedProfile } from "../../store/session";
import { ROUTES, relaunchTo } from "../../utils/router";
import { toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

const goals = ["减脂", "增肌", "维持"];

export default function ProfilePage() {
  const ready = usePageGuard("activated");
  const [form, setForm] = useState(getCachedProfile() || {});
  const [session, setSession] = useState(getSession());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function loadProfile() {
    try {
      setLoading(true);
      setError("");
      const profile = await getMyProfile();
      setForm(profile);
      setSession(getSession());
      saveCachedProfile(profile);
    } catch (err) {
      setError(toErrorMessage(err, "资料拉取失败，已展示缓存"));
    } finally {
      setLoading(false);
    }
  }

  useDidShow(() => {
    if (ready) {
      loadProfile();
    }
  });

  async function handleSave() {
    try {
      setSaving(true);
      setError("");
      const payload = await updateMyProfile({
        nickname: form.nickname || "",
        goal: form.goal || "维持",
        height: Number(form.height) || 0,
        weight: Number(form.weight) || 0
      });
      setForm(payload);
      saveCachedProfile(payload);
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

  if (!ready) {
    return (
      <View className="page">
        <View className="section-card">
          <Text className="hint-text">页面准备中...</Text>
        </View>
      </View>
    );
  }

  return (
    <View className="page">
      <View className="page-shell">
        <View>
          <Text className="page-title">我的</Text>
          <Text className="page-subtitle">管理你的资料、目标和使用偏好。</Text>
        </View>

        <View className="section-card">
          <Text className="record-panel-title">账号信息</Text>
          <View className="readonly-box spacer-top">当前账号：{session.user?.openid || "未同步"}</View>
        </View>

        <View className="section-card profile-block">
          <Text className="record-panel-title">基础资料</Text>
          <View className="field-group">
            <Text className="field-label">昵称</Text>
            <Input
              className="field-input"
              value={form.nickname || ""}
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
                  onClick={() => updateField("goal", goal)}
                >
                  {goal}
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
              placeholder="请输入当前体重（kg）"
              onInput={(e) => updateField("weight", e.detail.value)}
            />
          </View>

          {loading ? <Text className="hint-text">资料同步中...</Text> : null}
          {error ? <Text className="error-text">{error}</Text> : null}

          <View className="button-row">
            <Button className="primary-button button-block" loading={saving} onClick={handleSave}>
              保存资料
            </Button>
          </View>
        </View>

        <View className="section-card">
          <Text className="record-panel-title">账号操作</Text>
          <Text className="hint-text">退出后会清理 token、profile、首页缓存与里程缓存。</Text>
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
