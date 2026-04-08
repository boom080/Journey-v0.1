import React, { useState } from "react";
import Taro from "@tarojs/taro";
import { Button, Text, View } from "@tarojs/components";
import { wechatLogin } from "../../services/auth";
import { saveCachedProfile, saveSession } from "../../store/session";
import { ROUTES, replaceRoute } from "../../utils/router";
import { toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

export default function AuthPage() {
  const ready = usePageGuard("guest");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleWechatLogin() {
    if (loading) {
      return;
    }

    try {
      setLoading(true);
      setError("");

      const loginResult = await Taro.login();
      if (!loginResult?.code) {
        throw new Error("微信登录未返回有效 code");
      }

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

      replaceRoute(payload.user?.is_activated ? ROUTES.home : ROUTES.invite);
    } catch (err) {
      setError(toErrorMessage(err, "微信登录失败，请稍后再试"));
    } finally {
      setLoading(false);
    }
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
        <View className="hero-card">
          <Text className="eyebrow">Journey / 即刻</Text>
          <View className="page-title">微信登录后，再进入邀请码准入</View>
          <View className="page-subtitle">
            主链路固定为：微信登录、邀请码激活、记录饮食与活动、首页联动、里程多天回看。
          </View>
        </View>

        <View className="section-card">
          <Text className="section-title">开始使用</Text>
          <Text className="section-desc">
            这一版只保留微信登录，不再提供邮箱或密码登录。
          </Text>
          <View className="inline-chip-row">
            <Text className="chip chip-active">1. 微信登录</Text>
            <Text className="chip">2. 邀请码激活</Text>
            <Text className="chip">3. 开始记录</Text>
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
          <View className="button-row">
            <Button className="primary-button button-block" loading={loading} onClick={handleWechatLogin}>
              微信登录
            </Button>
          </View>
        </View>
      </View>
    </View>
  );
}
