import React, { useMemo, useState } from "react";
import Taro, { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import AiEstimatePanel from "../../components/ai-estimate-panel";
import { estimateFoodText } from "../../services/ai";
import { refreshHomeCache } from "../../services/home";
import {
  createFoodRecord,
  deleteFoodRecord,
  getFoodRecords,
  updateFoodRecord
} from "../../services/records";
import { invalidateTimelineCaches } from "../../store/session";
import { buildFoodRecordFromAi, createEmptyAiResult, normalizeAiResult } from "../../utils/ai";
import {
  formatFoodRecordTitle,
  inferMealFromText,
  sanitizeFoodEstimateItem
} from "../../utils/estimate-display";
import { currentTimeString, todayString, safeList, toErrorMessage } from "../../utils/day";
import { getRecordTimeLabel } from "../../utils/record-display";
import { usePageGuard } from "../../utils/use-page-guard";

const meals = ["早餐", "午餐", "晚餐", "加餐"];

const initialForm = {
  record_date: todayString(),
  time_text: "",
  meal: "早餐",
  detail: "",
  location: "",
  kcal: "",
  source_type: "manual",
  ai_type: ""
};

const initialEstimateState = {
  draft: "",
  loading: false,
  confirming: false,
  error: "",
  result: createEmptyAiResult("food_text_estimate")
};

function createSubmitTimestamp(isEditing, form) {
  if (isEditing) {
    return {
      record_date: form.record_date || todayString(),
      time_text: form.time_text || currentTimeString()
    };
  }

  return {
    record_date: todayString(),
    time_text: currentTimeString()
  };
}

export default function FoodPage() {
  const ready = usePageGuard("activated");
  const [form, setForm] = useState(initialForm);
  const [items, setItems] = useState([]);
  const [editingId, setEditingId] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [estimateState, setEstimateState] = useState(initialEstimateState);

  const estimateItems = useMemo(
    () => safeList(estimateState.result?.items).map((item) => sanitizeFoodEstimateItem(item, estimateState.draft)),
    [estimateState.result, estimateState.draft]
  );

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateEstimateDraft(value) {
    setEstimateState((prev) => ({
      ...prev,
      draft: value,
      error: prev.error ? "" : prev.error
    }));
  }

  function resetEstimateState() {
    setEstimateState({
      ...initialEstimateState,
      result: createEmptyAiResult("food_text_estimate")
    });
  }

  async function loadList() {
    try {
      setLoading(true);
      setError("");
      const payload = await getFoodRecords({ limit: 20 });
      setItems(safeList(payload.items || payload));
    } catch (err) {
      setError(toErrorMessage(err, "饮食记录加载失败"));
    } finally {
      setLoading(false);
    }
  }

  useDidShow(() => {
    if (ready) {
      loadList();
    }
  });

  async function syncAfterMutation() {
    invalidateTimelineCaches();
    await Promise.all([loadList(), refreshHomeCache()]);
  }

  async function handleSubmit() {
    try {
      setSaving(true);
      setError("");
      const nextTimestamp = createSubmitTimestamp(Boolean(editingId), form);
      const payload = {
        ...form,
        ...nextTimestamp,
        kcal: Number(form.kcal) || 0,
        source_type: form.source_type || "manual",
        ai_type: form.ai_type || null
      };

      if (editingId) {
        await updateFoodRecord(editingId, payload);
      } else {
        await createFoodRecord(payload);
      }

      setForm(initialForm);
      setEditingId("");
      await syncAfterMutation();
      Taro.showToast({ title: "已保存", icon: "success" });
    } catch (err) {
      setError(toErrorMessage(err, "饮食记录保存失败"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteFoodRecord(id);
      invalidateTimelineCaches();
      if (editingId === id) {
        setEditingId("");
        setForm(initialForm);
      }
      await loadList();
      Taro.showToast({ title: "已删除", icon: "success" });
    } catch (err) {
      setError(toErrorMessage(err, "饮食记录删除失败"));
    }
  }

  async function handleEstimate() {
    const draftText = estimateState.draft.trim();
    if (!draftText) {
      setEstimateState((prev) => ({
        ...prev,
        error: "请先输入一句话描述"
      }));
      return;
    }

    try {
      setEstimateState((prev) => ({
        ...prev,
        loading: true,
        error: "",
        result: createEmptyAiResult("food_text_estimate")
      }));

      const mealHint = inferMealFromText(draftText);
      const payload = await estimateFoodText({
        text: draftText,
        record_date: todayString(),
        time_text: currentTimeString(),
        ...(mealHint ? { meal: mealHint } : {}),
        location: form.location || null,
        extra: {
          entry_mode: "text"
        }
      });

      setEstimateState((prev) => ({
        ...prev,
        loading: false,
        result: normalizeAiResult(payload, "food_text_estimate")
      }));
    } catch (err) {
      setEstimateState((prev) => ({
        ...prev,
        loading: false,
        error: toErrorMessage(err, "一句话估算失败，你仍然可以改为精确记录")
      }));
    }
  }

  async function handleConfirmEstimate() {
    if (!estimateItems.length) {
      setEstimateState((prev) => ({
        ...prev,
        error: "当前没有可确认的估算结果，请继续完善描述"
      }));
      return;
    }

    try {
      setEstimateState((prev) => ({
        ...prev,
        confirming: true,
        error: ""
      }));

      const timestamp = currentTimeString();
      const recordDate = todayString();

      for (const item of estimateItems) {
        await createFoodRecord(
          buildFoodRecordFromAi(item, {
            record_date: recordDate,
            time_text: timestamp,
            meal: item.meal || "加餐",
            location: form.location,
            ai_type: estimateState.result?.ai_type || "food_text_estimate"
          })
        );
      }

      await syncAfterMutation();
      resetEstimateState();
      Taro.showToast({ title: "已添加到今日饮食", icon: "success" });
    } catch (err) {
      setEstimateState((prev) => ({
        ...prev,
        confirming: false,
        error: toErrorMessage(err, "估算结果写入失败，请改为精确记录")
      }));
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
        <View className="hero-card hero-card--subpage">
          <Text className="eyebrow">饮食记录</Text>
          <Text className="page-title">吃了什么</Text>
          <Text className="page-subtitle">先用最顺手的方式记下今天吃了什么，首页和里程会自动更新。</Text>
          <View className="hero-pill-row">
            <Text className="hero-badge">{editingId ? "正在编辑记录" : "今日新增记录"}</Text>
            <Text className="hero-badge">记录时间自动生成</Text>
          </View>
        </View>

        <AiEstimatePanel
          eyebrow="AI 辅助估算"
          title="一句话估算"
          description="输入一句自然描述，先看看估算结果，再决定是否写入今日饮食。"
          placeholder="例如：中午吃了 200g 鸡胸肉、150g 米饭、一个鸡蛋"
          inputValue={estimateState.draft}
          onInputChange={updateEstimateDraft}
          onSubmit={handleEstimate}
          submitLabel="生成估算结果"
          loading={estimateState.loading}
          loadingText="正在分析这顿饮食..."
          summary={estimateState.result?.summary}
          error={estimateState.error}
          items={estimateItems}
          renderResultItem={(item, index) => (
            <View className="ai-result-card" key={`${item.displayTitle || item.detail}-${index}`}>
              {item.displayMeal ? <Text className="status-pill status-pill--accent">{item.displayMeal}</Text> : null}
              <Text className="list-title">{item.displayTitle}</Text>
              <Text className="list-subtitle">{getRecordTimeLabel({ ...item, time_text: currentTimeString() })}</Text>
              <Text className="list-kcal list-kcal-positive">+{item.kcal} kcal</Text>
            </View>
          )}
          confirmLabel="确认添加到今日饮食"
          onConfirm={handleConfirmEstimate}
          confirming={estimateState.confirming}
          reserveTitle="更多方式"
          reserveContent={(
            <View className="reserve-grid">
              <View className="reserve-card">
                <Text className="reserve-card-title">拍照识别</Text>
                <Text className="reserve-card-desc">餐盘拍照识别会在这里继续补充，入口会保持一致。</Text>
              </View>
              <View className="reserve-card">
                <Text className="reserve-card-title">营养明细</Text>
                <Text className="reserve-card-desc">后续会补充更细的营养信息和更多估算来源说明。</Text>
              </View>
            </View>
          )}
        />

        <View className="section-card form-shell">
          <View className="section-heading">
            <Text className="record-panel-title">精确记录</Text>
            <Text className="section-desc">记录时间会自动写入当前系统时间。</Text>
          </View>

          <View className="field-group">
            <Text className="field-label">餐别</Text>
            <View className="inline-chip-row">
              {meals.map((meal) => (
                <Text
                  key={meal}
                  className={`chip ${form.meal === meal ? "chip-active" : ""}`}
                  onClick={() => updateField("meal", meal)}
                >
                  {meal}
                </Text>
              ))}
            </View>
          </View>

          <View className="field-group">
            <Text className="field-label">吃了什么</Text>
            <Input
              className="field-input"
              value={form.detail}
              placeholder="例如：鸡胸肉沙拉 / 牛奶燕麦 / 米饭牛肉"
              onInput={(event) => updateField("detail", event.detail.value)}
            />
          </View>

          <View className="field-group">
            <Text className="field-label">热量（kcal）</Text>
            <Input
              className="field-input"
              type="number"
              value={String(form.kcal || "")}
              placeholder="例如：420"
              onInput={(event) => updateField("kcal", event.detail.value)}
            />
          </View>

          <View className="button-row">
            <Button className="primary-button button-block" loading={saving} onClick={handleSubmit}>
              保存饮食记录
            </Button>
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <View className="placeholder-panel">
          <View className="section-heading">
            <Text className="record-panel-title">拍照识别</Text>
            <Text className="section-desc">拍照识别即将支持，后续可以直接从这里完成识别和确认。</Text>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              选择图片
            </Button>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              拍照识别即将支持
            </Button>
          </View>
        </View>

        <View className="section-card record-list-card">
          <View className="section-heading">
            <Text className="record-panel-title">今日饮食记录</Text>
            <Text className="section-desc">今天新增或编辑过的饮食记录都会出现在这里。</Text>
          </View>
          {loading ? <Text className="hint-text">饮食记录同步中...</Text> : null}
          {safeList(items).length ? (
            safeList(items).map((item) => (
              <View className="list-row" key={item.id}>
                <View className="status-pill-row">
                  {item.source_type === "manual" ? (
                    <Text className="status-pill status-pill--accent">{item.meal}</Text>
                  ) : null}
                </View>
                <Text className="list-title">{formatFoodRecordTitle(item)}</Text>
                <Text className="list-subtitle">{getRecordTimeLabel(item)}</Text>
                <Text className="list-kcal list-kcal-positive">+{item.kcal} kcal</Text>
                <View className="list-row-actions">
                  <Button
                    className="secondary-button"
                    onClick={() => {
                      setEditingId(item.id);
                      setForm({
                        record_date: item.record_date || todayString(),
                        time_text: item.time_text || "",
                        meal: item.meal || "早餐",
                        detail: item.detail || "",
                        location: item.location || "",
                        kcal: String(item.kcal || ""),
                        source_type: item.source_type || "manual",
                        ai_type: item.ai_type || ""
                      });
                    }}
                  >
                    编辑
                  </Button>
                  <Button className="danger-button" onClick={() => handleDelete(item.id)}>
                    删除
                  </Button>
                </View>
              </View>
            ))
          ) : (
            <Text className="empty-text">今天还没有饮食记录。</Text>
          )}
        </View>
      </View>
    </View>
  );
}
