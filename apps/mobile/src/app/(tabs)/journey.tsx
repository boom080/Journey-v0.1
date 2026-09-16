import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ActivityRecord, AgentSummaryResponse, FoodRecord, GoalKind, JourneyDay, WeightRecord } from '@journey/contracts';
import { journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, EmptyState, ErrorState, LoadingState, Metric, Notice, SectionTitle } from '@/components/ui';
import { ScreenShell } from '@/components/screen-shell';
import { ApiError, ApiNetworkError, generateJourneySummary } from '@/lib/api';
import { formatDate, formatNumber, formatTime, intensityLabels, mealLabels } from '@/lib/format';
import { estimateEnergyEquivalent, type EnergyEquivalentEstimate, summarizeJourneyDays } from '@/lib/journey-summary';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

function recordMeta(record: FoodRecord | ActivityRecord | WeightRecord) {
  return { version: String(record.version), createdAt: record.created_at, updatedAt: record.updated_at };
}

function openFood(record: FoodRecord) {
  router.push({ pathname: '/record/[kind]', params: { ...recordMeta(record), kind: 'food', id: record.id, name: record.name, energy: String(record.energy_kcal), meal: record.meal_type, detail: record.detail ?? '', portion: record.portion_amount == null ? '' : String(record.portion_amount), portionUnit: record.portion_unit ?? '', timestamp: record.recorded_at } });
}

function openActivity(record: ActivityRecord) {
  router.push({ pathname: '/record/[kind]', params: { ...recordMeta(record), kind: 'activity', id: record.id, name: record.name, energy: String(record.energy_kcal), duration: String(record.duration_minutes), intensity: record.intensity, detail: record.note ?? '', timestamp: record.recorded_at } });
}

function openWeight(record: WeightRecord) {
  router.push({ pathname: '/record/[kind]', params: { ...recordMeta(record), kind: 'weight', id: record.id, weight: String(record.weight_kg), detail: record.note ?? '', timestamp: record.measured_at } });
}

function RecordRow({ label, meta, color, onPress }: { label: string; meta: string; color: string; onPress: () => void }) {
  const theme = useJourneyTheme();
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.record, { backgroundColor: theme.colors.background, opacity: pressed ? 0.7 : 1 }]}><View style={[styles.dot, { backgroundColor: color }]} /><View style={styles.recordCopy}><Text style={[styles.recordTitle, { color: theme.colors.text }]}>{label}</Text><Text style={[styles.meta, { color: theme.colors.textMuted }]}>{meta}</Text></View><Text style={{ color: theme.colors.textMuted }}>›</Text></Pressable>;
}

function energyEquivalentLabel(goalKind: GoalKind | undefined) {
  if (goalKind === 'lose_fat') return '减脂能量等效';
  if (goalKind === 'gain_muscle') return '增重能量等效';
  return '热量能量等效';
}

function energyEquivalentValue(estimate: EnergyEquivalentEstimate | null, goalKind: GoalKind | undefined) {
  if (!estimate) return '记录不足';
  if (goalKind === 'lose_fat') {
    return estimate.balanceKcal < 0 ? `≈ ${formatNumber(Math.abs(estimate.equivalentKg), 2)} kg` : '未形成缺口';
  }
  if (goalKind === 'gain_muscle') {
    return estimate.balanceKcal > 0 ? `≈ ${formatNumber(estimate.equivalentKg, 2)} kg` : '未形成盈余';
  }
  const sign = estimate.equivalentKg > 0 ? '+' : '';
  return `${sign}${formatNumber(estimate.equivalentKg, 2)} kg`;
}

function weightChangeLabel(value: number | null) {
  if (value == null) return '记录不足';
  return `${value > 0 ? '+' : ''}${formatNumber(value, 1)} kg`;
}

const summaryMinimumDays: Record<7 | 30, number> = { 7: 2, 30: 7 };

function formatSummaryGeneratedAt(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value));
}

function DayCard({ day }: { day: JourneyDay }) {
  const theme = useJourneyTheme();
  const empty = day.food_records.length + day.activity_records.length + day.weight_records.length === 0;
  return <Card>
    <SectionTitle action={<Text style={[styles.net, { color: day.net_kcal > 0 ? theme.colors.food : theme.colors.primaryStrong }]}>{formatNumber(day.net_kcal)} kcal</Text>}>{formatDate(day.date)}</SectionTitle>
    <Text style={[styles.meta, { color: theme.colors.textMuted }]}>摄入 {formatNumber(day.intake_kcal)} · 运动 {formatNumber(day.activity_kcal)} · 记录差值</Text>
    {empty && <Text style={[styles.meta, { color: theme.colors.textMuted }]}>这一天没有记录。</Text>}
    {day.food_records.map((record) => <RecordRow key={record.id} label={record.name} meta={`${mealLabels[record.meal_type]} · ${formatNumber(record.energy_kcal)} kcal · ${formatTime(record.recorded_at)}`} color={theme.colors.food} onPress={() => openFood(record)} />)}
    {day.activity_records.map((record) => <RecordRow key={record.id} label={record.name} meta={`${record.duration_minutes} 分钟 · ${intensityLabels[record.intensity]} · ${formatNumber(record.energy_kcal)} kcal`} color={theme.colors.primaryStrong} onPress={() => openActivity(record)} />)}
    {day.weight_records.map((record) => <RecordRow key={record.id} label={`${formatNumber(record.weight_kg, 1)} kg`} meta={`${formatTime(record.measured_at)}${record.note ? ` · ${record.note}` : ''}`} color={theme.colors.info} onPress={() => openWeight(record)} />)}
  </Card>;
}

export default function JourneyScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const [range, setRange] = useState<7 | 30>(7);
  const [aiSummaries, setAiSummaries] = useState<Record<7 | 30, AgentSummaryResponse | null>>({ 7: null, 30: null });
  const [summaryPending, setSummaryPending] = useState<Record<7 | 30, boolean>>({ 7: false, 30: false });
  const [summaryErrors, setSummaryErrors] = useState<Record<7 | 30, string>>({ 7: '', 30: '' });
  const [knowledgeExpanded, setKnowledgeExpanded] = useState<Record<7 | 30, boolean>>({ 7: false, 30: false });
  const journey = useQuery({
    queryKey: ['journey', range],
    queryFn: () => sync.fetchJourney(range, undefined, range),
  });
  const goal = useQuery({ queryKey: ['goal'], queryFn: sync.fetchGoal });
  const home = useQuery({ queryKey: ['home'], queryFn: sync.fetchHome });
  const summary = useMemo(() => {
    return summarizeJourneyDays(journey.data?.items ?? []);
  }, [journey.data]);
  const energyEquivalent = useMemo(() => estimateEnergyEquivalent(
    journey.data?.items ?? [],
    home.data?.resting_energy.kcal_per_day,
  ), [home.data?.resting_energy.kcal_per_day, journey.data]);
  const maxNet = Math.max(1, ...(journey.data?.items.map((day) => Math.abs(day.net_kcal)) ?? [1]));
  const aiSummary = aiSummaries[range];
  const selectedStatistics = aiSummary
    ? (range === 7 ? aiSummary.statistics.last_7_days : aiSummary.statistics.last_30_days)
    : null;
  const recordedDays = journey.data?.items.length ?? 0;
  const minimumDays = summaryMinimumDays[range];
  const remainingDays = Math.max(0, minimumDays - recordedDays);
  const canGenerateSummary = recordedDays >= minimumDays;

  async function generateSummary() {
    const period = range;
    if (!sync.isOnline) {
      setSummaryErrors((current) => ({ ...current, [period]: `联网后才能生成 AI ${period}天总结。` }));
      return;
    }
    if (!canGenerateSummary) return;
    setSummaryPending((current) => ({ ...current, [period]: true }));
    setSummaryErrors((current) => ({ ...current, [period]: '' }));
    try {
      const result = await generateJourneySummary(period);
      setAiSummaries((current) => ({ ...current, [period]: result }));
      setKnowledgeExpanded((current) => ({ ...current, [period]: false }));
    }
    catch (reason) {
      setSummaryErrors((current) => ({
        ...current,
        [period]: reason instanceof ApiError || reason instanceof ApiNetworkError
          ? reason.message
          : `AI ${period}天总结暂时不可用`,
      }));
    }
    finally { setSummaryPending((current) => ({ ...current, [period]: false })); }
  }

  function closeSummary() {
    const period = range;
    setAiSummaries((current) => ({ ...current, [period]: null }));
    setSummaryErrors((current) => ({ ...current, [period]: '' }));
    setKnowledgeExpanded((current) => ({ ...current, [period]: false }));
  }

  return (
    <ScreenShell eyebrow="JOURNEY / 回看" title="看见每一步">
      {!sync.isOnline && <Notice tone="info">当前读取本机加密副本；新增、编辑和删除会在联网后同步。</Notice>}
      <View style={styles.range}><Chip label="近 7 天" selected={range === 7} onPress={() => setRange(7)} /><Chip label="近 30 天" selected={range === 30} onPress={() => setRange(30)} /></View>
      {journey.isLoading ? <LoadingState label="正在整理 Journey…" /> : journey.isError ? <ErrorState message="Journey 暂时无法加载" onRetry={() => void journey.refetch()} /> : journey.data ? (
        <>
          <View style={styles.metrics}><Metric label={`${range}天摄入`} value={`${formatNumber(summary.intake)} kcal`} accent={theme.colors.food} /><Metric label={`${range}天运动`} value={`${formatNumber(summary.activity)} kcal`} accent={theme.colors.primaryStrong} /><Metric label="静息估算/天" value={home.data?.resting_energy.kcal_per_day == null ? '待补资料' : `${formatNumber(home.data.resting_energy.kcal_per_day)} kcal`} /><Metric label={energyEquivalentLabel(goal.data?.kind)} value={energyEquivalentValue(energyEquivalent, goal.data?.kind)} /><Metric label="当前目标" value={goal.data ? (goal.data.kind === 'lose_fat' ? '减脂' : goal.data.kind === 'gain_muscle' ? '增肌' : '保持') : '未设置'} /></View>
          <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{energyEquivalent
            ? `按有饮食记录的 ${energyEquivalent.loggedDays} 天计算：记录口径热量${energyEquivalent.balanceKcal >= 0 ? '盈余' : '缺口'} ${formatNumber(Math.abs(energyEquivalent.balanceKcal))} kcal。它只是热量能量等效，不代表实际脂肪或体重变化；漏记、水分和代谢适应都会造成偏差。${goal.data?.kind === 'gain_muscle' ? ' 热量盈余不能单独推算肌肉增长量。' : ''}`
            : '需要至少一天饮食记录和可用的静息能量估算，才能显示热量能量等效。'} 同期称重记录变化：{summary.weightChange == null ? '记录不足' : `${summary.weightChange > 0 ? '+' : ''}${formatNumber(summary.weightChange, 1)} kg`}。</Text>
          <Card style={{ backgroundColor: theme.colors.hero }}>
            <SectionTitle>趋势速览</SectionTitle>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>柱长表示每日“摄入－已记录运动”的绝对值；它是记录差值，不是完整能量结余。</Text>
            {(journey.data.items.slice(0, range)).map((day) => <View key={day.date} style={styles.trendRow}><Text style={[styles.trendDate, { color: theme.colors.textMuted }]}>{day.date.slice(5)}</Text><View style={[styles.track, { backgroundColor: theme.colors.surface }]}><View style={[styles.bar, { width: `${Math.max(4, Math.abs(day.net_kcal) / maxNet * 100)}%`, backgroundColor: day.net_kcal > 0 ? theme.colors.food : theme.colors.primaryStrong }]} /></View><Text style={[styles.trendValue, { color: theme.colors.text }]}>{formatNumber(day.net_kcal)}</Text></View>)}
          </Card>
          <Card>
            <SectionTitle action={aiSummary ? <View style={styles.summaryActions}>
              <Button accessibilityLabel={`刷新AI ${range}天总结`} variant="ghost" loading={summaryPending[range]} disabled={!sync.isOnline || !canGenerateSummary} onPress={() => void generateSummary()}>刷新</Button>
              <Button accessibilityLabel={`关闭AI ${range}天总结`} variant="ghost" onPress={closeSummary}>关闭</Button>
            </View> : <Button accessibilityLabel={`生成AI ${range}天总结`} variant="ghost" loading={summaryPending[range]} disabled={!sync.isOnline || !canGenerateSummary} onPress={() => void generateSummary()}>{canGenerateSummary ? '生成' : `还差 ${remainingDays} 天`}</Button>}>AI {range}天总结</SectionTitle>
            {!aiSummary ? <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{canGenerateSummary
              ? `已达到生成条件：近${range}天有${recordedDays}个记录日。基础统计由后端计算，AI 只负责生成发现和接下来7天建议。`
              : `近${range}天已有${recordedDays}个记录日；至少需要${minimumDays}天，再记录${remainingDays}天即可生成。`}</Text> : <>
              <Text style={[styles.generatedAt, { color: theme.colors.textMuted }]}>生成于 {formatSummaryGeneratedAt(aiSummary.generated_at)}{aiSummary.cache_hit ? ' · 已复用最新结果' : ''}</Text>
              <View style={[styles.headline, { backgroundColor: theme.colors.infoSoft }]}>
                <Text style={[styles.headlineText, { color: theme.colors.text }]}>{aiSummary.content.headline}</Text>
              </View>

              <Text style={[styles.summaryLabel, { color: theme.colors.text }]}>数据概览</Text>
              <View style={styles.summaryMetrics}>
                <Metric label="记录数" value={`${selectedStatistics?.record_count ?? 0} 条`} />
                <Metric label={`近${range}天摄入`} value={`${formatNumber(selectedStatistics?.total_intake_kcal ?? 0)} kcal`} accent={theme.colors.food} />
                <Metric label={`近${range}天运动消耗`} value={`${formatNumber(selectedStatistics?.total_activity_kcal ?? 0)} kcal`} accent={theme.colors.primaryStrong} />
                <Metric label="有记录天数 / 体重变化" value={`${selectedStatistics?.days_with_records ?? 0} 天 / ${weightChangeLabel(selectedStatistics?.weight_change_kg ?? null)}`} />
              </View>

              <Text style={[styles.summaryLabel, { color: theme.colors.text }]}>AI发现</Text>
              <View style={styles.summaryList}>{aiSummary.content.key_findings.map((finding, index) => <View key={`${index}-${finding.title}`} style={styles.summaryItem}>
                <Text style={[styles.summaryIndex, { color: theme.colors.primaryStrong }]}>{index + 1}</Text>
                <View style={styles.summaryItemCopy}>
                  <Text style={[styles.summaryItemTitle, { color: theme.colors.text }]}>{finding.title}</Text>
                  <Text style={[styles.summaryCopy, { color: theme.colors.textMuted }]}>证据：{finding.evidence}</Text>
                  <Text style={[styles.summaryCopy, { color: theme.colors.text }]}>意味着：{finding.interpretation}</Text>
                </View>
              </View>)}</View>

              <Text style={[styles.summaryLabel, { color: theme.colors.text }]}>接下来7天</Text>
              <View style={styles.summaryList}>{aiSummary.content.next_7_days.map((action, index) => <View key={`${index}-${action.title}`} style={[styles.actionCard, { backgroundColor: theme.colors.background }]}>
                <Text style={[styles.actionTitle, { color: theme.colors.text }]}>{index + 1}. {action.title}</Text>
                <Text style={[styles.summaryCopy, { color: theme.colors.text }]}>{action.plan}</Text>
                <Text style={[styles.actionMeta, { color: theme.colors.textMuted }]}>为什么：{action.reason}</Text>
                <Text style={[styles.actionMetric, { color: theme.colors.primaryStrong }]}>验收：{action.success_metric}</Text>
              </View>)}</View>

              <Pressable accessibilityRole="button" accessibilityState={{ expanded: knowledgeExpanded[range] }} onPress={() => setKnowledgeExpanded((current) => ({ ...current, [range]: !current[range] }))} style={({ pressed }) => [styles.knowledgeToggle, { borderColor: theme.colors.border, opacity: pressed ? 0.7 : 1 }]}>
                <Text style={[styles.knowledgeToggleText, { color: theme.colors.text }]}>知识依据 {aiSummary.citations.length} 条</Text>
                <Text style={{ color: theme.colors.textMuted }}>{knowledgeExpanded[range] ? '⌃' : '›'}</Text>
              </Pressable>
              {knowledgeExpanded[range] && <View style={styles.knowledgeList}>{aiSummary.citations.length ? aiSummary.citations.map((citation) => <View key={citation.chunk_id} style={[styles.knowledgeItem, { backgroundColor: theme.colors.background }]}><Text style={[styles.knowledgeTitle, { color: theme.colors.text }]}>{citation.title} · v{citation.version}</Text><Text style={[styles.meta, { color: theme.colors.textMuted }]}>{citation.excerpt}</Text></View>) : <Text style={[styles.meta, { color: theme.colors.textMuted }]}>本次只使用结构化记录，没有调用知识库。</Text>}</View>}
            </>}
            {!!summaryErrors[range] && <Notice tone="error">{summaryErrors[range]}</Notice>}
          </Card>
          <SectionTitle action={<Button variant="ghost" onPress={() => void journey.refetch()}>刷新</Button>}>时间线</SectionTitle>
          {!journey.data.items.length ? <EmptyState title="还没有 Journey" message="从首页新增一条饮食、运动或体重记录，这里会按天归档。" action={<Button onPress={() => router.push('/record/food')}>记录第一餐</Button>} /> : journey.data.items.map((day) => <DayCard key={day.date} day={day} />)}
        </>
      ) : null}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  range: { flexDirection: 'row', gap: journeySpacing.sm }, metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  meta: { fontSize: journeyTypography.small, lineHeight: 21 },
  generatedAt: { fontSize: journeyTypography.caption, lineHeight: 18 }, summaryActions: { flexDirection: 'row', alignItems: 'center', gap: journeySpacing.xs },
  headline: { borderRadius: journeyRadii.sm, padding: journeySpacing.md }, headlineText: { fontSize: journeyTypography.body, lineHeight: 25, fontWeight: '800' },
  summaryLabel: { fontSize: journeyTypography.body, fontWeight: '800', marginTop: 2 }, summaryMetrics: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  summaryList: { gap: 10 }, summaryItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 }, summaryItemCopy: { flex: 1, gap: 5 }, summaryItemTitle: { fontSize: journeyTypography.small, lineHeight: 22, fontWeight: '800' }, summaryIndex: { width: 22, height: 22, borderRadius: 11, textAlign: 'center', fontWeight: '900', lineHeight: 22 }, summaryCopy: { fontSize: journeyTypography.small, lineHeight: 22 },
  actionCard: { borderRadius: journeyRadii.sm, padding: 13, gap: 7 }, actionTitle: { fontSize: journeyTypography.body, lineHeight: 23, fontWeight: '900' }, actionMeta: { fontSize: journeyTypography.caption, lineHeight: 20 }, actionMetric: { fontSize: journeyTypography.small, lineHeight: 21, fontWeight: '800' },
  knowledgeToggle: { minHeight: 48, borderTopWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 2, paddingTop: 12 }, knowledgeToggleText: { fontSize: journeyTypography.small, fontWeight: '800' }, knowledgeList: { gap: journeySpacing.sm }, knowledgeItem: { borderRadius: journeyRadii.sm, padding: 12, gap: 4 }, knowledgeTitle: { fontSize: journeyTypography.small, fontWeight: '800' },
  net: { fontSize: journeyTypography.small, fontWeight: '900' }, record: { minHeight: 58, borderRadius: journeyRadii.sm, flexDirection: 'row', alignItems: 'center', padding: 12, gap: 10 },
  dot: { width: 8, height: 32, borderRadius: 4 }, recordCopy: { flex: 1, gap: 3 }, recordTitle: { fontSize: journeyTypography.body, fontWeight: '700' },
  trendRow: { flexDirection: 'row', alignItems: 'center', gap: 8 }, trendDate: { width: 42, fontSize: 12 }, track: { flex: 1, height: 12, borderRadius: 6, overflow: 'hidden' }, bar: { height: 12, borderRadius: 6 }, trendValue: { width: 48, textAlign: 'right', fontSize: 12 },
});
