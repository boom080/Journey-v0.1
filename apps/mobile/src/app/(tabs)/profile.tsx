import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { ScreenShell } from '@/components/screen-shell';
import { LOCAL_KNOWLEDGE_SAFETY_NOTICE, LOCAL_KNOWLEDGE_VERSION } from '@/content/local-knowledge';
import { ApiError, fetchGoal, fetchProfile } from '@/lib/api';
import { formatNumber, goalLabels } from '@/lib/format';
import { useAuth } from '@/providers/auth-provider';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

export default function ProfileScreen() {
  const theme = useJourneyTheme();
  const { session, signOut } = useAuth();
  const sync = useSync();
  const profile = useQuery({ queryKey: ['profile'], queryFn: fetchProfile });
  const goal = useQuery({ queryKey: ['goal'], queryFn: async () => {
    try { return await fetchGoal(); } catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error; }
  }});
  const email = session?.user.identities.find((item) => item.kind === 'email')?.display_value;
  const username = session?.user.identities.find((item) => item.kind === 'username')?.display_value;

  return (
    <ScreenShell eyebrow="JOURNEY / 我的" title={profile.data?.display_name || '我的空间'}>
      {!sync.isOnline && <Notice tone="warning">当前离线：画像、目标、账号操作需要联网；本地常识仍可使用。</Notice>}
      {profile.isLoading ? <LoadingState label="正在读取画像…" /> : (
        <>
          <Card style={{ backgroundColor: theme.colors.hero }}>
            <SectionTitle>账号</SectionTitle>
            <Text style={[styles.account, { color: theme.colors.text }]}>{email ?? '未设置邮箱'}</Text>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>@{username ?? 'unknown'} · {session?.user.status === 'active' ? '账号正常' : '账号受限'}</Text>
            {Platform.OS === 'web' && <Notice tone="warning">Web 仅作补充形态，令牌只保存在当前标签页会话中。</Notice>}
          </Card>
          <Card>
            <SectionTitle>画像与单位</SectionTitle>
            <View style={styles.rows}>
              <Info label="性别" value={profile.data?.sex ? ({ female: '女性', male: '男性', other: '其他', undisclosed: '不透露' } as const)[profile.data.sex] : '未填写'} />
              <Info label="身高" value={profile.data?.height_cm ? `${formatNumber(profile.data.height_cm, 1)} cm` : '未填写'} />
              <Info label="最新体重" value={profile.data?.latest_weight_kg ? `${formatNumber(profile.data.latest_weight_kg, 1)} kg` : '未记录'} />
              <Info label="单位" value={profile.data?.preferred_unit === 'imperial' ? '英制' : '公制'} />
            </View>
            <Button variant="secondary" disabled={!sync.isOnline} onPress={() => router.push('/settings/profile')}>编辑画像</Button>
          </Card>
          <Card>
            <SectionTitle>当前目标</SectionTitle>
            <Text style={[styles.account, { color: theme.colors.text }]}>{goal.data ? goalLabels[goal.data.kind] : '还没有设置目标'}</Text>
            {goal.data && <Text style={[styles.meta, { color: theme.colors.textMuted }]}>目标体重 {goal.data.target_weight_kg == null ? '未设置' : `${formatNumber(goal.data.target_weight_kg, 1)} kg`} · 每日能量 {goal.data.daily_energy_target_kcal ?? '未设置'} kcal</Text>}
            <Button variant="secondary" disabled={!sync.isOnline} onPress={() => router.push('/settings/goal')}>{goal.data ? '调整目标' : '设置目标'}</Button>
          </Card>
          <Card>
            <SectionTitle>同步与离线</SectionTitle>
            <Info label="网络" value={sync.isOnline ? '在线' : '离线'} />
            <Info label="待同步" value={`${sync.pendingCount} 条`} />
            {sync.pendingCount > 0 && <Button variant="secondary" disabled={!sync.isOnline} loading={sync.status === 'syncing'} onPress={() => void sync.retryPending()}>立即重试同步</Button>}
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>本地常识包 v{LOCAL_KNOWLEDGE_VERSION}：蛋白质与恢复、补水、睡眠。可在首页离线查询。</Text>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{LOCAL_KNOWLEDGE_SAFETY_NOTICE}</Text>
          </Card>
          <Card>
            <SectionTitle>隐私与边界</SectionTitle>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>令牌保存在系统安全存储；普通缓存不保存密码。图片、语音和视频尚未接入，也不会被静默上传。</Text>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>Journey 提供一般健身、营养和生活方式管理，不诊断疾病、不开处方。</Text>
          </Card>
          <Button variant="danger" onPress={() => void signOut()}>退出登录</Button>
        </>
      )}
    </ScreenShell>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  const theme = useJourneyTheme();
  return <View style={styles.info}><Text style={[styles.meta, { color: theme.colors.textMuted }]}>{label}</Text><Text style={[styles.infoValue, { color: theme.colors.text }]}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  account: { fontSize: journeyTypography.subtitle, fontWeight: '800' }, meta: { fontSize: journeyTypography.small, lineHeight: 22 },
  rows: { gap: journeySpacing.sm }, info: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: journeySpacing.md }, infoValue: { fontSize: journeyTypography.body, fontWeight: '700', textAlign: 'right' },
});
