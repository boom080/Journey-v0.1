import React, { useState } from "react";
import Taro from "@tarojs/taro";
import { Button, Text, View } from "@tarojs/components";
import { wechatLogin } from "../../services/auth";
import { saveCachedProfile, saveSession } from "../../store/session";
import { ROUTES, relaunchTo } from "../../utils/router";
import { toErrorMessage } from "../../utils/day";
import { usePageGuardState } from "../../utils/use-page-guard";

export default function AuthPage() {
  const guard = usePageGuardState("guest");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("");

  async function handleWechatLogin() {
    if (loading) {
      return;
    }

    let hasNavigated = false;

    try {
      setLoading(true);
      setError("");
      setStatusText("正在请求微信登录...");

      const loginResult = await Taro.login();
      if (!loginResult?.code) {
        throw new Error("微信登录未返回有效 code");
      }

      setStatusText("正在校验登录信息...");
      const payload = await wechatLogin(loginResult.code);

      saveSession({
        token: payload.access_token || payload.token || "",
        user: payload.user || null,
        isActivated: Boolean(payload.user?.is_activated),
        inviteCodeId: payload.user?.invite_code_id || ""
      });

      if (payload.user) {
        saveCachedProfile(payload.user);
      }

      setStatusText(payload.user?.is_activated ? "登录完成，正在进入首页..." : "登录完成，正在进入邀请码页...");
      await relaunchTo(payload.user?.is_activated ? ROUTES.home : ROUTES.invite);
      hasNavigated = true;
    } catch (err) {
      setError(toErrorMessage(err, "微信登录失败，请稍后再试"));
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
          <Text className="page-status-title">正在进入 Journey</Text>
          <Text className="page-status-message">{statusText || guard.message || "正在准备登录..."}</Text>
        </View>
      </View>
    );
  }

  return (
    <View className="page">
      <View className="page-shell page-shell--airy">
        <View className="hero-card hero-card--entry">
          <Text className="eyebrow">Journey / 即刻</Text>
          <View className="page-title">把今天轻轻记下来</View>
          <View className="page-subtitle">先完成微信登录，再继续进入正式使用流程。</View>
          <View className="hero-pill-row">
            <Text className="hero-badge">首页 / 里程 / 我的</Text>
            <Text className="hero-badge">吃了什么 / 做了什么</Text>
          </View>
        </View>

        <View className="section-card section-card--soft">
          <View className="section-heading">
            <Text className="section-title">开始使用</Text>
            <Text className="section-desc">完成登录后，会自动继续到下一步。</Text>
          </View>

          <View className="step-list">
            <View className="step-item">
              <Text className="step-index">1</Text>
              <View className="step-main">
                <Text className="step-title">微信登录</Text>
                <Text className="step-note">先确认当前账号，方便后续自动恢复登录状态。</Text>
              </View>
            </View>
            <View className="step-item">
              <Text className="step-index">2</Text>
              <View className="step-main">
                <Text className="step-title">邀请码激活</Text>
                <Text className="step-note">通过后即可进入首页开始记录。</Text>
              </View>
            </View>
            <View className="step-item">
              <Text className="step-index">3</Text>
              <View className="step-main">
                <Text className="step-title">开始记录</Text>
                <Text className="step-note">从“吃了什么”和“做了什么”开始，首页和里程会自动联动。</Text>
              </View>
            </View>
          </View>

          {error ? <Text className="error-text">{error}</Text> : null}
          <View className="button-row">
            <Button
              className="primary-button button-block"
              loading={loading}
              disabled={loading}
              onClick={handleWechatLogin}
            >
              微信登录
            </Button>
          </View>
          <View className="info-banner">
            <Text className="hint-text">{statusText || "登录成功后，会根据是否已激活自动进入下一步。"}</Text>
          </View>
        </View>
      </View>
    </View>
  );
}
