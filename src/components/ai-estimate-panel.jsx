import React from "react";
import { Button, Text, Textarea, View } from "@tarojs/components";

export default function AiEstimatePanel({
  visible = true,
  title,
  placeholder,
  inputValue,
  onInputChange,
  onSubmit,
  submitLabel,
  loading = false,
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
      className="placeholder-panel"
      style={{ display: visible ? "block" : "none" }}
    >
      <Text className="record-panel-title">{title}</Text>
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
        <Button className="soft-button button-block" loading={loading} onClick={onSubmit}>
          {submitLabel}
        </Button>
      </View>

      {summary ? <Text className="hint-text">{summary}</Text> : null}
      {error ? <Text className="error-text">{error}</Text> : null}

      {Array.isArray(items) && items.length ? (
        <View className="ai-result-shell">
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

      {reserveTitle ? <Text className="record-panel-title spacer-top">{reserveTitle}</Text> : null}
      {reserveContent || null}
    </View>
  );
}
