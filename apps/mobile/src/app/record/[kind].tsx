import { useQueryClient } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { ActivityIntensity, FoodRecordCreate, MealType, WeightRecordCreate } from '@journey/contracts';
import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, Field, Notice, SectionTitle } from '@/components/ui';
import { ApiError, confirmAgentCandidate, deleteRecord, resumeAgentRun, updateRecord, type RecordKind } from '@/lib/api';
import { intensityLabels, mealLabels } from '@/lib/format';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

const meals: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack', 'other'];
const intensities: ActivityIntensity[] = ['low', 'moderate', 'high'];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function RecordFormScreen() {
  const params = useLocalSearchParams();
  const theme = useJourneyTheme();
  const sync = useSync();
  const queryClient = useQueryClient();
  const kindValue = first(params.kind);
  const kind: RecordKind = kindValue === 'activity' || kindValue === 'weight' ? kindValue : 'food';
  const id = first(params.id);
  const candidateId = first(params.candidateId);
  const confirmationToken = first(params.confirmationToken);
  const runId = first(params.runId);
  const resumeRequired = first(params.resumeRequired) === 'true';
  const candidateSource = first(params.candidateSource);
  const isAgentCandidate = Boolean(candidateId && confirmationToken);
  const isImageCandidate = isAgentCandidate && candidateSource === 'image';
  const isEditing = Boolean(id);
  const [name, setName] = useState(first(params.name) ?? '');
  const [energy, setEnergy] = useState(first(params.energy) ?? '');
  const [detail, setDetail] = useState(first(params.detail) ?? '');
  const [meal, setMeal] = useState<MealType>((first(params.meal) as MealType) ?? 'other');
  const [portion, setPortion] = useState(first(params.portion) ?? '');
  const [portionUnit, setPortionUnit] = useState(first(params.portionUnit) ?? '');
  const [duration, setDuration] = useState(first(params.duration) ?? '');
  const [intensity, setIntensity] = useState<ActivityIntensity>((first(params.intensity) as ActivityIntensity) ?? 'moderate');
  const [weight, setWeight] = useState(first(params.weight) ?? '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  const title = kind === 'food' ? '饮食记录' : kind === 'activity' ? '运动记录' : '体重记录';
  const validation = useMemo(() => {
    if (kind === 'weight') {
      const value = Number(weight);
      return value >= 25 && value <= 400 ? '' : '体重需在 25—400 kg 之间';
    }
    if (!name.trim()) return '请填写名称';
    const kcal = Number(energy);
    if (!Number.isFinite(kcal) || kcal < 0 || kcal > 20000) return '热量需在 0—20000 kcal 之间';
    if (kind === 'activity') {
      const minutes = Number(duration);
      if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440) return '时长需为 1—1440 分钟的整数';
    }
    if (kind === 'food' && portion && Number(portion) <= 0) return '份量必须大于 0';
    return '';
  }, [duration, energy, kind, name, portion, weight]);

  function payload() {
    const timestamp = first(params.timestamp) ?? new Date().toISOString();
    if (kind === 'food') return {
      recorded_at: timestamp,
      meal_type: meal,
      name: name.trim(),
      energy_kcal: Number(energy),
      detail: detail.trim() || null,
      portion_amount: portion ? Number(portion) : null,
      portion_unit: portionUnit.trim() || null,
      source: isImageCandidate ? 'image' as const : isAgentCandidate ? 'agent' as const : 'manual' as const,
      source_ref: isAgentCandidate ? candidateId : undefined,
    } satisfies FoodRecordCreate;
    if (kind === 'activity') return {
      recorded_at: timestamp,
      name: name.trim(),
      activity_type: name.trim(),
      duration_minutes: Number(duration),
      intensity,
      energy_kcal: Number(energy),
      note: detail.trim() || null,
      source: isAgentCandidate ? 'agent' as const : 'manual' as const,
      source_ref: isAgentCandidate ? candidateId : undefined,
    };
    return {
      measured_at: timestamp,
      weight_kg: Number(weight),
      note: detail.trim() || null,
      source: isAgentCandidate ? 'agent' as const : 'manual' as const,
    } satisfies WeightRecordCreate;
  }

  async function invalidate() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['home'] }),
      queryClient.invalidateQueries({ queryKey: ['journey'] }),
      queryClient.invalidateQueries({ queryKey: ['profile'] }),
    ]);
  }

  function notifyAndReturn(title: string, message: string, actionLabel: string) {
    if (Platform.OS === 'web') {
      Alert.alert(title, message);
      router.back();
      return;
    }
    Alert.alert(title, message, [{ text: actionLabel, onPress: () => router.back() }]);
  }

  async function save() {
    if (validation) { setError(validation); return; }
    if (isAgentCandidate && !sync.isOnline) { setError('Agent 候选确认需要联网；请恢复网络后重试。'); return; }
    if (isEditing && !sync.isOnline) { setError('编辑记录需要联网；离线时可新增记录。'); return; }
    setPending(true); setError('');
    try {
      if (isEditing && id) {
        const body = payload() as unknown as Record<string, unknown>;
        delete body.source;
        await updateRecord(kind, id, body);
        await invalidate();
        Alert.alert('已更新', `${title}已同步。`, [{ text: '完成', onPress: () => router.back() }]);
      } else if (isAgentCandidate && candidateId && confirmationToken) {
        const body = payload();
        const confirmation = await confirmAgentCandidate(candidateId, {
          confirmation_token: confirmationToken,
          kind,
          payload: body,
        }, `agent-${candidateId}`);
        await invalidate();
        if (confirmation.resume_available && runId) {
          queryClient.setQueryData(['agent-resume-needed'], runId);
          try {
            const continuation = await resumeAgentRun(runId);
            queryClient.setQueryData(['agent-continuation'], continuation);
            queryClient.removeQueries({ queryKey: ['agent-resume-needed'], exact: true });
            notifyAndReturn('已确认并继续', `${title}已同步，Agent 已基于最新数据完成后续步骤。`, '查看结果');
          } catch {
            notifyAndReturn('记录已保存', 'Agent 后续步骤暂未完成，可返回首页点击“继续执行”。', '返回首页');
          }
        } else {
          const pendingCount = confirmation.confirmation_progress?.pending ?? 0;
          notifyAndReturn('已确认并保存', pendingCount ? `还需确认 ${pendingCount} 个候选。` : `${title}已同步。`, '完成');
        }
      } else {
        const result = await sync.submitRecord(kind, payload());
        Alert.alert(result === 'saved' ? '已保存' : '已加入待同步', result === 'saved' ? `${title}已同步。` : '联网后会自动上传，不需要重复提交。', [{ text: '完成', onPress: () => router.back() }]);
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '保存失败，请稍后重试');
    } finally { setPending(false); }
  }

  function confirmDelete() {
    if (!id) return;
    if (!sync.isOnline) { setError('删除记录需要联网。'); return; }
    Alert.alert('删除这条记录？', '删除后首页和 Journey 会同步更新。', [
      { text: '取消', style: 'cancel' },
      { text: '删除', style: 'destructive', onPress: () => void (async () => {
        setPending(true); setError('');
        try { await deleteRecord(kind, id); await invalidate(); router.back(); }
        catch (reason) { setError(reason instanceof ApiError ? reason.message : '删除失败'); }
        finally { setPending(false); }
      })() },
    ]);
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={[styles.header, { borderBottomColor: theme.colors.border }]}>
          <Button variant="ghost" onPress={() => router.back()}>取消</Button>
          <Text style={[styles.headerTitle, { color: theme.colors.text }]}>{isEditing ? `编辑${title}` : `新建${title}`}</Text>
          <View style={styles.headerSpacer} />
        </View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          {!sync.isOnline && <Notice tone="warning">当前离线：新增记录会进入安全待同步队列；编辑和删除不可用。</Notice>}
          <Card>
            {kind === 'food' && <>
              <SectionTitle>这餐吃了什么</SectionTitle>
              <Field label="食物名称" value={name} onChangeText={setName} placeholder="例如：鸡肉饭" />
              <Text style={[styles.label, { color: theme.colors.text }]}>餐别</Text>
              <View style={styles.chips}>{meals.map((item) => <Chip key={item} label={mealLabels[item]} selected={meal === item} onPress={() => setMeal(item)} />)}</View>
              <Field label="热量（kcal）" value={energy} onChangeText={setEnergy} keyboardType="decimal-pad" placeholder="例如：520" />
              <View style={styles.twoCol}><View style={styles.col}><Field label="份量" value={portion} onChangeText={setPortion} keyboardType="decimal-pad" placeholder="可选" /></View><View style={styles.col}><Field label="单位" value={portionUnit} onChangeText={setPortionUnit} placeholder="碗 / 克" /></View></View>
              <Field label="备注" value={detail} onChangeText={setDetail} multiline placeholder="可选" />
            </>}
            {kind === 'activity' && <>
              <SectionTitle>完成了什么运动</SectionTitle>
              <Field label="运动名称" value={name} onChangeText={setName} placeholder="例如：户外跑步" />
              <View style={styles.twoCol}><View style={styles.col}><Field label="时长（分钟）" value={duration} onChangeText={setDuration} keyboardType="number-pad" /></View><View style={styles.col}><Field label="消耗（kcal）" value={energy} onChangeText={setEnergy} keyboardType="decimal-pad" /></View></View>
              <Text style={[styles.label, { color: theme.colors.text }]}>强度</Text>
              <View style={styles.chips}>{intensities.map((item) => <Chip key={item} label={intensityLabels[item]} selected={intensity === item} onPress={() => setIntensity(item)} />)}</View>
              <Field label="备注" value={detail} onChangeText={setDetail} multiline placeholder="可选" />
            </>}
            {kind === 'weight' && <>
              <SectionTitle>记录当前体重</SectionTitle>
              <Field label="体重（kg）" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" placeholder="例如：65.5" />
              <Field label="备注" value={detail} onChangeText={setDetail} multiline placeholder="例如：晨起空腹" />
            </>}
            {!!error && <Notice tone="error">{error}</Notice>}
            {isAgentCandidate && <Notice tone="info">{isImageCandidate ? '这是图片估算候选。请校正名称、份量和热量；原图不会保存。' : '这是 Agent 生成的候选。请核对并修改字段；只有点击下方按钮后才会写入。'}</Notice>}
            <Button loading={pending} disabled={isAgentCandidate && !sync.isOnline} onPress={() => void save()}>{isEditing ? '保存修改' : isAgentCandidate && resumeRequired ? '确认候选并继续' : isAgentCandidate ? '确认候选并保存' : sync.isOnline ? '确认并保存' : '确认并离线保存'}</Button>
            {isEditing && <Button variant="danger" disabled={pending} onPress={confirmDelete}>删除记录</Button>}
          </Card>
          <Text style={[styles.footnote, { color: theme.colors.textMuted }]}>热量和运动消耗可手动修正。Journey 不把估算值作为医疗结论。</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 }, flex: { flex: 1 },
  header: { minHeight: 58, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: journeySpacing.md },
  headerTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800' }, headerSpacer: { width: 72 },
  content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg, gap: journeySpacing.md },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm }, label: { fontSize: journeyTypography.small, fontWeight: '700' },
  twoCol: { flexDirection: 'row', gap: journeySpacing.sm }, col: { flex: 1 },
  footnote: { fontSize: journeyTypography.caption, lineHeight: 18, textAlign: 'center' },
});
