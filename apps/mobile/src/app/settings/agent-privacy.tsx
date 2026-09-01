import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Linking, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { AgentPrivacyStatus } from '@journey/contracts';
import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, LoadingState, Notice, SectionTitle } from '@/components/ui';
import {
  deleteAgentData,
  fetchAgentPrivacy,
  getAgentErrorMessage,
  notifyAgentDataDeleted,
  updateAgentConsent,
} from '@/lib/api';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

type ConfirmAction = 'revoke' | 'delete' | null;
type BusyAction = 'consent' | 'delete' | null;

function grantedAtLabel(value: string | null): string {
  if (!value) return '未授权';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function statusLabel(status: AgentPrivacyStatus): string {
  if (!status.enabled) return '服务端已关闭';
  if (status.external) return status.consent_granted ? '已授权，可使用' : '未授权';
  return 'Journey 内置服务';
}

function clearAgentRunCache(queryClient: ReturnType<typeof useQueryClient>): void {
  queryClient.removeQueries({
    predicate: (query) => {
      const [root] = query.queryKey;
      return typeof root === 'string' && root.startsWith('agent') && root !== 'agent-privacy';
    },
  });
}

export default function AgentPrivacySettingsScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const queryClient = useQueryClient();
  const privacy = useQuery({
    queryKey: ['agent-privacy'],
    queryFn: fetchAgentPrivacy,
    enabled: sync.isOnline,
  });
  const [selectedPolicyVersion, setSelectedPolicyVersion] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<{
    action: Exclude<ConfirmAction, null>;
    policyVersion: string;
  } | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const status = privacy.data;
  // Choices belong to the exact version the user read. A refresh cannot
  // carry a previous choice into a different policy, even for one render.
  const consentSelected = !!status && selectedPolicyVersion === status.policy_version;
  const confirmAction = pendingConfirmation?.policyVersion === status?.policy_version
    ? pendingConfirmation?.action : null;

  function setConfirmAction(action: ConfirmAction) {
    setPendingConfirmation(action && status ? { action, policyVersion: status.policy_version } : null);
  }

  async function grantConsent() {
    if (!sync.isOnline || !status || !consentSelected || busy) return;
    setBusy('consent'); setError(null); setMessage(null);
    try {
      const updated = await updateAgentConsent({ granted: true, policy_version: status.policy_version });
      if (!updated.consent_granted) throw new Error('服务端没有确认授权，消息尚未发送。');
      queryClient.setQueryData(['agent-privacy'], updated);
      setSelectedPolicyVersion(null);
      setMessage('已在服务端记录授权。之后发送给外部 AI 的范围和保留期限以本页为准。');
    } catch (reason) {
      setError(getAgentErrorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  async function revokeConsent() {
    if (!sync.isOnline || !status || busy) return;
    setBusy('consent'); setError(null); setMessage(null);
    try {
      const updated = await updateAgentConsent({ granted: false, policy_version: status.policy_version });
      if (updated.consent_granted) throw new Error('服务端没有确认撤回授权。');
      queryClient.setQueryData(['agent-privacy'], updated);
      setConfirmAction(null);
      setSelectedPolicyVersion(null);
      setMessage('已撤回外部 AI 授权。之后不会向外部 AI 发送新消息。');
    } catch (reason) {
      setError(getAgentErrorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  async function deleteData() {
    if (!sync.isOnline || !status || busy) return;
    setBusy('delete'); setError(null); setMessage(null);
    try {
      const result = await deleteAgentData();
      if (result.consent_revoked !== true) throw new Error('服务端没有确认删除和撤回授权。');
      // The endpoint response is the source of truth. Only now clear mounted
      // Home state and in-memory Agent run caches; no local storage is touched.
      clearAgentRunCache(queryClient);
      notifyAgentDataDeleted();
      queryClient.setQueryData<AgentPrivacyStatus>(['agent-privacy'], {
        ...status,
        consent_granted: false,
        granted_at: null,
      });
      setConfirmAction(null);
      setSelectedPolicyVersion(null);
      setMessage(`已删除 Journey 侧 ${result.deleted_runs} 个 Run、${result.deleted_threads} 个线程，并撤回授权。${result.message}`);
    } catch (reason) {
      setError(getAgentErrorMessage(reason));
    } finally {
      setBusy(null);
    }
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}>
      <KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={[styles.header, { borderBottomColor: theme.colors.border }]}>
          <Button variant="ghost" onPress={() => router.back()}>取消</Button>
          <Text style={[styles.title, { color: theme.colors.text }]}>外部 AI 与数据</Text>
          <View style={styles.spacer} />
        </View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          <Notice tone="info">授权状态以服务端为准，本机仅临时展示，不写入离线记录或持久化存储。</Notice>
          {!sync.isOnline && <Notice tone="warning">当前离线，无法读取最新的服务端授权状态；授权、撤回和删除都不会在离线时假装成功。</Notice>}
          {sync.isOnline && privacy.isLoading && <LoadingState label="正在读取服务端隐私状态…" />}
          {sync.isOnline && privacy.isError && <Notice tone="error">{getAgentErrorMessage(privacy.error)}</Notice>}
          {sync.isOnline && status && (
            <>
              <Card>
                <SectionTitle>当前授权状态</SectionTitle>
                <View style={styles.rows}>
                  <Info label="服务商" value={status.provider || '未提供'} />
                  <Info label="服务端状态" value={statusLabel(status)} />
                  <Info label="政策版本" value={status.policy_version} />
                  <Info label="授权时间" value={grantedAtLabel(status.granted_at)} />
                </View>
                <Text style={[styles.body, { color: theme.colors.textMuted }]}>{status.notice}</Text>
                {!status.external && <Notice tone="success">当前不是外部服务商模式，Journey 内置服务不会把消息发送给第三方。</Notice>}
                {status.external && !status.enabled && <Notice tone="warning">外部 AI 当前由服务端关闭，消息不会发送。</Notice>}
                {status.external && status.enabled && !status.consent_granted && <Notice tone="warning">尚未授权。首页会在首次线上提交前拦截消息，直到你明确确认。</Notice>}
              </Card>

              <Card>
                <SectionTitle>发送范围与保留</SectionTitle>
                <Text style={[styles.body, { color: theme.colors.text }]}>发送给服务商的数据</Text>
                {status.data_sent.length ? status.data_sent.map((item) => (
                  <Text key={item} style={[styles.meta, { color: theme.colors.textMuted }]}>• {item}</Text>
                )) : <Text style={[styles.meta, { color: theme.colors.textMuted }]}>无</Text>}
                <Info label="Journey 侧保留" value={`${status.retention_days} 天`} />
                <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{status.provider_retention_notice}</Text>
                {!!status.provider_policy_url && <Button variant="secondary" onPress={() => void Linking.openURL(status.provider_policy_url!)}>查看服务商隐私政策</Button>}
              </Card>

              {status.external && status.enabled && !status.consent_granted && <Card>
                <SectionTitle>明确授权外部 AI</SectionTitle>
                <Text style={[styles.body, { color: theme.colors.textMuted }]}>请先阅读上面的发送范围、保留期限和服务商政策，再由你主动选择授权。未选择时不会自动授权，也不会上传首页消息。</Text>
                <Chip label="我已阅读发送范围和保留规则" selected={consentSelected} onPress={() => setSelectedPolicyVersion(consentSelected ? null : status.policy_version)} />
                <Button disabled={!consentSelected || !sync.isOnline} loading={busy === 'consent'} onPress={() => void grantConsent()}>授权外部 AI</Button>
              </Card>}

              {status.external && status.consent_granted && <Card>
                <SectionTitle>撤回授权</SectionTitle>
                <Text style={[styles.body, { color: theme.colors.textMuted }]}>撤回只阻止之后的新消息发送，不会自动删除已经保存的 Journey 侧 Agent 数据。</Text>
                {confirmAction === 'revoke' ? <View style={styles.actions}>
                  <Button variant="ghost" disabled={busy !== null} onPress={() => setConfirmAction(null)}>取消</Button>
                  <Button variant="danger" loading={busy === 'consent'} onPress={() => void revokeConsent()}>确认撤回授权</Button>
                </View> : <Button variant="secondary" disabled={!sync.isOnline || busy !== null} onPress={() => { setError(null); setMessage(null); setConfirmAction('revoke'); }}>撤回外部 AI 授权</Button>}
              </Card>}

              <Card>
                <SectionTitle>删除 Agent 数据</SectionTitle>
                <Text style={[styles.body, { color: theme.colors.textMuted }]}>{status.deletion_notice}</Text>
                <Text style={[styles.meta, { color: theme.colors.textMuted }]}>这不会删除健康记录、离线队列或账号；服务商侧数据是否删除以服务商政策为准。</Text>
                {confirmAction === 'delete' ? <View style={styles.actions}>
                  <Button variant="ghost" disabled={busy !== null} onPress={() => setConfirmAction(null)}>取消</Button>
                  <Button variant="danger" loading={busy === 'delete'} onPress={() => void deleteData()}>确认删除 Agent 数据</Button>
                </View> : <Button variant="danger" disabled={!sync.isOnline || busy !== null} onPress={() => { setError(null); setMessage(null); setConfirmAction('delete'); }}>删除 Agent 数据</Button>}
              </Card>
            </>
          )}
          {!!error && <Notice tone="error">{error}</Notice>}
          {!!message && <Notice tone="success">{message}</Notice>}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  const theme = useJourneyTheme();
  return <View style={styles.info}><Text style={[styles.meta, { color: theme.colors.textMuted }]}>{label}</Text><Text style={[styles.infoValue, { color: theme.colors.text }]}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  header: { minHeight: 58, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: journeySpacing.md },
  title: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  spacer: { width: 72 },
  content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg, gap: journeySpacing.md },
  rows: { gap: journeySpacing.sm },
  info: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: journeySpacing.md },
  infoValue: { fontSize: journeyTypography.body, fontWeight: '700', textAlign: 'right', flexShrink: 1 },
  body: { fontSize: journeyTypography.body, lineHeight: 24 },
  meta: { fontSize: journeyTypography.small, lineHeight: 21 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
});
