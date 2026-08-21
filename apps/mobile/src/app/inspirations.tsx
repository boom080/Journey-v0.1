import { useQuery } from '@tanstack/react-query';
import { Linking, StyleSheet, Text, View } from 'react-native';
import { useState } from 'react';

import type { InspirationPreview } from '@journey/contracts';
import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { ScreenShell } from '@/components/screen-shell';
import { Button, Card, Chip, EmptyState, Field, LoadingState, Notice, SectionTitle } from '@/components/ui';
import {
  ApiError,
  ApiNetworkError,
  createInspiration,
  deleteInspiration,
  listInspirations,
  previewInspiration,
} from '@/lib/api';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

function errorMessage(error: unknown): string {
  if (error instanceof ApiError || error instanceof ApiNetworkError) return error.message;
  return '这次没有完成，请稍后再试。';
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date(value));
}

export default function InspirationsScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const inspirations = useQuery({
    queryKey: ['inspirations'],
    queryFn: listInspirations,
    enabled: sync.isOnline,
  });
  const [sourceUrl, setSourceUrl] = useState('');
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [tags, setTags] = useState('');
  const [preview, setPreview] = useState<InspirationPreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState<'preview' | 'save' | 'delete' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const resetDraft = () => {
    setSourceUrl(''); setTitle(''); setSummary(''); setTags('');
    setPreview(null); setConfirmed(false);
  };

  const handlePreview = async () => {
    if (!sync.isOnline) {
      setError('预览公开链接需要联网；当前不会在后台自动重试。');
      return;
    }
    if (!sourceUrl.trim()) {
      setError('请粘贴你主动分享的公开链接。');
      return;
    }
    setBusy('preview'); setError(null); setSavedMessage(null); setConfirmed(false);
    try {
      const result = await previewInspiration({ source_url: sourceUrl.trim() });
      setPreview(result);
      setSourceUrl(result.source_url);
      setTitle(result.title ?? '');
      setSummary(result.summary ?? '');
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(null);
    }
  };

  const handleSave = async () => {
    if (!preview || !confirmed || !title.trim() || !sync.isOnline) return;
    setBusy('save'); setError(null); setSavedMessage(null);
    try {
      await createInspiration({
        source_url: preview.source_url,
        title: title.trim(),
        summary: summary.trim() || null,
        tags: tags.split(/[,，]/).map((item) => item.trim()).filter(Boolean).slice(0, 5),
        source_checked_at: preview.source_checked_at,
        confirmed: true,
      });
      await inspirations.refetch();
      resetDraft();
      setSavedMessage('已保存为生活灵感；不会自动进入健康建议或知识库。');
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async (id: string) => {
    setBusy('delete'); setError(null);
    try {
      await deleteInspiration(id);
      setDeleteConfirmId(null);
      await inspirations.refetch();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(null);
    }
  };

  return (
    <ScreenShell eyebrow="JOURNEY / 生活灵感" title="把喜欢的想法带回来">
      <Notice tone="info">只接受你逐次主动分享的公开链接。不绑定账号、不读取 Cookie、不后台抓取。</Notice>
      {!sync.isOnline && <Notice tone="warning">当前离线：可以保留剪贴板里的链接，但预览和保存需要联网。</Notice>}
      {!!error && <Notice tone="error">{error}</Notice>}
      {!!savedMessage && <Notice tone="success">{savedMessage}</Notice>}

      <Card>
        <SectionTitle>导入一条公开链接</SectionTitle>
        <Field
          label="公开分享链接"
          value={sourceUrl}
          onChangeText={(value) => { setSourceUrl(value); setPreview(null); setConfirmed(false); }}
          placeholder="https://www.xiaohongshu.com/..."
          autoCapitalize="none"
          autoCorrect={false}
          hint="仅支持当前白名单中的小红书公开 HTTPS 链接。"
        />
        <Button
          accessibilityLabel="预览公开链接"
          disabled={!sync.isOnline || !sourceUrl.trim()}
          loading={busy === 'preview'}
          onPress={() => void handlePreview()}
        >预览公开链接</Button>
      </Card>

      {preview && <Card>
        <SectionTitle>{preview.status === 'preview' ? '确认公开信息' : '改为手动填写'}</SectionTitle>
        <Notice tone={preview.status === 'preview' ? 'info' : 'warning'}>{preview.message}</Notice>
        <Field label="标题" value={title} onChangeText={setTitle} maxLength={160} placeholder="例如：周末轻徒步路线" />
        <Field
          label="短摘要（可选）"
          value={summary}
          onChangeText={setSummary}
          maxLength={500}
          multiline
          placeholder="用自己的话记录为什么想保存"
          hint="页面内容不发送给模型；建议删掉个人信息和未经核验的健康结论。"
        />
        <Field label="标签（可选）" value={tags} onChangeText={setTags} placeholder="周末，户外，朋友" hint="最多 5 个，用逗号分隔。" />
        <Notice tone="warning">生活灵感 · 非健康证据。不会进入营养数值、健康风险或医疗结论。</Notice>
        <Chip
          label={confirmed ? '✓ 已确认由我主动保存' : '我确认由自己主动保存'}
          selected={confirmed}
          onPress={() => setConfirmed((value) => !value)}
        />
        <Button
          accessibilityLabel="确认保存生活灵感"
          disabled={!confirmed || !title.trim() || !sync.isOnline}
          loading={busy === 'save'}
          onPress={() => void handleSave()}
        >确认保存生活灵感</Button>
      </Card>}

      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>已保存</Text>
        <Text style={[styles.meta, { color: theme.colors.textMuted }]}>仅你当前账号可见</Text>
      </View>
      {inspirations.isLoading && sync.isOnline ? <LoadingState label="正在读取生活灵感…" /> : null}
      {!inspirations.isLoading && !(inspirations.data?.items.length) ? (
        <EmptyState title="还没有生活灵感" message="从一条你主动分享的公开链接开始；无法读取时也可以手动填写。" />
      ) : inspirations.data?.items.map((item) => (
        <Card key={item.id}>
          <SectionTitle>{item.title}</SectionTitle>
          {!!item.summary && <Text style={[styles.body, { color: theme.colors.text }]}>{item.summary}</Text>}
          <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{item.source_name} · {formatDate(item.source_checked_at)} · 生活灵感/非健康证据</Text>
          {!!item.tags.length && <Text style={[styles.meta, { color: theme.colors.primaryStrong }]}>#{item.tags.join('  #')}</Text>}
          <Button variant="secondary" accessibilityLabel={`打开来源 ${item.title}`} onPress={() => void Linking.openURL(item.source_url)}>打开原链接</Button>
          {deleteConfirmId === item.id ? <View style={styles.actions}>
            <Button variant="ghost" onPress={() => setDeleteConfirmId(null)}>取消</Button>
            <Button variant="danger" accessibilityLabel={`确认删除 ${item.title}`} loading={busy === 'delete'} onPress={() => void handleDelete(item.id)}>确认删除</Button>
          </View> : <Button variant="ghost" accessibilityLabel={`删除 ${item.title}`} onPress={() => setDeleteConfirmId(item.id)}>删除</Button>}
        </Card>
      ))}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: journeySpacing.md },
  sectionTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  body: { fontSize: journeyTypography.body, lineHeight: 24 },
  meta: { fontSize: journeyTypography.small, lineHeight: 21 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
});
