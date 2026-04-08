import React, { useState } from "react";
import { Button, Input, Text, View } from "@tarojs/components";
import { verifyInvite } from "../../services/auth";
import { saveCachedProfile, saveSession } from "../../store/session";
import { ROUTES, replaceRoute } from "../../utils/router";
import { toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

export default function InvitePage() {
  const ready = usePageGuard("invite");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleVerify() {
    if (!inviteCode.trim()) {
      setError("请输入邀请码");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const payload = await verifyInvite(inviteCode.trim());

      saveSession({
        user: payload.user || null,
        isActivated: true,
        inviteCodeId: payload.user?.invite_code_id || payload.invite_code_id || ""
      });

      if (payload.user) {
        saveCachedProfile(payload.user);
      }

      replaceRoute(ROUTES.home);
    } catch (err) {
      setError(toErrorMessage(err, "邀请码校验失败"));
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
          <Text className="eyebrow">邀请码准入</Text>
          <View className="page-title">未通过邀请码前，不进入主页面</View>
          <View className="page-subtitle">
            邀请码默认单次使用，支持状态、过期时间和使用者绑定；前端这里先只做输入与校验。
          </View>
        </View>

        <View className="section-card">
          <Text className="section-title">输入邀请码</Text>
          <View className="field-group">
            <Text className="field-label">邀请码</Text>
            <Input
              className="field-input"
              value={inviteCode}
              maxlength={32}
              placeholder="请输入邀请码"
              onInput={(event) => {
                setInviteCode(event.detail.value);
                if (error) setError("");
              }}
            />
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
          <View className="button-row">
            <Button className="primary-button button-block" loading={loading} onClick={handleVerify}>
              校验并激活
            </Button>
          </View>
        </View>
      </View>
    </View>
  );
}
