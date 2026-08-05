import { Image } from 'expo-image';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { journeyColors, journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';
import type { HomeToday } from '@journey/contracts';

import { formatDate, formatNumber, goalLabels, todayIsoDate } from '@/lib/format';

export const warmHomeColors = {
  background: '#FBFFFD',
  backgroundSoft: journeyColors.mint50,
  hero: journeyColors.mint500,
  heroDeep: '#55B98E',
  surface: journeyColors.surface,
  border: journeyColors.border,
  text: journeyColors.ink900,
  muted: journeyColors.ink600,
  primary: journeyColors.mint700,
} as const;

const suggestions = [
  { label: '吃了一碗…', value: '午饭吃了一碗' },
  { label: '运动了 30 分钟', value: '今天运动了 30 分钟' },
  { label: '今天状态如何？', value: '根据今天的记录给我一个建议' },
] as const;

type WarmHomeHeroProps = {
  input: string;
  isOnline: boolean;
  isAnalyzing: boolean;
  imageEnabled: boolean;
  date?: string;
  onInputChange: (value: string) => void;
  onAnalyze: () => void;
  onImagePress: () => void;
};

export function WarmHomeHero({
  input,
  isOnline,
  isAnalyzing,
  imageEnabled,
  date,
  onInputChange,
  onAnalyze,
  onImagePress,
}: WarmHomeHeroProps) {
  const status = isOnline ? 'Agent 在线' : '离线 · 手动可用';

  return (
    <View style={styles.intro}>
      <View style={styles.header}>
        <Text style={styles.brand}>JOURNEY</Text>
        <View accessibilityLabel={`在线状态：${status}`} style={styles.status}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>{status}</Text>
        </View>
      </View>

      <View style={styles.hero}>
        <View style={styles.heroCircleLarge} />
        <View style={styles.heroCircleSmall} />
        <View style={styles.heroCopy}>
          <Text style={styles.heroDate}>{formatDate(date ?? todayIsoDate())}</Text>
          <View accessibilityLabel="你好，今天轻松记" style={styles.heroHeading}>
            <Text maxFontSizeMultiplier={1.25} style={styles.heroGreeting}>你好，</Text>
            <Text maxFontSizeMultiplier={1.25} numberOfLines={1} style={styles.heroTitle}>今天轻松记</Text>
          </View>
          <Text style={styles.heroSubtitle}>不必精确，先说下来。</Text>
        </View>
        <View style={styles.mascotFrame}>
          <Image
            accessibilityLabel="Journey 原版行走叶子吉祥物"
            source={require('@/assets/brand/journey-leaf-home.png')}
            style={styles.mascot}
            contentFit="cover"
            transition={160}
          />
        </View>
      </View>

      <View style={styles.composer}>
        <Text style={styles.composerLabel}>今天想记什么？</Text>
        <View style={styles.inputRow}>
          <TextInput
            accessibilityLabel="统一记录输入"
            multiline
            maxLength={300}
            maxFontSizeMultiplier={1.5}
            onChangeText={onInputChange}
            placeholder={isOnline ? '午饭吃了牛肉面，晚上慢跑了 30 分钟…' : '可查询内置常识；手动记录请使用下方入口…'}
            placeholderTextColor={warmHomeColors.muted}
            style={styles.input}
            textAlignVertical="top"
            value={input}
          />
          {imageEnabled && (
            <Pressable
              accessibilityLabel="📷 拍照估算饮食"
              accessibilityRole="button"
              disabled={!isOnline}
              onPress={onImagePress}
              style={({ pressed }) => [
                styles.iconButton,
                !isOnline && styles.iconButtonDisabled,
                pressed && isOnline && styles.iconButtonPressed,
              ]}>
              <Text style={styles.photoIcon}>▧</Text>
            </Pressable>
          )}
          <Pressable
            accessibilityLabel="理解并处理"
            accessibilityRole="button"
            disabled={!input.trim() || isAnalyzing}
            onPress={onAnalyze}
            style={({ pressed }) => [
              styles.iconButton,
              styles.sendButton,
              (!input.trim() || isAnalyzing) && styles.iconButtonDisabled,
              pressed && input.trim() && !isAnalyzing && styles.sendButtonPressed,
            ]}>
            {isAnalyzing ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.sendIcon}>↑</Text>}
          </Pressable>
        </View>
        <Text style={styles.helper}>
          {isOnline
            ? 'Journey 会自动归类、调用工具，并在写入前请你确认。'
            : '手动记录仍可安全保存并在联网后同步；Agent 与图片暂不可用。'}
        </Text>
      </View>

      <View accessibilityLabel="快捷输入" style={styles.suggestions}>
        {suggestions.map((suggestion) => (
          <Pressable
            accessibilityRole="button"
            key={suggestion.label}
            onPress={() => onInputChange(suggestion.value)}
            style={({ pressed }) => [styles.suggestion, pressed && styles.suggestionPressed]}>
            <Text numberOfLines={1} style={styles.suggestionText}>{suggestion.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function WarmHomeMetrics({ data, onRefresh }: { data: HomeToday; onRefresh: () => void }) {
  const target = data.active_goal?.daily_energy_target_kcal;

  return (
    <View style={styles.overview}>
      <View style={styles.overviewHeader}>
        <Text style={styles.overviewTitle}>今天的变化</Text>
        <Pressable accessibilityLabel="刷新今日数据" accessibilityRole="button" onPress={onRefresh}>
          <Text style={styles.overviewTarget}>
            {target == null ? '刷新' : `目标 ${formatNumber(target)} kcal · 刷新`}
          </Text>
        </Pressable>
      </View>
      <View style={styles.metrics}>
        <HomeMetric label="已摄入" value={formatNumber(data.intake_kcal)} unit="kcal" />
        <HomeMetric label="活动" value={formatNumber(data.activity_kcal)} unit="kcal" />
        <HomeMetric label="净结余" value={formatNumber(data.net_kcal)} unit="kcal" isLast />
      </View>
      <Text style={styles.overviewFootnote}>
        {data.active_goal ? `${goalLabels[data.active_goal.kind]}进行中` : '设置目标后，Journey 会结合你的记录给出建议'}
        {' · '}饮食 {data.counts.food} 条 · 运动 {data.counts.activity} 条 · 体重 {data.counts.weight} 条
      </Text>
    </View>
  );
}

function HomeMetric({ label, value, unit, isLast }: { label: string; value: string; unit: string; isLast?: boolean }) {
  return (
    <View style={[styles.metric, isLast && styles.metricLast]}>
      <View style={styles.metricHeading}>
        <Text style={styles.metricLabel}>{label}</Text>
        <Text style={styles.metricUnit}>{unit}</Text>
      </View>
      <Text numberOfLines={1} style={styles.metricValue}>{value}</Text>
    </View>
  );
}

type AgentStatusStripProps = {
  isOnline: boolean;
  isPending: boolean;
  hasError: boolean;
  resultStatus?: string;
  resumeRequired: boolean;
};

export function AgentStatusStrip({ isOnline, isPending, hasError, resultStatus, resumeRequired }: AgentStatusStripProps) {
  let title = 'Journey 已准备好';
  let detail = '识别意图 → 调用工具 → 等你确认 → 更新今天';

  if (!isOnline) {
    title = '当前是本地记录模式';
    detail = '手动记录 → 安全保存 → 联网后同步';
  } else if (isPending) {
    title = '正在理解这件事';
    detail = '规划和工具执行中，不会绕过你的确认';
  } else if (resumeRequired || resultStatus === 'waiting_for_user') {
    title = '等你确认后继续';
    detail = '候选确认完成后，Agent 才会执行后续步骤';
  } else if (hasError) {
    title = '这次没有完成';
    detail = '内容仍在输入框中，可以修改后重试';
  } else if (resultStatus === 'completed') {
    title = '这件事已处理完成';
    detail = '结果、工具和校验信息都在下方';
  }

  return (
    <View accessibilityLiveRegion="polite" style={styles.agentStrip}>
      <View style={styles.agentMark}><Text style={styles.agentMarkText}>✦</Text></View>
      <View style={styles.agentCopy}>
        <Text style={styles.agentTitle}>{title}</Text>
        <Text numberOfLines={1} style={styles.agentDetail}>{detail}</Text>
      </View>
      <Text style={styles.agentArrow}>›</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  intro: { gap: journeySpacing.sm },
  header: { minHeight: 42, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  brand: { color: warmHomeColors.primary, fontSize: journeyTypography.small, fontWeight: '800', letterSpacing: 1.2 },
  status: { minHeight: 32, flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 11, borderWidth: 1, borderColor: '#CCE8DC', borderRadius: journeyRadii.pill, backgroundColor: warmHomeColors.surface },
  statusDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: warmHomeColors.hero },
  statusText: { color: warmHomeColors.primary, fontSize: journeyTypography.caption, fontWeight: '700' },
  hero: { minHeight: 226, marginTop: 4, overflow: 'hidden', borderRadius: 30, backgroundColor: warmHomeColors.hero, padding: journeySpacing.lg, paddingRight: 116, justifyContent: 'center' },
  heroCircleLarge: { position: 'absolute', width: 154, height: 154, borderRadius: 77, right: -46, top: -50, backgroundColor: 'rgba(255,255,255,0.13)' },
  heroCircleSmall: { position: 'absolute', width: 82, height: 82, borderRadius: 41, right: 108, bottom: -48, backgroundColor: 'rgba(255,255,255,0.11)' },
  heroCopy: { gap: journeySpacing.md },
  heroHeading: { gap: 1 },
  heroDate: { color: '#FFFFFF', fontSize: journeyTypography.caption, fontWeight: '700', opacity: 0.92 },
  heroGreeting: { color: '#FFFFFF', fontSize: 28, lineHeight: 33, fontWeight: '800' },
  heroTitle: { color: '#FFFFFF', fontSize: 22, lineHeight: 28, fontWeight: '800' },
  heroSubtitle: { color: '#FFFFFF', fontSize: journeyTypography.small, fontWeight: '700', opacity: 0.94 },
  mascotFrame: { position: 'absolute', right: 12, bottom: 16, width: 106, height: 106, overflow: 'hidden', borderWidth: 5, borderColor: 'rgba(255,255,255,0.68)', borderRadius: 53, backgroundColor: '#9BE5C4' },
  mascot: { width: '100%', height: '100%', transform: [{ scale: 1.07 }] },
  composer: { zIndex: 2, marginHorizontal: 10, marginTop: -26, gap: 10, padding: journeySpacing.md, borderWidth: 1, borderColor: '#CCE8DC', borderRadius: 24, backgroundColor: warmHomeColors.surface, shadowColor: '#397F64', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.11, shadowRadius: 18, elevation: 4 },
  composerLabel: { color: warmHomeColors.text, fontSize: journeyTypography.subtitle, fontWeight: '800' },
  inputRow: { flexDirection: 'row', alignItems: 'center', gap: journeySpacing.sm },
  input: { flex: 1, minHeight: 62, maxHeight: 92, color: warmHomeColors.text, fontSize: journeyTypography.small, lineHeight: 21, paddingVertical: 6 },
  iconButton: { width: 46, height: 46, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#D2E9DF', borderRadius: 15, backgroundColor: '#F5FCF8' },
  sendButton: { borderColor: warmHomeColors.heroDeep, backgroundColor: warmHomeColors.heroDeep },
  iconButtonPressed: { opacity: 0.72 },
  sendButtonPressed: { backgroundColor: warmHomeColors.primary },
  iconButtonDisabled: { opacity: 0.36 },
  photoIcon: { color: warmHomeColors.primary, fontSize: 18, fontWeight: '700' },
  sendIcon: { color: '#FFFFFF', fontSize: 24, fontWeight: '700', marginTop: -2 },
  helper: { color: warmHomeColors.muted, fontSize: journeyTypography.caption, lineHeight: 18 },
  suggestions: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm, paddingHorizontal: 2, paddingTop: 4 },
  suggestion: { minHeight: 36, maxWidth: '48%', justifyContent: 'center', paddingHorizontal: 12, borderWidth: 1, borderColor: warmHomeColors.border, borderRadius: journeyRadii.pill, backgroundColor: warmHomeColors.surface },
  suggestionPressed: { backgroundColor: journeyColors.mint100 },
  suggestionText: { color: warmHomeColors.muted, fontSize: journeyTypography.caption, fontWeight: '700' },
  overview: { gap: journeySpacing.md },
  overviewHeader: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', gap: journeySpacing.md },
  overviewTitle: { color: warmHomeColors.text, fontSize: journeyTypography.subtitle, fontWeight: '800' },
  overviewTarget: { flexShrink: 1, color: warmHomeColors.muted, fontSize: journeyTypography.caption, textAlign: 'right' },
  metrics: { flexDirection: 'row', borderTopWidth: 1, borderBottomWidth: 1, borderColor: '#DCEEE6', backgroundColor: 'rgba(255,255,255,0.44)', paddingVertical: journeySpacing.md },
  metric: { flex: 1, minWidth: 0, paddingHorizontal: 8, borderRightWidth: 1, borderRightColor: '#DCEEE6' },
  metricLast: { borderRightWidth: 0 },
  metricHeading: { flexDirection: 'row', alignItems: 'baseline', gap: 3 },
  metricLabel: { color: '#789087', fontSize: journeyTypography.caption },
  metricValue: { marginTop: 5, color: warmHomeColors.text, fontSize: 20, fontWeight: '800' },
  metricUnit: { color: '#789087', fontSize: 9, fontWeight: '500' },
  overviewFootnote: { color: warmHomeColors.muted, fontSize: journeyTypography.caption, lineHeight: 18 },
  agentStrip: { minHeight: 68, flexDirection: 'row', alignItems: 'center', gap: 11, paddingHorizontal: 14, paddingVertical: 12, borderWidth: 1, borderColor: '#D5EADF', borderRadius: 18, backgroundColor: '#EFFAF4' },
  agentMark: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center', borderRadius: 13, backgroundColor: warmHomeColors.surface },
  agentMarkText: { color: warmHomeColors.primary, fontSize: 17 },
  agentCopy: { flex: 1, minWidth: 0 },
  agentTitle: { color: warmHomeColors.text, fontSize: journeyTypography.small, fontWeight: '800' },
  agentDetail: { marginTop: 3, color: warmHomeColors.muted, fontSize: 11 },
  agentArrow: { color: warmHomeColors.primary, fontSize: 22 },
});
