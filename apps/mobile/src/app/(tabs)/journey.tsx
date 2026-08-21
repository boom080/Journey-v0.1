import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ActivityRecord, AgentRunResponse, FoodRecord, JourneyDay, WeightRecord } from '@journey/contracts';
import { journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, EmptyState, ErrorState, LoadingState, Metric, Notice, SectionTitle } from '@/components/ui';
import { ScreenShell } from '@/components/screen-shell';
import { ApiError, ApiNetworkError, runAgent } from '@/lib/api';
import { formatDate, formatNumber, formatTime, intensityLabels, mealLabels } from '@/lib/format';
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
  const [weekly, setWeekly] = useState<AgentRunResponse | null>(null);
  const [weeklyPending, setWeeklyPending] = useState(false);
  const [weeklyError, setWeeklyError] = useState('');
  const journey = useQuery({
    queryKey: ['journey', range],
    queryFn: () => sync.fetchJourney(range, undefined, range),
  });
  const goal = useQuery({ queryKey: ['goal'], queryFn: sync.fetchGoal });
  const home = useQuery({ queryKey: ['home'], queryFn: sync.fetchHome });
  const summary = useMemo(() => {
    const days = journey.data?.items ?? [];
    const totals = days.reduce((acc, day) => ({ intake: acc.intake + day.intake_kcal, activity: acc.activity + day.activity_kcal, records: acc.records + day.food_records.length + day.activity_records.length + day.weight_records.length }), { intake: 0, activity: 0, records: 0 });
    const weights = days.flatMap((day) => day.weight_records).sort((left, right) => new Date(left.measured_at).getTime() - new Date(right.measured_at).getTime());
    const firstWeight = weights[0];
    const latestWeight = weights.at(-1);
    return { ...totals, weightChange: firstWeight && latestWeight ? latestWeight.weight_kg - firstWeight.weight_kg : null };
  }, [journey.data]);
  const maxNet = Math.max(1, ...(journey.data?.items.map((day) => Math.abs(day.net_kcal)) ?? [1]));

  async function generateWeeklySummary() {
    if (!sync.isOnline) { setWeeklyError('联网后才能生成 Agent 周总结。'); return; }
    setWeeklyPending(true); setWeeklyError('');
    try { setWeekly(await runAgent(range === 7 ? '请生成我的近7天目标执行总结和下一阶段建议' : '请生成我的近30天趋势、目标执行总结和下一阶段建议')); }
    catch (reason) { setWeeklyError(reason instanceof ApiError || reason instanceof ApiNetworkError ? reason.message : '周总结暂时不可用'); }
    finally { setWeeklyPending(false); }
  }

  return (
    <ScreenShell eyebrow="JOURNEY / 回看" title="看见每一步">
      {!sync.isOnline && <Notice tone="info">当前读取本机加密副本；新增、编辑和删除会在联网后同步。</Notice>}
      <View style={styles.range}><Chip label="近 7 天" selected={range === 7} onPress={() => setRange(7)} /><Chip label="近 30 天" selected={range === 30} onPress={() => setRange(30)} /></View>
      {journey.isLoading ? <LoadingState label="正在整理 Journey…" /> : journey.isError ? <ErrorState message="Journey 暂时无法加载" onRetry={() => void journey.refetch()} /> : journey.data ? (
        <>
          <View style={styles.metrics}><Metric label={`${range}天摄入`} value={`${formatNumber(summary.intake)} kcal`} accent={theme.colors.food} /><Metric label={`${range}天运动`} value={`${formatNumber(summary.activity)} kcal`} accent={theme.colors.primaryStrong} /><Metric label="静息估算/天" value={home.data?.resting_energy.kcal_per_day == null ? '待补资料' : `${formatNumber(home.data.resting_energy.kcal_per_day)} kcal`} /><Metric label="体重变化" value={summary.weightChange == null ? '记录不足' : `${summary.weightChange > 0 ? '+' : ''}${formatNumber(summary.weightChange, 1)} kg`} /><Metric label="当前目标" value={goal.data ? (goal.data.kind === 'lose_fat' ? '减脂' : goal.data.kind === 'gain_muscle' ? '增肌' : '保持') : '未设置'} /></View>
          <Card style={{ backgroundColor: theme.colors.hero }}>
            <SectionTitle>趋势速览</SectionTitle>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>柱长表示每日“摄入－已记录运动”的绝对值；它是记录差值，不是完整能量结余。</Text>
            {(journey.data.items.slice(0, range)).map((day) => <View key={day.date} style={styles.trendRow}><Text style={[styles.trendDate, { color: theme.colors.textMuted }]}>{day.date.slice(5)}</Text><View style={[styles.track, { backgroundColor: theme.colors.surface }]}><View style={[styles.bar, { width: `${Math.max(4, Math.abs(day.net_kcal) / maxNet * 100)}%`, backgroundColor: day.net_kcal > 0 ? theme.colors.food : theme.colors.primaryStrong }]} /></View><Text style={[styles.trendValue, { color: theme.colors.text }]}>{formatNumber(day.net_kcal)}</Text></View>)}
          </Card>
          <Card>
            <SectionTitle action={<Button variant="ghost" loading={weeklyPending} disabled={!sync.isOnline} onPress={() => void generateWeeklySummary()}>生成</Button>}>AI {range} 天总结</SectionTitle>
            <Text style={[styles.summary, { color: theme.colors.text }]}>{weekly?.answer ?? `近 ${range} 天记录了 ${summary.records} 条，摄入 ${formatNumber(summary.intake)} kcal，运动消耗 ${formatNumber(summary.activity)} kcal。`}</Text>
            {weekly?.citations.map((citation) => <Text key={citation.chunk_id} style={[styles.meta, { color: theme.colors.textMuted }]}>依据：{citation.title} · v{citation.version}</Text>)}
            {weekly?.fallback_used && <Notice tone="info">当前使用 Mock 或确定性降级，未调用外部模型。</Notice>}
            {!!weeklyError && <Notice tone="error">{weeklyError}</Notice>}
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>总结只读取结构化画像、目标、聚合记录与受控知识，不会自动修改数据。</Text>
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
  meta: { fontSize: journeyTypography.small, lineHeight: 21 }, summary: { fontSize: journeyTypography.body, lineHeight: 25, fontWeight: '600' },
  net: { fontSize: journeyTypography.small, fontWeight: '900' }, record: { minHeight: 58, borderRadius: journeyRadii.sm, flexDirection: 'row', alignItems: 'center', padding: 12, gap: 10 },
  dot: { width: 8, height: 32, borderRadius: 4 }, recordCopy: { flex: 1, gap: 3 }, recordTitle: { fontSize: journeyTypography.body, fontWeight: '700' },
  trendRow: { flexDirection: 'row', alignItems: 'center', gap: 8 }, trendDate: { width: 42, fontSize: 12 }, track: { flex: 1, height: 12, borderRadius: 6, overflow: 'hidden' }, bar: { height: 12, borderRadius: 6 }, trendValue: { width: 48, textAlign: 'right', fontSize: 12 },
});
