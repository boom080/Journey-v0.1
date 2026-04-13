import React from "react";
import { Button, Text, Textarea, View } from "@tarojs/components";

export default function AiEstimatePanel({
  visible = true,
  eyebrow = "AI 辅助估算",
  title,
  description = "",
  placeholder,
  inputValue,
  onInputChange,
  onSubmit,
  submitLabel,
  loading = false,
  loadingText = "正在计算，请稍候...",
  summary = "",
  error = "",
  items = [],
  renderResultItem,
  confirmLabel,
  onConfirm,
  confirming = false,
  reserveTitle,
  reserveContent
}) {
  return (
    <View
      className="section-card ai-panel"
      style={{ display: visible ? "block" : "none" }}
    >
      <View className="section-heading">
        <Text className="eyebrow eyebrow-soft">{eyebrow}</Text>
        <Text className="record-panel-title">{title}</Text>
        {description ? <Text className="section-desc">{description}</Text> : null}
      </View>

      <View className="field-group">
        <Textarea
          className="field-textarea"
          placeholder={placeholder}
          value={inputValue}
          maxlength={500}
          autoHeight
          cursorSpacing={160}
          showConfirmBar
          adjustPosition
          onInput={(event) => onInputChange(event.detail.value)}
        />
      </View>

      <View className="button-row">
        <Button
          className="soft-button button-block"
          loading={loading}
          disabled={loading}
          onClick={onSubmit}
        >
          {loading ? loadingText : submitLabel}
        </Button>
      </View>

      {loading ? (
        <View className="ai-panel-loading">
          <Text className="hint-text">{loadingText}</Text>
          <View className="ai-skeleton-line ai-skeleton-line--primary" />
          <View className="ai-skeleton-line" />
          <View className="ai-skeleton-line ai-skeleton-line--short" />
        </View>
      ) : null}

      {summary ? (
        <View className="ai-panel-summary">
          <Text className="hint-text">{summary}</Text>
        </View>
      ) : null}
      {error ? <Text className="error-text">{error}</Text> : null}

      {Array.isArray(items) && items.length ? (
        <View className="ai-result-shell ai-result-shell--visible">
          {items.map((item, index) => renderResultItem(item, index))}
          {confirmLabel && onConfirm ? (
            <View className="button-row">
              <Button
                className="primary-button button-block"
                loading={confirming}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </View>
          ) : null}
        </View>
      ) : null}

      {reserveTitle ? (
        <View className="section-heading spacer-top">
          <Text className="record-panel-title">{reserveTitle}</Text>
        </View>
      ) : null}
      {reserveContent || null}
    </View>
  );
}
