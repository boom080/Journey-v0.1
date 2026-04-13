import React, { useMemo, useState } from "react";
import Taro, { useDidShow } from "@tarojs/taro";
import { Button, Input, Text, View } from "@tarojs/components";
import AiEstimatePanel from "../../components/ai-estimate-panel";
import { estimateActivityText } from "../../services/ai";
import { refreshHomeCache } from "../../services/home";
import {
  createActivityRecord,
  deleteActivityRecord,
  getActivityRecords,
  updateActivityRecord
} from "../../services/records";
import { invalidateTimelineCaches } from "../../store/session";
import { buildActivityRecordFromAi, createEmptyAiResult, normalizeAiResult } from "../../utils/ai";
import { sanitizeActivityEstimateItem } from "../../utils/estimate-display";
import { currentTimeString, todayString, safeList, toErrorMessage } from "../../utils/day";
import { getRecordTimeLabel } from "../../utils/record-display";
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

export default function ActivityPage() {
  const ready = usePageGuard("activated");
  const [form, setForm] = useState(initialForm);
  const [items, setItems] = useState([]);
  const [editingId, setEditingId] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [estimateState, setEstimateState] = useState(initialEstimateState);

  const estimateItems = useMemo(
    () => safeList(estimateState.result?.items).map((item) => sanitizeActivityEstimateItem(item, estimateState.draft)),
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
        await updateActivityRecord(editingId, payload);
      } else {
        await createActivityRecord(payload);
      }

      setForm(initialForm);
      setEditingId("");
      await syncAfterMutation();
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
        error: "",
        result: createEmptyAiResult("activity_text_estimate")
      }));

      const payload = await estimateActivityText({
        text: draftText,
        record_date: todayString(),
        time_text: currentTimeString(),
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
        await createActivityRecord(
          buildActivityRecordFromAi(item, {
            record_date: recordDate,
            time_text: timestamp,
            location: form.location,
            ai_type: estimateState.result?.ai_type || "activity_text_estimate"
          })
        );
      }

      await syncAfterMutation();
      resetEstimateState();
      Taro.showToast({ title: "已添加到今日活动", icon: "success" });
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
          <Text className="eyebrow">活动记录</Text>
          <Text className="page-title">做了什么</Text>
          <Text className="page-subtitle">先记下今天做了什么，训练和活动记录会同步到首页与里程。</Text>
          <View className="hero-pill-row">
            <Text className="hero-badge">{editingId ? "正在编辑记录" : "今日新增记录"}</Text>
            <Text className="hero-badge">记录时间自动生成</Text>
          </View>
        </View>

        <AiEstimatePanel
          eyebrow="AI 辅助估算"
          title="一句话估算"
          description="输入一句自然描述，先得到活动估算结果，再确认是否写入今日活动。"
          placeholder="例如：晚上跑步 45 分钟，大概 6 公里"
          inputValue={estimateState.draft}
          onInputChange={updateEstimateDraft}
          onSubmit={handleEstimate}
          submitLabel="生成估算结果"
          loading={estimateState.loading}
          loadingText="正在分析这段活动..."
          summary={estimateState.result?.summary}
          error={estimateState.error}
          items={estimateItems}
          renderResultItem={(item, index) => (
            <View className="ai-result-card" key={`${item.displayTitle || item.name}-${index}`}>
              <Text className="list-title">{item.displayTitle}</Text>
              <Text className="list-subtitle">{getRecordTimeLabel({ ...item, time_text: currentTimeString() })}</Text>
              <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
            </View>
          )}
          confirmLabel="确认添加到今日活动"
          onConfirm={handleConfirmEstimate}
          confirming={estimateState.confirming}
          reserveTitle="更多方式"
          reserveContent={(
            <View className="reserve-grid">
              <View className="reserve-card">
                <Text className="reserve-card-title">截图识别</Text>
                <Text className="reserve-card-desc">训练截图识别会继续补充到这里，入口保持不变。</Text>
              </View>
              <View className="reserve-card">
                <Text className="reserve-card-title">更多来源</Text>
                <Text className="reserve-card-desc">后续可以继续接入设备摘要和更多智能估算方式。</Text>
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

          <View className="button-row">
            <Button className="primary-button button-block" loading={saving} onClick={handleSubmit}>
              保存活动记录
            </Button>
          </View>
          {error ? <Text className="error-text">{error}</Text> : null}
        </View>

        <View className="placeholder-panel">
          <View className="section-heading">
            <Text className="record-panel-title">截图识别</Text>
            <Text className="section-desc">截图识别即将支持，后续可直接从这里识别训练内容。</Text>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              选择截图
            </Button>
          </View>
          <View className="button-row">
            <Button className="soft-button button-block" disabled>
              截图识别即将支持
            </Button>
          </View>
        </View>

        <View className="section-card record-list-card">
          <View className="section-heading">
            <Text className="record-panel-title">今日活动记录</Text>
            <Text className="section-desc">今天新增或编辑过的活动都会同步到这里。</Text>
          </View>
          {loading ? <Text className="hint-text">活动记录同步中...</Text> : null}
          {safeList(items).length ? (
            safeList(items).map((item) => (
              <View className="list-row" key={item.id}>
                <View className="status-pill-row">
                  <Text className="status-pill status-pill--negative">活动</Text>
                </View>
                <Text className="list-title">{item.name}</Text>
                <Text className="list-subtitle">{getRecordTimeLabel(item)}</Text>
                <Text className="list-kcal list-kcal-negative">-{item.kcal} kcal</Text>
                <View className="list-row-actions">
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
