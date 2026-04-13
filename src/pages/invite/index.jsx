import React, { useState } from "react";
import { Button, Input, Text, View } from "@tarojs/components";
import { verifyInvite } from "../../services/auth";
import { saveCachedProfile, saveSession } from "../../store/session";
import { ROUTES, relaunchTo } from "../../utils/router";
import { toErrorMessage } from "../../utils/day";
import { usePageGuardState } from "../../utils/use-page-guard";

export default function InvitePage() {
  const guard = usePageGuardState("invite");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("");

  async function handleVerify() {
    if (!inviteCode.trim()) {
      setError("请输入邀请码");
      return;
    }

    let hasNavigated = false;

    try {
      setLoading(true);
      setError("");
      setStatusText("正在校验邀请码...");
      const payload = await verifyInvite(inviteCode.trim());

      saveSession({
        user: payload.user || null,
        isActivated: true,
        inviteCodeId: payload.user?.invite_code_id || payload.invite_code_id || ""
      });

      if (payload.user) {
        saveCachedProfile(payload.user);
      }

      setStatusText("邀请码通过，正在进入首页...");
      await relaunchTo(ROUTES.home);
      hasNavigated = true;
    } catch (err) {
      setError(toErrorMessage(err, "邀请码校验失败"));
      setStatusText("");
    } finally {
      if (!hasNavigated) {
        setLoading(false);
      }
    }
  }

  if (!guard.ready || loading) {
    return (
      <View className="page-status-shell">
        <View className="page-status-card">
          <Text className="page-status-title">正在检查邀请码</Text>
          <Text className="page-status-message">{statusText || guard.message || "正在准备邀请码页面..."}</Text>
        </View>
      </View>
    );
  }

  return (
    <View className="page">
      <View className="page-shell page-shell--airy">
        <View className="hero-card hero-card--entry">
          <Text className="eyebrow">邀请码</Text>
          <View className="page-title">输入邀请码，继续使用</View>
          <View className="page-subtitle">验证通过后，会自动进入首页开始记录。</View>
          <View className="hero-pill-row">
            <Text className="hero-badge">验证后自动进入首页</Text>
            <Text className="hero-badge">继续当前账号使用</Text>
          </View>
        </View>

        <View className="section-card section-card--soft">
          <View className="section-heading">
            <Text className="section-title">输入邀请码</Text>
            <Text className="section-desc">邀请码通过后，会自动完成激活。</Text>
          </View>

          <View className="step-list">
            <View className="step-item">
              <Text className="step-index">1</Text>
              <View className="step-main">
                <Text className="step-title">输入邀请码</Text>
                <Text className="step-note">确认邀请码可用后，会与当前账号完成绑定。</Text>
              </View>
            </View>
            <View className="step-item">
              <Text className="step-index">2</Text>
              <View className="step-main">
                <Text className="step-title">完成校验</Text>
                <Text className="step-note">通过后将保留激活状态，后续可直接进入首页。</Text>
              </View>
            </View>
          </View>

          <View className="field-group">
            <Text className="field-label">邀请码</Text>
            <Input
              className="field-input"
              value={inviteCode}
              maxlength={32}
              placeholder="请输入邀请码"
              onInput={(event) => {
                setInviteCode(event.detail.value);
                if (error) {
                  setError("");
                }
              }}
            />
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
          <View className="button-row">
            <Button
              className="primary-button button-block"
              loading={loading}
              disabled={loading}
              onClick={handleVerify}
            >
              校验并激活
            </Button>
          </View>
          <View className="info-banner">
            <Text className="hint-text">{statusText || "激活成功后，会自动进入首页。"}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}
