import React, { useMemo, useState } from "react";
import Taro, { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import AiEstimatePanel from "../../components/ai-estimate-panel";
import { estimateActivityText } from "../../services/ai";
import {
  createActivityRecord,
  deleteActivityRecord,
  getActivityRecords,
  updateActivityRecord
} from "../../services/records";
import { invalidateTimelineCaches } from "../../store/session";
import { buildActivityRecordFromAi, createEmptyAiResult, normalizeAiResult } from "../../utils/ai";
import { todayString, safeList, toErrorMessage } from "../../utils/day";
import { usePageGuard } from "../../utils/use-page-guard";

const initialForm = {
  record_date: todayString(),
  time_text: "",
  name: "",
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
  result: createEmptyAiResult("activity_text_estimate")
};

export default function ActivityPage() {
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
      result: createEmptyAiResult("activity_text_estimate")
    });
  }

  async function loadList() {
    try {
      setLoading(true);
      setError("");
      const payload = await getActivityRecords({ limit: 20 });
      setItems(safeList(payload.items || payload));
    } catch (err) {
      setError(toErrorMessage(err, "活动记录加载失败"));
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
        await updateActivityRecord(editingId, payload);
      } else {
        await createActivityRecord(payload);
      }

      invalidateTimelineCaches();
      setForm(initialForm);
      setEditingId("");
      await loadList();
      Taro.showToast({ title: "已保存", icon: "success" });
    } catch (err) {
      setError(toErrorMessage(err, "活动记录保存失败"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteActivityRecord(id);
      invalidateTimelineCaches();
      if (editingId === id) {
        setEditingId("");
        setForm(initialForm);
      }
      await loadList();
      Taro.showToast({ title: "已删除", icon: "success" });
    } catch (err) {
      setError(toErrorMessage(err, "活动记录删除失败"));
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

      const payload = await estimateActivityText({
        text: draftText,
        record_date: form.record_date,
        time_text: form.time_text || null,
        location: form.location || null,
        extra: {
          entry_mode: "text"
        }
      });

      setEstimateState((prev) => ({
        ...prev,
        loading: false,
        result: normalizeAiResult(payload, "activity_text_estimate")
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
        await createActivityRecord(
          buildActivityRecordFromAi(item, {
            record_date: form.record_date,
            time_text: form.time_text,
            location: form.location,
            ai_type: estimateState.result?.ai_type || "activity_text_estimate"
          })
        );
      }

      invalidateTimelineCaches();
      await loadList();
      resetEstimateState();
      Taro.showToast({ title: "已添加到今日活动", icon: "success" });
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
          <Text className="page-title">做了什么</Text>
          <Text className="page-subtitle">记录今天做了什么，首页和里程会自动联动。</Text>
        </View>

        <View className="section-card form-shell">
          <Text className="record-panel-title">手动记录</Text>

          <View className="field-group">
            <Text className="field-label">活动名称</Text>
            <Input
              className="field-input"
              value={form.name}
              placeholder="例如：跑步 / 力量训练 / 步行"
              onInput={(event) => updateField("name", event.detail.value)}
            />
          </View>

          <View className="field-group">
            <Text className="field-label">消耗热量（kcal）</Text>
            <Input
              className="field-input"
              type="number"
              value={String(form.kcal || "")}
              placeholder="例如：260"
              onInput={(event) => updateField("kcal", event.detail.value)}
            />
          </View>

          <View className="field-group">
            <Text className="field-label">地点</Text>
            <Input
              className="field-input"
              value={form.location}
              placeholder="例如：健身房 / 操场 / 公司附近"
              onInput={(event) => updateField("location", event.detail.value)}
            />
          </View>

          <View className="button-row">
            <Button className="primary-button button-block" loading={saving} onClick={handleSubmit}>
              保存活动记录
            </Button>
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <AiEstimatePanel
          title="一句话估算"
          placeholder="例如：晚上跑步 45 分钟，大概 6 公里"
          inputValue={estimateState.draft}
          onInputChange={updateEstimateDraft}
          onSubmit={handleEstimate}
          submitLabel="生成估算结果"
          loading={estimateState.loading}
          summary={estimateState.result?.summary}
          error={estimateState.error}
          items={estimateItems}
          renderResultItem={(item, index) => (
            <View className="ai-result-card" key={`${item.name || item.title}-${index}`}>
              <Text className="list-title">{item.name || item.title}</Text>
              <Text className="list-subtitle">
                {item.time_text || form.time_text || "--:--"} · {item.location || form.location || "未填写地点"}
              </Text>
              <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
              <Text className="meta-text">来源：{item.source_type || "ai"} · {item.ai_type || "activity_text_estimate"}</Text>
            </View>
          )}
          confirmLabel="确认添加到今日活动"
          onConfirm={handleConfirmEstimate}
          confirming={estimateState.confirming}
        />

        <View className="placeholder-panel">
          <Text className="record-panel-title">训练截图 OCR（当前为预留入口）</Text>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              选择截图
            </Button>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              开始识别
            </Button>
          </View>
        </View>

        <View className="section-card record-list-card">
          <Text className="record-panel-title">今日活动记录</Text>
          {loading ? <Text className="hint-text">活动记录同步中...</Text> : null}
          {safeList(items).length ? (
            safeList(items).map((item) => (
              <View className="list-row" key={item.id}>
                <Text className="list-title">{item.name}</Text>
                <Text className="list-subtitle">{item.time_text || "--:--"} · {item.location || "未填写地点"}</Text>
                <Text className="meta-text">来源：{item.source_type || "manual"}{item.ai_type ? ` · ${item.ai_type}` : ""}</Text>
                <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
                <View className="button-row">
                  <Button
                    className="secondary-button"
                    onClick={() => {
                      setEditingId(item.id);
                      setForm({
                        record_date: item.record_date || todayString(),
                        time_text: item.time_text || "",
                        name: item.name || "",
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
            <Text className="empty-text">今天还没有活动记录。</Text>
          )}
        </View>
      </View>
    </View>
  );
}
