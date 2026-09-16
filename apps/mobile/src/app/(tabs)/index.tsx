import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router, type Href, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { journeySpacing, journeyTypography } from '@journey/design-tokens';
import type { AgentCandidate, AgentConfirmationRequest, AgentRunResponse, MealType } from '@journey/contracts';

import { AgentStatusStrip, WarmHomeHero, WarmHomeMetrics, warmHomeColors } from '@/components/home-overview';
import { ScreenShell } from '@/components/screen-shell';
import { Button, Card, Chip, EmptyState, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { isFoodImageAnalysisEnabled } from '@/config/environment';
import {
  ApiError,
  confirmAgentCandidate,
  fetchAgentPrivacy,
  fetchAgentRunTrace,
  getAgentErrorMessage,
  resumeAgentRun,
  runAgent,
  subscribeToAgentDataDeleted,
} from '@/lib/api';
import { formatNumber, intensityLabels, mealLabels } from '@/lib/format';
import { classifyMockInput, type MockCandidate } from '@/lib/mock-intent';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

function candidateParams(candidate: Exclude<MockCandidate, { kind: 'knowledge' }>) {
  if (candidate.kind === 'food') return { kind: 'food', name: candidate.title, energy: String(candidate.energyKcal), meal: candidate.mealType };
  if (candidate.kind === 'activity') return { kind: 'activity', name: candidate.title, energy: String(candidate.energyKcal), duration: String(candidate.durationMinutes), intensity: candidate.intensity };
  return { kind: 'weight', weight: String(candidate.weightKg) };
}

function agentConfirmationRequest(candidate: AgentCandidate): AgentConfirmationRequest {
  return {
    confirmation_token: candidate.confirmation_token,
    kind: candidate.kind,
    payload: candidate.payload,
  } as AgentConfirmationRequest;
}

function agentCandidateDetail(candidate: AgentCandidate): string {
  if (candidate.kind === 'food') {
    const amount = candidate.payload.portion_amount ?? 1;
    const unit = candidate.payload.portion_unit ?? '份';
    return `${formatNumber(amount, 1)} ${unit} · 约 ${formatNumber(candidate.payload.energy_kcal)} kcal`;
  }
  if (candidate.kind === 'activity') {
    return `${candidate.payload.duration_minutes} 分钟 · ${intensityLabels[candidate.payload.intensity]} · 约 ${formatNumber(candidate.payload.energy_kcal)} kcal`;
  }
  return `${formatNumber(candidate.payload.weight_kg, 1)} kg`;
}

const mealOptions: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack', 'other'];

function runStatus(status: string | null, fallback: AgentRunResponse['status']): AgentRunResponse['status'] {
  return status === 'completed' || status === 'degraded' ||
    status === 'clarification_required' || status === 'waiting_for_user'
    ? status
    : fallback;
}

function isAgentPrivacyError(error: unknown): error is ApiError {
  return error instanceof ApiError && ['consent_required', 'consent_outdated', 'agent_external_disabled', 'agent_provider_review_required'].includes(error.code);
}

export default function HomeScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const queryClient = useQueryClient();
  const [input, setInput] = useState('');
  const [candidate, setCandidate] = useState<MockCandidate | null>(null);
  const [agentResult, setAgentResult] = useState<AgentRunResponse | null>(null);
  const [agentThreadId, setAgentThreadId] = useState<string>();
  const [agentPending, setAgentPending] = useState(false);
  const [agentError, setAgentError] = useState('');
  const [agentMessage, setAgentMessage] = useState('');
  const [openMealCandidateId, setOpenMealCandidateId] = useState<string>();
  const [resumeRunId, setResumeRunId] = useState<string>();
  const agentPrivacyChecked = useRef(false);
  const agentMemoryVersion = useRef(0);
  const home = useQuery({ queryKey: ['home'], queryFn: sync.fetchHome });

  useEffect(() => subscribeToAgentDataDeleted(() => {
    queryClient.removeQueries({
      predicate: (query) => {
        const [root] = query.queryKey;
        return typeof root === 'string' && root.startsWith('agent');
      },
    });
    agentMemoryVersion.current += 1;
    setCandidate(null);
    setAgentResult(null);
    setAgentThreadId(undefined);
    setResumeRunId(undefined);
    setAgentError('');
    setAgentMessage('');
    setOpenMealCandidateId(undefined);
    agentPrivacyChecked.current = false;
  }), [queryClient]);

  useFocusEffect(useCallback(() => {
    const continuation = queryClient.getQueryData<AgentRunResponse>(['agent-continuation']);
    if (continuation) {
      setAgentResult(continuation);
      queryClient.removeQueries({ queryKey: ['agent-continuation'], exact: true });
    }
    const confirmationUpdate = queryClient.getQueryData<{
      runId: string;
      candidateId: string;
      progress: AgentRunResponse['confirmation_progress'];
      runStatus?: string | null;
    }>(['agent-confirmation-update']);
    if (confirmationUpdate) {
      setAgentResult((current) => current?.run_id === confirmationUpdate.runId ? {
        ...current,
        candidates: current.candidates.filter(
          (item) => item.candidate_id !== confirmationUpdate.candidateId,
        ),
        confirmation_progress: confirmationUpdate.progress,
        status: runStatus(confirmationUpdate.runStatus ?? null, current.status),
      } : current);
      queryClient.removeQueries({ queryKey: ['agent-confirmation-update'], exact: true });
    }
    setResumeRunId(queryClient.getQueryData<string>(['agent-resume-needed']));
  }, [queryClient]));

  async function continueRun() {
    if (!resumeRunId) return;
    const memoryVersion = agentMemoryVersion.current;
    setAgentPending(true); setAgentError('');
    try {
      const continuation = await resumeAgentRun(resumeRunId);
      if (memoryVersion !== agentMemoryVersion.current) return;
      setAgentResult(continuation);
      queryClient.removeQueries({ queryKey: ['agent-resume-needed'], exact: true });
      setResumeRunId(undefined);
    } catch (reason) {
      if (memoryVersion !== agentMemoryVersion.current) return;
      const trace = await fetchAgentRunTrace(resumeRunId).catch(() => null);
      if (memoryVersion !== agentMemoryVersion.current) return;
      if (trace && trace.status !== 'waiting_for_user') {
        queryClient.removeQueries({ queryKey: ['agent-resume-needed'], exact: true });
        setResumeRunId(undefined);
        setAgentError('该 Run 已在后台完成。记录已同步，可到 Journey 生成最新总结。');
        await home.refetch();
      } else {
        setAgentError(getAgentErrorMessage(reason));
        if (isAgentPrivacyError(reason)) {
          agentPrivacyChecked.current = false;
          router.push('/settings/agent-privacy' as Href);
        }
      }
    } finally { setAgentPending(false); }
  }

  async function analyze() {
    const memoryVersion = agentMemoryVersion.current;
    setAgentError(''); setAgentMessage(''); setAgentResult(null); setCandidate(null); setOpenMealCandidateId(undefined);
    if (!sync.isOnline) {
      const local = classifyMockInput(input);
      if (local?.kind === 'knowledge') setCandidate(local);
      else setAgentError('离线时 Agent 不可用；可使用下方手动记录，或查询内置常识。');
      return;
    }
    setAgentPending(true);
    try {
      if (!agentPrivacyChecked.current) {
        const privacy = await fetchAgentPrivacy();
        if (!privacy.enabled) {
          setAgentError('Agent 当前已关闭，消息不会发送；请到“外部 AI 与数据”查看服务端状态。');
          router.push('/settings/agent-privacy' as Href);
          return;
        }
        if (privacy.external && !privacy.consent_granted) {
          setAgentError('使用外部 AI 前需要先明确授权，消息尚未发送。');
          router.push('/settings/agent-privacy' as Href);
          return;
        }
        if (memoryVersion !== agentMemoryVersion.current) return;
        agentPrivacyChecked.current = true;
      }
      const result = await runAgent(input.trim(), agentThreadId);
      if (memoryVersion !== agentMemoryVersion.current) return;
      setAgentThreadId(result.thread_id ?? undefined);
      setAgentResult(result);
    }
    catch (reason) {
      if (memoryVersion !== agentMemoryVersion.current) return;
      setAgentError(getAgentErrorMessage(reason));
      if (isAgentPrivacyError(reason)) {
        agentPrivacyChecked.current = false;
        router.push('/settings/agent-privacy' as Href);
      }
    }
    finally { setAgentPending(false); }
  }

  function updateInput(value: string) {
    setInput(value);
    setCandidate(null);
    setAgentResult(null);
    setAgentError('');
    setAgentMessage('');
    setOpenMealCandidateId(undefined);
  }

  function updateCandidateMeal(candidateId: string, mealType: MealType) {
    setAgentResult((current) => current ? {
      ...current,
      candidates: current.candidates.map((item) => item.candidate_id === candidateId && item.kind === 'food'
        ? { ...item, payload: { ...item.payload, meal_type: mealType } }
        : item),
    } : current);
    setOpenMealCandidateId(undefined);
  }

  async function refreshConfirmedRecords() {
    await sync.fetchJourney(7, undefined, 7);
    await queryClient.invalidateQueries({ queryKey: ['journey'] });
    await home.refetch();
  }

  async function confirmAllCandidates() {
    if (!agentResult?.candidates.length || agentPending || !sync.isOnline) return;
    const memoryVersion = agentMemoryVersion.current;
    const candidates = [...agentResult.candidates];
    let confirmed = 0;
    let finalRunStatus: string | null = agentResult.status;
    let resumeAvailable = false;
    let continuationPending = false;
    setAgentPending(true); setAgentError(''); setAgentMessage('');
    try {
      for (const item of candidates) {
        const confirmation = await confirmAgentCandidate(
          item.candidate_id,
          agentConfirmationRequest(item),
          `agent-${item.candidate_id}`,
        );
        if (memoryVersion !== agentMemoryVersion.current) return;
        confirmed += 1;
        setOpenMealCandidateId((current) => current === item.candidate_id ? undefined : current);
        finalRunStatus = confirmation.run_status;
        resumeAvailable = confirmation.resume_available;
        setAgentResult((current) => current ? {
          ...current,
          candidates: current.candidates.filter(
            (candidateItem) => candidateItem.candidate_id !== item.candidate_id,
          ),
          confirmation_progress: confirmation.confirmation_progress,
          status: runStatus(confirmation.run_status, current.status),
        } : current);
      }
      if (resumeAvailable) {
        try {
          const continuation = await resumeAgentRun(agentResult.run_id);
          if (memoryVersion !== agentMemoryVersion.current) return;
          setAgentResult(continuation);
        } catch {
          if (memoryVersion !== agentMemoryVersion.current) return;
          const trace = await fetchAgentRunTrace(agentResult.run_id).catch(() => null);
          if (memoryVersion !== agentMemoryVersion.current) return;
          if (trace && trace.status !== 'waiting_for_user') {
            setAgentResult(null);
          } else {
            continuationPending = true;
            setResumeRunId(agentResult.run_id);
            queryClient.setQueryData(['agent-resume-needed'], agentResult.run_id);
          }
        }
      } else if (runStatus(finalRunStatus, agentResult.status) === 'completed') {
        setAgentResult(null);
      }
      try {
        await refreshConfirmedRecords();
      } catch {
        if (memoryVersion !== agentMemoryVersion.current) return;
        setInput('');
        setAgentMessage(`已记录 ${confirmed} 条；首页自动刷新失败时可点“刷新”。需要调整时可到 Journey 中编辑。`);
        return;
      }
      if (memoryVersion !== agentMemoryVersion.current) return;
      setInput('');
      setAgentMessage(continuationPending
        ? `已记录 ${confirmed} 条，今天的变化已更新；后续总结可点击“继续执行”。`
        : `已记录 ${confirmed} 条，今天的变化已更新。需要调整时可到 Journey 中编辑。`);
    } catch (reason) {
      if (memoryVersion !== agentMemoryVersion.current) return;
      if (confirmed > 0) await refreshConfirmedRecords().catch(() => undefined);
      setAgentError(confirmed > 0
        ? `已记录 ${confirmed}/${candidates.length} 条；剩余记录尚未保存，请再次点击确认。`
        : getAgentErrorMessage(reason));
    } finally {
      if (memoryVersion === agentMemoryVersion.current) setAgentPending(false);
    }
  }

  return (
    <ScreenShell
      backgroundColor={warmHomeColors.background}
      hero={(
        <WarmHomeHero
          date={home.data?.date}
          imageEnabled={isFoodImageAnalysisEnabled()}
          input={input}
          isAnalyzing={agentPending}
          isOnline={sync.isOnline}
          onAnalyze={() => void analyze()}
          onImagePress={() => router.push('/food-image')}
          onInputChange={updateInput}
        />
      )}>
      {!!resumeRunId && <View style={styles.resumeBlock}><Notice tone="info">候选已保存，但 Agent 后续步骤尚未执行。</Notice><Button variant="secondary" loading={agentPending} onPress={() => void continueRun()}>继续执行</Button></View>}
      {sync.pendingCount > 0 && <Notice tone={sync.status === 'error' ? 'error' : 'info'}>{sync.pendingCount} 条记录等待同步。{sync.isOnline ? '正在尝试上传。' : '联网后将自动上传。'}</Notice>}
      {!!agentError && <Notice tone="error">{agentError}</Notice>}
      {!!agentMessage && <Notice tone="success">{agentMessage}</Notice>}

      {agentResult && (
        <Card>
          <SectionTitle>处理结果</SectionTitle>
          {agentResult.status === 'waiting_for_user' && agentResult.candidates.length > 0 && <Notice tone="info">已按常见情况补全默认值。核对后一次确认即可写入全部记录。</Notice>}
          {!!agentResult.answer && <Text style={[styles.copy, { color: theme.colors.text }]}>{agentResult.answer}</Text>}
          {agentResult.candidates.map((item) => <View key={item.candidate_id} style={styles.resultBlock}>
            <Text style={[styles.candidateTitle, { color: theme.colors.text }]}>{item.kind === 'food' ? item.payload.name : item.kind === 'activity' ? item.payload.name : `${item.payload.weight_kg} kg`}</Text>
            {item.kind === 'food' ? <>
              <View style={styles.candidateDetailRow}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`餐别：${mealLabels[item.payload.meal_type]}，点击修改`}
                  onPress={() => setOpenMealCandidateId((current) => current === item.candidate_id ? undefined : item.candidate_id)}
                  style={({ pressed }) => [styles.inlineSelect, {
                    backgroundColor: theme.colors.background,
                    borderColor: theme.colors.border,
                    opacity: pressed ? 0.72 : 1,
                  }]}
                >
                  <Text style={[styles.inlineSelectText, { color: theme.colors.primaryStrong }]}>{mealLabels[item.payload.meal_type]}⌄</Text>
                </Pressable>
                <Text style={[styles.candidateDetail, { color: theme.colors.text }]}>· {agentCandidateDetail(item)}</Text>
              </View>
              {openMealCandidateId === item.candidate_id && <View accessibilityLabel="选择餐别" style={styles.inlineOptions}>
                {mealOptions.map((meal) => <Chip
                  key={meal}
                  label={mealLabels[meal]}
                  selected={meal === item.payload.meal_type}
                  onPress={() => updateCandidateMeal(item.candidate_id, meal)}
                />)}
              </View>}
            </> : <Text style={[styles.candidateDetail, { color: theme.colors.text }]}>{agentCandidateDetail(item)}</Text>}
          </View>)}
          {agentResult.candidates.length > 0 && <>
            <Button loading={agentPending} disabled={!sync.isOnline} onPress={() => void confirmAllCandidates()}>确认并记录 {agentResult.candidates.length} 条</Button>
            <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>确认后立即更新“今天的变化”；如需调整，可到 Journey 打开记录编辑。</Text>
          </>}
          {agentResult.citations.map((citation) => <View key={citation.chunk_id} style={styles.citation}>
            <Text style={[styles.citationTitle, { color: theme.colors.text }]}>{citation.title} · v{citation.version}</Text>
            <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{citation.excerpt}</Text>
          </View>)}
          {agentResult.fallback_used && <Notice tone="info">这是估算结果，请结合实际情况判断。</Notice>}
          <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{agentResult.safety_notice}</Text>
          <Button variant="ghost" onPress={() => setAgentResult(null)}>关闭结果</Button>
        </Card>
      )}

      {candidate && (
        <Card>
          <SectionTitle>{candidate.kind === 'knowledge' ? candidate.title : '请确认候选'}</SectionTitle>
          {candidate.kind === 'knowledge' ? (
            <Text style={[styles.copy, { color: theme.colors.text }]}>{candidate.answer}</Text>
          ) : (
            <>
              <Text style={[styles.candidateTitle, { color: theme.colors.text }]}>{candidate.kind === 'weight' ? `${candidate.weightKg} kg` : candidate.title}</Text>
              <Button onPress={() => router.push({ pathname: '/record/[kind]', params: candidateParams(candidate) })}>打开表单确认</Button>
            </>
          )}
          <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{candidate.explanation}</Text>
          <Button variant="ghost" onPress={() => setCandidate(null)}>放弃候选</Button>
        </Card>
      )}

      {home.isLoading ? <LoadingState label="正在同步今日数据…" /> : home.isError ? (
        <EmptyState title="今天还没有记录" message="先从下方记下一条，今天的变化就会更新。" />
      ) : home.data ? (
        <>
          <WarmHomeMetrics data={home.data} onRefresh={() => void home.refetch()} />
          {home.data.counts.food + home.data.counts.activity + home.data.counts.weight === 0 && <EmptyState title="今天还没有记录" message="随手记下一条，今天的变化就会跟着更新。" />}
        </>
      ) : null}
      <AgentStatusStrip
        hasError={Boolean(agentError)}
        isOnline={sync.isOnline}
        isPending={agentPending}
        resultStatus={agentResult?.status}
        resumeRequired={Boolean(resumeRunId)}
      />
      <SectionTitle>快速手动记录</SectionTitle>
      <View style={styles.quickRow}>
        <View style={styles.quick}><Button variant="secondary" onPress={() => router.push('/record/food')}>＋ 饮食</Button></View>
        <View style={styles.quick}><Button variant="secondary" onPress={() => router.push('/record/activity')}>＋ 运动</Button></View>
        <View style={styles.quick}><Button variant="secondary" onPress={() => router.push('/record/weight')}>＋ 体重</Button></View>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  copy: { fontSize: journeyTypography.small, lineHeight: 22 },
  candidateTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  candidateDetail: { fontSize: journeyTypography.body, lineHeight: 24, fontWeight: '700' },
  candidateDetailRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: journeySpacing.xs },
  inlineSelect: { minHeight: 34, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6, justifyContent: 'center' },
  inlineSelectText: { fontSize: journeyTypography.small, fontWeight: '800' },
  inlineOptions: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.xs },
  explanation: { fontSize: journeyTypography.caption, lineHeight: 18 },
  resultBlock: { gap: journeySpacing.sm, paddingVertical: journeySpacing.sm },
  citation: { gap: journeySpacing.xs, borderTopWidth: 1, borderTopColor: '#D7EBE1', paddingTop: journeySpacing.sm },
  citationTitle: { fontSize: journeyTypography.small, fontWeight: '800' },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  quick: { flexGrow: 1, minWidth: 96 },
  resumeBlock: { gap: journeySpacing.sm },
});
