import React, { useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { Text, View } from "@tarojs/components";
import { generateHomeSuggestion } from "../../services/ai";
import { getHomeSummary } from "../../services/home";
import { getCachedHome, getCachedProfile, saveCachedHome } from "../../store/session";
import { createAiState, normalizeAiResult } from "../../utils/ai";
import { openRoute, ROUTES } from "../../utils/router";
import { safeList, toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

const defaultSummary = {
  today_date: "",
  today_summary: "今天还没有记录，先记下吃了什么或做了什么。",
  goal_suggestion: "完成记录后，首页会给出更贴近目标的建议。",
  intake_kcal: 0,
  activity_kcal: 0,
  net_kcal: 0,
  recent_updates: [],
  extra: {}
};

function formatNetKcal(value) {
  const amount = Number(value || 0);
  return `${amount >= 0 ? "+" : ""}${amount} kcal`;
}

export default function HomePage() {
  const ready = usePageGuard("activated");
  const cachedHome = getCachedHome() || defaultSummary;
  const [data, setData] = useState(cachedHome);
  const [profile, setProfile] = useState(getCachedProfile());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [suggestionState, setSuggestionState] = useState({
    ...createAiState("home_suggestion"),
    result: normalizeAiResult(cachedHome?.extra?.aiSuggestion, "home_suggestion")
  });

  async function loadHome() {
    try {
      setLoading(true);
      setError("");
      const payload = await getHomeSummary();
      const summaryData = {
        ...defaultSummary,
        ...(payload || {}),
        extra: payload?.extra || {}
      };

      setData(summaryData);
      setProfile(getCachedProfile());

      try {
        setSuggestionState((prev) => ({
          ...prev,
          loading: true,
          error: ""
        }));

        const aiSuggestion = await generateHomeSuggestion({
          today_summary: summaryData.today_summary,
          intake_kcal: summaryData.intake_kcal,
          activity_kcal: summaryData.activity_kcal,
          net_kcal: summaryData.net_kcal,
          recent_updates: summaryData.recent_updates,
          extra: summaryData.extra || {}
        });

        const normalizedSuggestion = normalizeAiResult(aiSuggestion, "home_suggestion");
        const mergedData = {
          ...summaryData,
          extra: {
            ...(summaryData.extra || {}),
            aiSuggestion: normalizedSuggestion
          }
        };

        setData(mergedData);
        saveCachedHome(mergedData);
        setSuggestionState({
          ...createAiState("home_suggestion"),
          result: normalizedSuggestion
        });
      } catch (suggestionError) {
        saveCachedHome(summaryData);
        setSuggestionState((prev) => ({
          ...prev,
          loading: false,
          error: toErrorMessage(suggestionError, "AI 建议暂时不可用，已使用默认建议"),
          result: normalizeAiResult(prev.result, "home_suggestion")
        }));
      }
    } catch (err) {
      setError(toErrorMessage(err, "首页摘要获取失败，已展示本地缓存"));
    } finally {
      setLoading(false);
      setSuggestionState((prev) => ({
        ...prev,
        loading: false
      }));
    }
  }

  useDidShow(() => {
    if (ready) {
      loadHome();
    }
  });

  if (!ready) {
    return (
      <View className="page">
        <View className="section-card">
          <Text className="hint-text">页面准备中...</Text>
        </View>
      </View>
    );
  }

  const suggestionText =
    suggestionState.result?.summary ||
    data.extra?.aiSuggestion?.summary ||
    data.goal_suggestion ||
    defaultSummary.goal_suggestion;

  return (
    <View className="page">
      <View className="page-shell">
        <View className="hero-card">
          <View className="hero-meta">
            <Text className="eyebrow">{data.today_date || "今日概览"}</Text>
            <Text className="hero-badge">当前目标: {profile?.goal || "维持体重"}</Text>
          </View>

          <View className="hero-main">
            <Text className="page-title">你好，{profile?.nickname || "即刻用户"}</Text>
            <Text className="hero-kcal">今日热量结余</Text>
            <Text className="hero-balance">{formatNetKcal(data.net_kcal)}</Text>
            <Text className="hero-note">{data.today_summary || defaultSummary.today_summary}</Text>
          </View>
        </View>

        <View className="action-card" onClick={() => openRoute(ROUTES.food)}>
          <View className="action-icon">🍱</View>
          <View className="action-content">
            <Text className="action-title">吃了什么</Text>
            <Text className="action-desc">手动记录 / 一句话估算 / 预留图片识别入口</Text>
          </View>
          <Text className="action-arrow">›</Text>
        </View>

        <View className="action-card" onClick={() => openRoute(ROUTES.activity)}>
          <View className="action-icon">🏃</View>
          <View className="action-content">
            <Text className="action-title">做了什么</Text>
            <Text className="action-desc">手动记录 / 一句话估算 / 预留 OCR 入口</Text>
          </View>
          <Text className="action-arrow">›</Text>
        </View>

        <View className="section-card">
          <Text className="section-title">热量概况</Text>
          <Text className="section-desc">来自今日真实汇总</Text>
          <View className="summary-grid">
            <View className="summary-card">
              <Text className="grid-label">净结余</Text>
              <Text className="summary-value">{Number(data.net_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
            <View className="summary-card">
              <Text className="grid-label">活动消耗</Text>
              <Text className="summary-value">{Number(data.activity_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
            <View className="summary-card">
              <Text className="grid-label">已摄入</Text>
              <Text className="summary-value">{Number(data.intake_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
          </View>
        </View>

        <View className="section-card">
          <Text className="section-title">今日更新</Text>
          <Text className="section-desc">{data.today_date || "今天"} 的最新真实记录</Text>
          <View className="update-list">
            {safeList(data.recent_updates).length ? (
              safeList(data.recent_updates).map((item, index) => {
                const negative = String(item.kcal || "").startsWith("-");
                return (
                  <View className="update-row" key={`${item.title}-${index}`}>
                    <Text className="update-time">{item.time_text || "--:--"}</Text>
                    <View className="update-main">
                      <Text className="update-title">{item.title}</Text>
                      <Text className="update-desc">{item.description}</Text>
                    </View>
                    <Text className={`update-kcal ${negative ? "list-kcal-negative" : "list-kcal-positive"}`}>
                      {item.kcal || ""}
                    </Text>
                  </View>
                );
              })
            ) : (
              <Text className="empty-text">今天还没有真实记录，先去添加一条饮食或活动。</Text>
            )}
          </View>
          {loading ? <Text className="hint-text">首页摘要同步中...</Text> : null}
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <View className="note-card">
          <Text className="section-title">今日建议</Text>
          <Text className="section-desc">{suggestionText}</Text>
          {suggestionState.loading ? <Text className="hero-note">AI 建议生成中...</Text> : null}
          {suggestionState.error ? <Text className="hero-note">{suggestionState.error}</Text> : null}
        </View>
      </View>
    </View>
  );
}
