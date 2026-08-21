import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { Goal, GoalKind } from '@journey/contracts';
import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, Field, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { goalLabels, todayIsoDate } from '@/lib/format';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

const kinds: GoalKind[] = ['lose_fat', 'gain_muscle', 'maintain'];

export default function GoalSettingsScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const existing = useQuery({ queryKey: ['goal'], queryFn: sync.fetchGoal });
  return <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}><KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><View style={[styles.header, { borderBottomColor: theme.colors.border }]}><Button variant="ghost" onPress={() => router.back()}>取消</Button><Text style={[styles.title, { color: theme.colors.text }]}>目标设置</Text><View style={styles.spacer} /></View><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>{existing.isLoading ? <LoadingState /> : <GoalForm initial={existing.data ?? null} />}</ScrollView></KeyboardAvoidingView></SafeAreaView>;
}

function GoalForm({ initial }: { initial: Goal | null }) {
  const theme = useJourneyTheme();
  const sync = useSync();
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<GoalKind>(initial?.kind ?? 'maintain');
  const [weight, setWeight] = useState(initial?.target_weight_kg == null ? '' : String(initial.target_weight_kg));
  const [energy, setEnergy] = useState(initial?.daily_energy_target_kcal == null ? '' : String(initial.daily_energy_target_kcal));
  const [targetDate, setTargetDate] = useState(initial?.target_date ?? '');
  const [error, setError] = useState('');
  const save = useMutation({
    mutationFn: (payload: Parameters<typeof sync.saveGoal>[1]) => sync.saveGoal(initial, payload),
    onSuccess: async (result) => {
      if (result === 'conflict') { setError('云端已有新版本，请到“我的”选择保留本机或使用云端。'); return; }
      await Promise.all([queryClient.invalidateQueries({ queryKey: ['goal'] }), queryClient.invalidateQueries({ queryKey: ['home'] })]);
      router.back();
    },
  });

  function submit() {
    const weightValue = weight ? Number(weight) : null; const energyValue = energy ? Number(energy) : null;
    if (weightValue != null && (weightValue < 25 || weightValue > 400)) { setError('目标体重需在 25—400 kg 之间'); return; }
    if (energyValue != null && (!Number.isInteger(energyValue) || energyValue < 800 || energyValue > 10000)) { setError('每日能量需为 800—10000 kcal 的整数'); return; }
    if (targetDate && !/^\d{4}-\d{2}-\d{2}$/.test(targetDate)) { setError('目标日期格式应为 YYYY-MM-DD'); return; }
    setError(''); save.mutate({ kind, target_weight_kg: weightValue, daily_energy_target_kcal: energyValue, starts_on: initial?.starts_on ?? todayIsoDate(), target_date: targetDate || null }, { onError: (reason) => setError(reason instanceof Error ? reason.message : '保存失败') });
  }

  return <><Card><SectionTitle>这段 Journey 想去哪里</SectionTitle>{!sync.isOnline && <Notice tone="info">修改将加密保存在本机，联网后同步。</Notice>}<View style={styles.chips}>{kinds.map((item) => <Chip key={item} label={goalLabels[item]} selected={kind === item} onPress={() => setKind(item)} />)}</View><Field label="目标体重（kg）" hint="可留空" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" /><Field label="每日能量目标（kcal）" hint="可留空；这里只保存你设定的目标" value={energy} onChangeText={setEnergy} keyboardType="number-pad" /><Field label="目标日期" hint="YYYY-MM-DD，可留空" value={targetDate} onChangeText={setTargetDate} keyboardType="numbers-and-punctuation" />{!!error && <Notice tone="error">{error}</Notice>}<Button loading={save.isPending} onPress={submit}>保存目标</Button></Card><Text style={[styles.note, { color: theme.colors.textMuted }]}>目标用于记录与反馈，不构成医疗或营养处方。</Text></>;
}

const styles = StyleSheet.create({ safe: { flex: 1 }, header: { minHeight: 58, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: journeySpacing.md }, title: { fontSize: journeyTypography.subtitle, fontWeight: '800' }, spacer: { width: 72 }, content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg, gap: journeySpacing.md }, chips: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm }, note: { fontSize: journeyTypography.caption, lineHeight: 18, textAlign: 'center' } });
