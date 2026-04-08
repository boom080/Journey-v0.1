import React, { useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { Button, Text, View } from "@tarojs/components";
import { getJourneyDays } from "../../services/journey";
import { getCachedJourney, saveCachedJourney } from "../../store/session";
import { safeList, toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

const FILTERS = [
  { label: "最近7天", value: 7 },
  { label: "最近30天", value: 30 },
  { label: "按月查看", value: 60 }
];

export default function JourneyPage() {
  const ready = usePageGuard("activated");
  const [journey, setJourney] = useState(getCachedJourney());
  const [expandedDate, setExpandedDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pageSize, setPageSize] = useState(7);

  async function fetchDays(cursor = "", append = false, nextPageSize = pageSize) {
    try {
      setLoading(true);
      setError("");
      const payload = await getJourneyDays({
        cursor,
        page_size: nextPageSize
      });

      const nextData = {
        items: append ? [...safeList(journey.items), ...safeList(payload.items)] : safeList(payload.items),
        nextCursor: payload.next_cursor || "",
        hasMore: Boolean(payload.has_more)
      };

      setJourney(nextData);
      saveCachedJourney(nextData);
    } catch (err) {
      setError(toErrorMessage(err, "多天里程加载失败，已保留本地缓存"));
    } finally {
      setLoading(false);
    }
  }

  useDidShow(() => {
    if (ready) {
      fetchDays("", false, pageSize);
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

  return (
    <View className="page">
      <View className="page-shell">
        <View>
          <Text className="page-title">里程</Text>
          <Text className="page-subtitle">按天查看你的饮食与活动记录，不是今日时间线，而是多天日记卡片。</Text>
        </View>

        <View className="journey-filters">
          {FILTERS.map((item) => (
            <Text
              key={item.label}
              className={`chip ${pageSize === item.value ? "chip-active" : ""}`}
              onClick={() => {
                setPageSize(item.value);
                fetchDays("", false, item.value);
              }}
            >
              {item.label}
            </Text>
          ))}
        </View>

        {safeList(journey.items).length ? (
          safeList(journey.items).map((day) => {
            const dateKey = day.record_date || day.id;
            const isOpen = expandedDate === dateKey;

            return (
              <View className="record-card" key={dateKey}>
                <View className="journey-card-header">
                  <View>
                    <Text className="journey-date">{String(dateKey)}</Text>
                    <Text className="section-desc">{day.status_text || "今天的生活轨迹"}</Text>
                  </View>
                  <Text className="badge">{isOpen ? "已展开" : "多天日记"}</Text>
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
                              <Text className="list-title">{item.meal} · {item.detail}</Text>
                              <Text className="list-subtitle">{item.time_text || "--:--"} · {item.location || "未填写地点"}</Text>
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
                              <Text className="list-title">{item.name}</Text>
                              <Text className="list-subtitle">{item.time_text || "--:--"} · {item.location || "未填写地点"}</Text>
                            </View>
                            <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
                          </View>
                        ))
                      ) : (
                        <Text className="empty-text">当天还没有活动记录。</Text>
                      )}
                    </View>

                    <View className="journey-summary">
                      <Text>{day.summary || "继续保持真实记录，里程页会按天沉淀生活轨迹。"}</Text>
                    </View>
                  </View>
                ) : null}
              </View>
            );
          })
        ) : (
          <View className="empty-card">
            <Text className="section-title">还没有多天记录</Text>
            <Text className="empty-text">先去首页记录饮食和活动，里程会按天聚合回看。</Text>
          </View>
        )}

        {error ? <Text className="error-text">{error}</Text> : null}

        <View className="button-row">
          <Button
            className="soft-button"
            loading={loading}
            onClick={() => fetchDays(journey.nextCursor, true, pageSize)}
            disabled={!journey.hasMore}
          >
            {journey.hasMore ? "加载更多日记" : "已经到底了"}
          </Button>
        </View>
      </View>
    </View>
  );
}
