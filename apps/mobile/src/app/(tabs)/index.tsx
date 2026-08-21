import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { journeySpacing, journeyTypography } from '@journey/design-tokens';
import type { AgentCandidate, AgentRunResponse, AgentSpecialist } from '@journey/contracts';

import { AgentStatusStrip, WarmHomeHero, WarmHomeMetrics, warmHomeColors } from '@/components/home-overview';
import { ScreenShell } from '@/components/screen-shell';
import { Button, Card, EmptyState, ErrorState, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { isFoodImageAnalysisEnabled } from '@/config/environment';
import { ApiError, ApiNetworkError, fetchAgentRunTrace, resumeAgentRun, runAgent } from '@/lib/api';
import { classifyMockInput, type MockCandidate } from '@/lib/mock-intent';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

function candidateParams(candidate: Exclude<MockCandidate, { kind: 'knowledge' }>) {
  if (candidate.kind === 'food') return { kind: 'food', name: candidate.title, energy: String(candidate.energyKcal), meal: candidate.mealType };
  if (candidate.kind === 'activity') return { kind: 'activity', name: candidate.title, energy: String(candidate.energyKcal), duration: String(candidate.durationMinutes), intensity: candidate.intensity };
  return { kind: 'weight', weight: String(candidate.weightKg) };
}

function agentCandidateParams(candidate: AgentCandidate, runId: string, resumeRequired: boolean) {
  const common = { candidateId: candidate.candidate_id, confirmationToken: candidate.confirmation_token, runId, resumeRequired: resumeRequired ? 'true' : 'false' };
  if (candidate.kind === 'food') return { ...common, kind: 'food', name: candidate.payload.name, energy: String(candidate.payload.energy_kcal), meal: candidate.payload.meal_type, portion: candidate.payload.portion_amount == null ? '' : String(candidate.payload.portion_amount), portionUnit: candidate.payload.portion_unit ?? '', timestamp: candidate.payload.recorded_at };
  if (candidate.kind === 'activity') return { ...common, kind: 'activity', name: candidate.payload.name, energy: String(candidate.payload.energy_kcal), duration: String(candidate.payload.duration_minutes), intensity: candidate.payload.intensity, timestamp: candidate.payload.recorded_at };
  return { ...common, kind: 'weight', weight: String(candidate.payload.weight_kg), timestamp: candidate.payload.measured_at };
}

const specialistLabels: Record<AgentSpecialist, string> = {
  orchestrator: 'Orchestrator',
  record_agent: 'Record Agent',
  health_knowledge_agent: 'Knowledge Agent',
  journey_summary_agent: 'Summary Agent',
};

function observationDetail(summary: Record<string, unknown>): string {
  if (typeof summary.candidate_count === 'number') return `候选 ${summary.candidate_count} 条`;
  if (typeof summary.chunk_count === 'number') {
    const score = typeof summary.retrieval_score === 'number' ? ` · 最高相关度 ${summary.retrieval_score.toFixed(3)}` : '';
    return `检索 ${summary.chunk_count} 个片段${score}`;
  }
  if (typeof summary.data_range_days === 'number') return `读取近 ${summary.data_range_days} 天结构化数据`;
  if (typeof summary.citation_count === 'number') return `引用 ${summary.citation_count} 条`;
  return '结构化结果已记录';
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
  const [resumeRunId, setResumeRunId] = useState<string>();
  const home = useQuery({ queryKey: ['home'], queryFn: sync.fetchHome });

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
    }>(['agent-confirmation-update']);
    if (confirmationUpdate) {
      setAgentResult((current) => current?.run_id === confirmationUpdate.runId ? {
        ...current,
        candidates: current.candidates.filter(
          (item) => item.candidate_id !== confirmationUpdate.candidateId,
        ),
        confirmation_progress: confirmationUpdate.progress,
      } : current);
      queryClient.removeQueries({ queryKey: ['agent-confirmation-update'], exact: true });
    }
    setResumeRunId(queryClient.getQueryData<string>(['agent-resume-needed']));
  }, [queryClient]));

  async function continueRun() {
    if (!resumeRunId) return;
    setAgentPending(true); setAgentError('');
    try {
      const continuation = await resumeAgentRun(resumeRunId);
      setAgentResult(continuation);
      queryClient.removeQueries({ queryKey: ['agent-resume-needed'], exact: true });
      setResumeRunId(undefined);
    } catch (reason) {
      const trace = await fetchAgentRunTrace(resumeRunId).catch(() => null);
      if (trace && trace.status !== 'waiting_for_user') {
        queryClient.removeQueries({ queryKey: ['agent-resume-needed'], exact: true });
        setResumeRunId(undefined);
        setAgentError('该 Run 已在后台完成。记录已同步，可到 Journey 生成最新总结。');
        await home.refetch();
      } else {
        setAgentError(reason instanceof ApiError || reason instanceof ApiNetworkError ? reason.message : '继续执行失败，请稍后重试');
      }
    } finally { setAgentPending(false); }
  }

  async function analyze() {
    setAgentError(''); setAgentResult(null); setCandidate(null);
    if (!sync.isOnline) {
      const local = classifyMockInput(input);
      if (local?.kind === 'knowledge') setCandidate(local);
      else setAgentError('离线时 Agent 不可用；可使用下方手动记录，或查询内置常识。');
      return;
    }
    setAgentPending(true);
    try {
      const result = await runAgent(input.trim(), agentThreadId);
      setAgentThreadId(result.thread_id ?? undefined);
      setAgentResult(result);
    }
    catch (reason) { setAgentError(reason instanceof ApiError || reason instanceof ApiNetworkError ? reason.message : 'Agent 暂时不可用，请稍后重试'); }
    finally { setAgentPending(false); }
  }

  function updateInput(value: string) {
    setInput(value);
    setCandidate(null);
    setAgentResult(null);
    setAgentError('');
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

      {agentResult && (
        <Card>
          <SectionTitle>处理结果</SectionTitle>
          <Text style={[styles.explanation, { color: theme.colors.primaryStrong }]}>协作链路：{agentResult.selected_agents.map((item) => specialistLabels[item]).join(' → ')}</Text>
          <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>运行模式：{agentResult.usage.provider === 'mock' ? 'MOCK' : 'REAL'} · {agentResult.usage.provider}/{agentResult.usage.model}</Text>
          {agentResult.plan && (
            <View style={styles.planBlock}>
              <Text style={[styles.planTitle, { color: theme.colors.text }]}>Agent 执行计划</Text>
              {agentResult.plan.steps.map((step) => {
                const result = agentResult.step_results.find((item) => item.step_id === step.id);
                return (
                  <View key={step.id} style={styles.planRow}>
                    <Text style={[styles.planStatus, { color: theme.colors.primaryStrong }]}>
                      {result?.status === 'completed' ? '✓' : result?.status === 'awaiting_confirmation' ? '待确认' : result?.status === 'failed' ? '失败' : result?.status === 'skipped' ? '跳过' : '计划'}
                    </Text>
                    <View style={styles.planCopy}>
                      <Text style={[styles.explanation, { color: theme.colors.text }]}>{specialistLabels[result?.specialist ?? step.specialist ?? 'orchestrator']} · {step.tool}</Text>
                      <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{result?.message ?? step.reason}{result ? ` · ${result.duration_ms} ms` : ''}</Text>
                    </View>
                  </View>
                );
              })}
              {agentResult.verification && <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>校验：{agentResult.verification.reason} · 重规划 {agentResult.verification.replan_count}/2</Text>}
              {agentResult.status === 'waiting_for_user' && <Notice tone="info">Agent 已暂停。确认全部候选后，才会读取更新后的记录并继续建议。</Notice>}
              {agentResult.observations.filter((item) => item.recoverable || item.step_id.startsWith('recovery-')).map((item) => (
                <Text key={`${item.step_id}-${item.status}`} style={[styles.explanation, { color: theme.colors.textMuted }]}>
                  {item.step_id.startsWith('recovery-') ? '降级工具' : '可恢复异常'}：{item.tool} · {item.status}
                </Text>
              ))}
              {agentResult.observations.filter((item) => !item.recoverable && !item.step_id.startsWith('recovery-')).map((item) => (
                <Text key={`trace-${item.step_id}-${item.status}`} style={[styles.explanation, { color: theme.colors.textMuted }]}>Trace · {specialistLabels[item.specialist]} · {item.tool} · {observationDetail(item.output_summary)}</Text>
              ))}
              {agentResult.confirmation_progress && <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>Confirmation · 已确认 {agentResult.confirmation_progress.confirmed}/{agentResult.confirmation_progress.total} · 待确认 {agentResult.confirmation_progress.pending}</Text>}
              {!!agentThreadId && <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>当前为连续对话线程；后续输入会复用结构化摘要。</Text>}
            </View>
          )}
          {!!agentResult.answer && <Text style={[styles.copy, { color: theme.colors.text }]}>{agentResult.answer}</Text>}
          {agentResult.candidates.map((item) => <View key={item.candidate_id} style={styles.resultBlock}>
            <Text style={[styles.candidateTitle, { color: theme.colors.text }]}>{item.kind === 'food' ? item.payload.name : item.kind === 'activity' ? item.payload.name : `${item.payload.weight_kg} kg`}</Text>
            <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{item.explanation}</Text>
            <Button onPress={() => router.push({ pathname: '/record/[kind]', params: agentCandidateParams(item, agentResult.run_id, Boolean(agentResult.plan && agentResult.step_results.length < agentResult.plan.steps.length)) })}>打开并确认候选</Button>
          </View>)}
          {agentResult.citations.map((citation) => <View key={citation.chunk_id} style={styles.citation}>
            <Text style={[styles.citationTitle, { color: theme.colors.text }]}>{citation.title} · v{citation.version}</Text>
            <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>{citation.excerpt}</Text>
          </View>)}
          <Text style={[styles.explanation, { color: theme.colors.textMuted }]}>意图：{agentResult.intents.map((item) => item.intent).join('、')} · {agentResult.usage.provider}/{agentResult.usage.model} · {agentResult.usage.latency_ms} ms · ${agentResult.usage.estimated_cost_usd.toFixed(6)}</Text>
          {agentResult.fallback_used && <Notice tone="info">当前使用 Mock 或确定性降级，未调用外部模型。</Notice>}
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

      {home.isLoading ? <LoadingState label="正在同步今日数据…" /> : home.isError ? <ErrorState message="今日数据暂时不可用" onRetry={() => void home.refetch()} /> : home.data ? (
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
  explanation: { fontSize: journeyTypography.caption, lineHeight: 18 },
  resultBlock: { gap: journeySpacing.sm, paddingVertical: journeySpacing.sm },
  planBlock: { gap: journeySpacing.sm, borderBottomWidth: 1, borderBottomColor: '#D7EBE1', paddingBottom: journeySpacing.md },
  planTitle: { fontSize: journeyTypography.small, fontWeight: '900' },
  planRow: { flexDirection: 'row', gap: journeySpacing.sm, alignItems: 'flex-start' },
  planStatus: { minWidth: 42, fontSize: journeyTypography.caption, fontWeight: '900' },
  planCopy: { flex: 1, gap: 2 },
  citation: { gap: journeySpacing.xs, borderTopWidth: 1, borderTopColor: '#D7EBE1', paddingTop: journeySpacing.sm },
  citationTitle: { fontSize: journeyTypography.small, fontWeight: '800' },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  quick: { flexGrow: 1, minWidth: 96 },
  resumeBlock: { gap: journeySpacing.sm },
});
