import React, { useEffect, useMemo, useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { Image, Text, View } from "@tarojs/components";
import { activityEntryImage, foodEntryImage, homeStickerImage } from "../../assets";
import { generateHomeSuggestion } from "../../services/ai";
import { buildHomeSummary, getHomeSummary } from "../../services/home";
import { getCachedHome, getCachedProfile, saveCachedHome } from "../../store/session";
import { createAiState, normalizeAiResult } from "../../utils/ai";
import { calculateDailyEnergy } from "../../utils/daily-energy";
import { buildHomeSummaryText } from "../../utils/home-copy";
import {
  buildStickerLoadingText,
  buildStickerText,
  getHomeUpdatePageCount,
  getHomeUpdatePageItems
} from "../../utils/home-panel";
import { normalizeHomeUpdates } from "../../utils/home-updates";
import { getUpdateTimeLabel } from "../../utils/record-display";
import { openRoute, ROUTES } from "../../utils/router";
import { safeList, toErrorMessage } from "../../utils/day";
import { usePageGuardState } from "../../utils/use-page-guard";

const defaultSummary = {
  today_date: "",
  today_summary: "今天还没有记录，先记下吃了什么或做了什么。",
  goal_suggestion: "完成记录后，首页会给出更贴近今天节奏的提醒。",
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

function formatDailyEnergy(value) {
  const amount = Number(value || 0);
  return amount > 0 ? `${amount} kcal/天` : "待补充";
}

export default function HomePage() {
  const guard = usePageGuardState("activated");
  const cachedHome = getCachedHome() || defaultSummary;
  const [data, setData] = useState(cachedHome);
  const [profile, setProfile] = useState(getCachedProfile());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [updatesPage, setUpdatesPage] = useState(1);
  const [suggestionState, setSuggestionState] = useState({
    ...createAiState("home_suggestion"),
    result: normalizeAiResult(cachedHome?.extra?.aiSuggestion, "home_suggestion")
  });

  async function loadHome() {
    try {
      setLoading(true);
      setError("");
      const payload = await getHomeSummary();
      const latestProfile = getCachedProfile();
      const summaryData = {
        ...defaultSummary,
        ...buildHomeSummary(payload, latestProfile)
      };

      setData(summaryData);
      setProfile(latestProfile);

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
          error: toErrorMessage(suggestionError, "今日贴纸先稍微歇一会儿，已经用默认提醒顶上了。"),
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
    if (guard.ready) {
      loadHome();
    }
  });

  const suggestionText =
    suggestionState.result?.summary ||
    data.extra?.aiSuggestion?.summary ||
    data.goal_suggestion ||
    defaultSummary.goal_suggestion;
  const recordCounts = data.extra?.record_counts || {};
  const dailyEnergy = data.extra?.daily_energy || calculateDailyEnergy(profile);
  const recentUpdates = useMemo(() => normalizeHomeUpdates(data.recent_updates), [data.recent_updates]);
  const updatePageCount = useMemo(() => getHomeUpdatePageCount(recentUpdates), [recentUpdates]);
  const visibleUpdates = useMemo(
    () => getHomeUpdatePageItems(recentUpdates, updatesPage),
    [recentUpdates, updatesPage]
  );
  const stickerText = buildStickerText(suggestionText);
  const summaryText = buildHomeSummaryText({
    ...data,
    daily_energy_kcal: dailyEnergy.daily_energy_kcal,
    extra: {
      ...(data.extra || {}),
      daily_energy: dailyEnergy
    }
  });

  useEffect(() => {
    setUpdatesPage((prev) => {
      const nextPage = Math.min(prev, updatePageCount);
      return nextPage > 0 ? nextPage : 1;
    });
  }, [updatePageCount]);

  if (!guard.ready) {
    return (
      <View className="page-status-shell">
        <View className="page-status-card">
          <Text className="page-status-title">正在准备首页</Text>
          <Text className="page-status-message">{guard.message || "正在同步首页状态..."}</Text>
        </View>
      </View>
    );
  }

  return (
    <View className="page">
      <View className="page-shell">
        <View className="hero-card hero-card--home">
          <View className="hero-meta">
            <Text className="eyebrow">{data.today_date || "今日概览"}</Text>
            <View className="hero-pill-row hero-pill-row--compact">
              <Text className="hero-badge">当前目标：{profile?.goal || "维持体重"}</Text>
              <Text className="hero-badge">日常消耗：{formatDailyEnergy(dailyEnergy.daily_energy_kcal)}</Text>
            </View>
          </View>

          <View className="hero-main">
            <Text className="page-title">你好，{profile?.nickname || "即刻用户"}</Text>
            <Text className="hero-kcal">今日热量结余</Text>
            <Text className="hero-balance">{formatNetKcal(data.net_kcal)}</Text>
            <Text className="hero-note">{summaryText || defaultSummary.today_summary}</Text>
            <View className="hero-pill-row">
              <Text className="hero-badge">饮食 {Number(recordCounts.food || 0)} 条</Text>
              <Text className="hero-badge">活动 {Number(recordCounts.activity || 0)} 条</Text>
            </View>
          </View>
        </View>

        <View className="section-card section-card--soft">
          <View className="section-heading">
            <Text className="section-title">记录入口</Text>
            <Text className="section-desc">随手记下一条，今天的变化就会跟着更新。</Text>
          </View>
          <View className="card-stack">
            <View className="action-card action-card--food" onClick={() => openRoute(ROUTES.food)}>
              <View className="action-icon action-icon--image">
                <Image className="action-icon-image" src={foodEntryImage} mode="aspectFill" />
              </View>
              <View className="action-content">
                <Text className="action-title">吃了什么</Text>
                <Text className="action-desc">精确记录 / AI 辅助估算 / 拍照识别即将支持</Text>
              </View>
              <Text className="action-arrow">›</Text>
            </View>

            <View className="action-card action-card--activity" onClick={() => openRoute(ROUTES.activity)}>
              <View className="action-icon action-icon--image">
                <Image className="action-icon-image" src={activityEntryImage} mode="aspectFill" />
              </View>
              <View className="action-content">
                <Text className="action-title">做了什么</Text>
                <Text className="action-desc">精确记录 / AI 辅助估算 / 截图识别即将支持</Text>
              </View>
              <Text className="action-arrow">›</Text>
            </View>
          </View>
        </View>

        <View className="section-card">
          <View className="section-heading">
            <Text className="section-title">今日概况</Text>
            <Text className="section-desc">热量结余 = 已摄入 - 活动消耗 - 日常消耗</Text>
          </View>
          <View className="summary-grid">
            <View className="summary-card summary-card--highlight">
              <Text className="grid-label">净结余</Text>
              <Text className="summary-value">{Number(data.net_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
            <View className="summary-card">
              <Text className="grid-label">活动消耗</Text>
              <Text className="summary-value summary-value--burn">{Number(data.activity_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
            <View className="summary-card">
              <Text className="grid-label">已摄入</Text>
              <Text className="summary-value summary-value--intake">{Number(data.intake_kcal || 0)}</Text>
              <Text className="summary-unit">kcal</Text>
            </View>
            <View className="summary-card">
              <Text className="grid-label">日常消耗</Text>
              <Text className="summary-value summary-value--burn">{Number(dailyEnergy.daily_energy_kcal || 0)}</Text>
              <Text className="summary-unit">kcal/天</Text>
            </View>
          </View>
        </View>

        <View className="section-card">
          <View className="section-heading">
            <Text className="section-title">今日更新</Text>
            <Text className="section-desc">按时间看看今天记下了什么。</Text>
          </View>
          <View className="update-list">
            {safeList(visibleUpdates).length ? (
              safeList(visibleUpdates).map((item, index) => {
                const negative = String(item.kcal || "").startsWith("-");
                return (
                  <View className="update-row" key={`${item.title}-${updatesPage}-${index}`}>
                    <View className="update-main">
                      <Text className="update-title">{item.title}</Text>
                      <Text className="update-desc">{getUpdateTimeLabel(item)}</Text>
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

          {updatePageCount > 1 ? (
            <View className="update-mini-pager">
              <Text
                className={`update-mini-pager__btn ${updatesPage <= 1 ? "update-mini-pager__btn--disabled" : ""}`}
                onClick={() => {
                  if (updatesPage > 1) {
                    setUpdatesPage((prev) => prev - 1);
                  }
                }}
              >
                &lt;
              </Text>
              <Text className="update-mini-pager__text">
                {updatesPage}/{updatePageCount}
              </Text>
              <Text
                className={`update-mini-pager__btn ${updatesPage >= updatePageCount ? "update-mini-pager__btn--disabled" : ""}`}
                onClick={() => {
                  if (updatesPage < updatePageCount) {
                    setUpdatesPage((prev) => prev + 1);
                  }
                }}
              >
                &gt;
              </Text>
            </View>
          ) : null}

          {loading ? <Text className="hint-text">首页摘要同步中...</Text> : null}
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <View className="note-card note-card--sticker">
          <View className="sticker-card-head">
            <View className="sticker-card-title-wrap">
              <Text className="section-title">今日贴纸</Text>
              <Text className="section-desc sticker-card-subtitle">收下一句轻轻的提醒</Text>
            </View>
            <View className="sticker-art-shell">
              <Image className="sticker-art-image" src={homeStickerImage} mode="aspectFill" />
            </View>
          </View>
          <Text className="sticker-card-copy">{stickerText}</Text>
          {suggestionState.loading ? <Text className="hero-note">{buildStickerLoadingText()}</Text> : null}
          {suggestionState.error ? <Text className="hero-note">{suggestionState.error}</Text> : null}
        </View>
      </View>
    </View>
  );
}
