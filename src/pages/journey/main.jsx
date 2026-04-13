import React, { useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { Button, Picker, Text, View } from "@tarojs/components";
import { getJourneyDays } from "../../services/journey";
import { getCachedJourney, saveCachedJourney } from "../../store/session";
import { safeList, toErrorMessage, todayString } from "../../utils/day";
import { formatFoodRecordTitle } from "../../utils/estimate-display";
import {
  appendJourneyBrowserPage,
  createJourneyBrowser,
  createJourneyBrowserFromPayload,
  findClosestJourneyPage,
  findJourneyPageByDate,
  getJourneyTotalPages,
  getJourneyVisibleDays,
  JOURNEY_PAGE_SIZE,
  setJourneyCurrentPage,
  shouldFetchMoreForDate
} from "../../utils/journey-pagination";
import { getRecordTimeLabel } from "../../utils/record-display";
import { usePageGuard } from "../../utils/use-page-guard";

function hasAnyJourneyDay(browser) {
  return safeList(browser?.items).length > 0;
}

export default function JourneyPage() {
  const ready = usePageGuard("activated");
  const [journey, setJourney] = useState(() => createJourneyBrowser(getCachedJourney(), JOURNEY_PAGE_SIZE));
  const [expandedDate, setExpandedDate] = useState("");
  const [selectedDate, setSelectedDate] = useState(todayString());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [jumpNotice, setJumpNotice] = useState("");

  function persistJourney(nextJourney) {
    setJourney(nextJourney);
    saveCachedJourney(nextJourney);
    return nextJourney;
  }

  async function requestJourneyPage(cursor = "") {
    return getJourneyDays({
      cursor,
      page_size: JOURNEY_PAGE_SIZE
    });
  }

  async function loadFirstPage() {
    try {
      setLoading(true);
      setError("");
      setJumpNotice("");
      const payload = await requestJourneyPage();
      const nextJourney = createJourneyBrowserFromPayload(payload, JOURNEY_PAGE_SIZE);
      persistJourney(nextJourney);
      setExpandedDate("");
    } catch (err) {
      setError(toErrorMessage(err, "里程加载失败，已保留本地缓存"));
    } finally {
      setLoading(false);
    }
  }

  async function ensurePageForDate(browser, targetDate) {
    let workingJourney = browser;
    let matchedPage = findJourneyPageByDate(workingJourney, targetDate);

    while (!matchedPage && shouldFetchMoreForDate(workingJourney, targetDate)) {
      const payload = await requestJourneyPage(workingJourney.nextCursor);
      workingJourney = appendJourneyBrowserPage(workingJourney, payload);
      matchedPage = findJourneyPageByDate(workingJourney, targetDate);
    }

    return {
      journey: workingJourney,
      matchedPage
    };
  }

  async function handleJumpToDate(targetDate) {
    try {
      setLoading(true);
      setError("");
      setJumpNotice("");
      setSelectedDate(targetDate);

      let workingJourney = journey;
      if (!hasAnyJourneyDay(workingJourney)) {
        const payload = await requestJourneyPage();
        workingJourney = createJourneyBrowserFromPayload(payload, JOURNEY_PAGE_SIZE);
      }

      const { journey: nextJourney, matchedPage } = await ensurePageForDate(workingJourney, targetDate);
      const targetPage = matchedPage || findClosestJourneyPage(nextJourney, targetDate);
      const pagedJourney = setJourneyCurrentPage(nextJourney, targetPage);

      persistJourney(pagedJourney);
      setExpandedDate("");

      if (!matchedPage) {
        setJumpNotice("该日期暂无记录，已跳到最接近的一页。");
      }
    } catch (err) {
      setError(toErrorMessage(err, "日期跳转失败，请稍后再试"));
    } finally {
      setLoading(false);
    }
  }

  async function handleNextPage() {
    if (loading) {
      return;
    }

    if (journey.currentPage < safeList(journey.pages).length) {
      persistJourney(setJourneyCurrentPage(journey, journey.currentPage + 1));
      setExpandedDate("");
      setJumpNotice("");
      return;
    }

    if (!journey.hasMore) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setJumpNotice("");
      const payload = await requestJourneyPage(journey.nextCursor);
      const nextJourney = appendJourneyBrowserPage(journey, payload);
      persistJourney(nextJourney);
      setExpandedDate("");
    } catch (err) {
      setError(toErrorMessage(err, "下一页加载失败，请稍后再试"));
    } finally {
      setLoading(false);
    }
  }

  function handlePrevPage() {
    if (loading || journey.currentPage <= 1) {
      return;
    }

    persistJourney(setJourneyCurrentPage(journey, journey.currentPage - 1));
    setExpandedDate("");
    setJumpNotice("");
  }

  useDidShow(() => {
    if (!ready) {
      return;
    }

    const cachedJourney = createJourneyBrowser(getCachedJourney(), JOURNEY_PAGE_SIZE);
    setJourney(cachedJourney);

    if (!safeList(cachedJourney.pages).length) {
      loadFirstPage();
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

  const visibleDays = getJourneyVisibleDays(journey);
  const totalPages = getJourneyTotalPages(journey);
  const canGoPrev = journey.currentPage > 1;
  const canGoNext = journey.currentPage < safeList(journey.pages).length || journey.hasMore;

  return (
    <View className="page">
      <View className="page-shell page-shell--airy">
        <View className="journey-page-top">
          <Text className="journey-page-title">看看你已经走了多远</Text>
        </View>

        <View className="section-card section-card--soft">
          <View className="journey-jump-row">
            <View>
              <Text className="section-title">按日期看看</Text>
              <Text className="section-desc">选择一天，直接跳到那一页。</Text>
            </View>
            <Picker mode="date" value={selectedDate} onChange={(e) => handleJumpToDate(e.detail.value)}>
              <View className="journey-date-picker">
                <Text className="journey-date-picker-label">{selectedDate || "选择日期"}</Text>
              </View>
            </Picker>
          </View>
          {jumpNotice ? <Text className="hint-text">{jumpNotice}</Text> : null}
        </View>

        {safeList(visibleDays).length ? (
          safeList(visibleDays).map((day) => {
            const dateKey = day.record_date || day.id;
            const isOpen = expandedDate === dateKey;

            return (
              <View className="record-card" key={dateKey}>
                <View className="journey-card-header">
                  <View>
                    <Text className="journey-date">{String(dateKey)}</Text>
                    <Text className="section-desc">{day.summary || "这一天的记录概览"}</Text>
                  </View>
                  <Text className="badge">{isOpen ? "展开中" : "查看当天"}</Text>
                </View>

                <View className="journey-card-counts">
                  <Text className="metric-chip metric-chip--food">饮食 {safeList(day.foodItems).length}</Text>
                  <Text className="metric-chip metric-chip--activity">活动 {safeList(day.activityItems).length}</Text>
                  <Text className="status-pill status-pill--surface">{day.status_text || "这一天的记录概览"}</Text>
                </View>

                <View className="button-row">
                  <Button className="ghost-button" onClick={() => setExpandedDate(isOpen ? "" : dateKey)}>
                    {isOpen ? "收起当天内容" : "展开当天内容"}
                  </Button>
                </View>

                {isOpen ? (
                  <View>
                    <View className="journey-section">
                      <Text className="record-panel-title">吃了什么</Text>
                      {safeList(day.foodItems).length ? (
                        safeList(day.foodItems).map((item) => (
                          <View className="journey-entry" key={`food-${item.id}`}>
                            <View className="journey-entry-main">
                              <Text className="list-title">{formatFoodRecordTitle(item)}</Text>
                              <Text className="list-subtitle">{getRecordTimeLabel(item)}</Text>
                            </View>
                            <Text className="list-kcal list-kcal-positive">+{item.kcal} kcal</Text>
                          </View>
                        ))
                      ) : (
                        <Text className="empty-text">当天还没有饮食记录。</Text>
                      )}
                    </View>

                    <View className="journey-section">
                      <Text className="record-panel-title">做了什么</Text>
                      {safeList(day.activityItems).length ? (
                        safeList(day.activityItems).map((item) => (
                          <View className="journey-entry" key={`activity-${item.id}`}>
                            <View className="journey-entry-main">
                              <Text className="list-title">{item.name || item.title || "已记录活动"}</Text>
                              <Text className="list-subtitle">{getRecordTimeLabel(item)}</Text>
                            </View>
                            <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
                          </View>
                        ))
                      ) : (
                        <Text className="empty-text">当天还没有活动记录。</Text>
                      )}
                    </View>

                    <View className="journey-summary">
                      <Text>{day.summary || "继续按天记录，里程会慢慢串起你的生活轨迹。"}</Text>
                    </View>
                  </View>
                ) : null}
              </View>
            );
          })
        ) : loading ? (
          <View className="section-card">
            <Text className="hint-text">里程加载中...</Text>
          </View>
        ) : (
          <View className="empty-card">
            <Text className="section-title">还没有多天记录</Text>
            <Text className="empty-text">先去首页记下一餐或一项活动，这里会按天慢慢积累起来。</Text>
          </View>
        )}

        {error ? <Text className="error-text">{error}</Text> : null}

        <View className="section-card journey-pagination-card">
          <View className="journey-pagination">
            <Button className="secondary-button journey-page-button" disabled={!canGoPrev || loading} onClick={handlePrevPage}>
              上一页
            </Button>
            <View className="journey-page-status">
              <Text className="journey-page-number">第 {journey.currentPage} 页</Text>
              {totalPages ? <Text className="journey-page-total">共 {totalPages} 页</Text> : null}
            </View>
            <Button className="primary-button journey-page-button" disabled={!canGoNext || loading} loading={loading} onClick={handleNextPage}>
              下一页
            </Button>
          </View>
        </View>
      </View>
    </View>
  );
}
