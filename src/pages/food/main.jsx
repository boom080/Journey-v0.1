import React, { useMemo, useState } from "react";
import Taro, { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import AiEstimatePanel from "../../components/ai-estimate-panel";
import { estimateFoodText } from "../../services/ai";
import {
  createFoodRecord,
  deleteFoodRecord,
  getFoodRecords,
  updateFoodRecord
} from "../../services/records";
import { invalidateTimelineCaches } from "../../store/session";
import { buildFoodRecordFromAi, createEmptyAiResult, normalizeAiResult } from "../../utils/ai";
import { todayString, safeList, toErrorMessage } from "../../utils/day";
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

export default function FoodPage() {
  const ready = usePageGuard("activated");
  const [form, setForm] = useState(initialForm);
  const [items, setItems] = useState([]);
  const [editingId, setEditingId] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [estimateState, setEstimateState] = useState(initialEstimateState);

  const estimateItems = useMemo(() => safeList(estimateState.result?.items), [estimateState.result]);

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

  async function handleSubmit() {
    try {
      setSaving(true);
      setError("");
      const payload = {
        ...form,
        kcal: Number(form.kcal) || 0,
        source_type: form.source_type || "manual",
        ai_type: form.ai_type || null
      };

      if (editingId) {
        await updateFoodRecord(editingId, payload);
      } else {
        await createFoodRecord(payload);
      }

      invalidateTimelineCaches();
      setForm(initialForm);
      setEditingId("");
      await loadList();
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
        error: ""
      }));

      const payload = await estimateFoodText({
        text: draftText,
        record_date: form.record_date,
        time_text: form.time_text || null,
        meal: form.meal,
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
        error: toErrorMessage(err, "一句话估算失败，你仍然可以手动记录")
      }));
    }
  }

  async function handleConfirmEstimate() {
    if (!estimateItems.length) {
      setEstimateState((prev) => ({
        ...prev,
        error: "当前没有可确认的估算结果，请继续手动输入"
      }));
      return;
    }

    try {
      setEstimateState((prev) => ({
        ...prev,
        confirming: true,
        error: ""
      }));

      for (const item of estimateItems) {
        await createFoodRecord(
          buildFoodRecordFromAi(item, {
            record_date: form.record_date,
            time_text: form.time_text,
            meal: form.meal,
            location: form.location,
            ai_type: estimateState.result?.ai_type || "food_text_estimate"
          })
        );
      }

      invalidateTimelineCaches();
      await loadList();
      resetEstimateState();
      Taro.showToast({ title: "已添加到今日饮食", icon: "success" });
    } catch (err) {
      setEstimateState((prev) => ({
        ...prev,
        confirming: false,
        error: toErrorMessage(err, "估算结果写入失败，请改用手动记录")
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
        <View>
          <Text className="page-title">吃了什么</Text>
          <Text className="page-subtitle">记录今天吃了什么，首页和里程会自动联动。</Text>
        </View>

        <View className="section-card form-shell">
          <Text className="record-panel-title">手动记录</Text>

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

          <View className="field-group">
            <Text className="field-label">地点</Text>
            <Input
              className="field-input"
              value={form.location}
              placeholder="例如：公司 / 学校 / 家里"
              onInput={(event) => updateField("location", event.detail.value)}
            />
          </View>

          <View className="button-row">
            <Button className="primary-button button-block" loading={saving} onClick={handleSubmit}>
              保存饮食记录
            </Button>
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <AiEstimatePanel
          title="一句话估算"
          placeholder="例如：中午吃了 200g 鸡胸肉、150g 米饭、一个鸡蛋"
          inputValue={estimateState.draft}
          onInputChange={updateEstimateDraft}
          onSubmit={handleEstimate}
          submitLabel="生成估算结果"
          loading={estimateState.loading}
          summary={estimateState.result?.summary}
          error={estimateState.error}
          items={estimateItems}
          renderResultItem={(item, index) => (
            <View className="ai-result-card" key={`${item.title || item.detail}-${index}`}>
              <Text className="list-title">{item.meal || form.meal} · {item.detail || item.title}</Text>
              <Text className="list-subtitle">
                {item.time_text || form.time_text || "--:--"} · {item.location || form.location || "未填写地点"}
              </Text>
              <Text className="list-kcal list-kcal-positive">+{item.kcal} kcal</Text>
              <Text className="meta-text">来源：{item.source_type || "ai"} · {item.ai_type || "food_text_estimate"}</Text>
            </View>
          )}
          confirmLabel="确认添加到今日饮食"
          onConfirm={handleConfirmEstimate}
          confirming={estimateState.confirming}
        />

        <View className="placeholder-panel">
          <Text className="record-panel-title">图片识别（当前为预留入口）</Text>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              选择图片
            </Button>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              开始识别
            </Button>
          </View>
        </View>

        <View className="section-card record-list-card">
          <Text className="record-panel-title">今日饮食记录</Text>
          {loading ? <Text className="hint-text">饮食记录同步中...</Text> : null}
          {safeList(items).length ? (
            safeList(items).map((item) => (
              <View className="list-row" key={item.id}>
                <Text className="list-title">{item.meal} · {item.detail}</Text>
                <Text className="list-subtitle">{item.time_text || "--:--"} · {item.location || "未填写地点"}</Text>
                <Text className="meta-text">来源：{item.source_type || "manual"}{item.ai_type ? ` · ${item.ai_type}` : ""}</Text>
                <Text className="list-kcal list-kcal-positive">+{item.kcal} kcal</Text>
                <View className="button-row">
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
