import { useQuery } from '@tanstack/react-query';
import { router, type Href } from 'expo-router';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { ScreenShell } from '@/components/screen-shell';
import { LOCAL_KNOWLEDGE_SAFETY_NOTICE, LOCAL_KNOWLEDGE_VERSION } from '@/content/local-knowledge';
import { formatNumber, goalLabels } from '@/lib/format';
import { useAuth } from '@/providers/auth-provider';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

const syncFieldLabels: Record<string, string> = {
  display_name: '昵称', timezone: '时区', locale: '语言', sex: '性别', birth_date: '生日',
  height_cm: '身高', preferred_unit: '单位', kind: '目标类型', target_weight_kg: '目标体重',
  daily_energy_target_kcal: '能量目标', starts_on: '开始日期', target_date: '目标日期',
  recorded_at: '记录时间', measured_at: '测量时间', meal_type: '餐别', name: '名称',
  energy_kcal: '热量', detail: '详情', portion_amount: '份量', portion_unit: '份量单位',
  duration_minutes: '时长', intensity: '强度', note: '备注', weight_kg: '体重',
  version: '版本', 删除状态: '删除状态',
};

function conflictFieldNames(fields: string[]): string {
  return fields.map((field) => syncFieldLabels[field] ?? field).join('、');
}

function conflictValue(value: unknown, missing: string): string {
  if (value == null) return missing;
  const formatted = typeof value === 'object' ? JSON.stringify(value) : String(value);
  return formatted.length > 80 ? `${formatted.slice(0, 77)}…` : formatted;
}

function conflictSide(
  record: Record<string, unknown> | null,
  field: string,
): string {
  if (field === '删除状态') return record ? '保留记录' : '删除记录';
  return conflictValue(record?.[field], record ? '未填写' : '已删除');
}

export default function ProfileScreen() {
  const theme = useJourneyTheme();
  const { session, signOut } = useAuth();
  const sync = useSync();
  const profile = useQuery({ queryKey: ['profile'], queryFn: sync.fetchProfile });
  const goal = useQuery({ queryKey: ['goal'], queryFn: sync.fetchGoal });
  const email = session?.user.identities.find((item) => item.kind === 'email')?.display_value;
  const username = session?.user.identities.find((item) => item.kind === 'username')?.display_value;

  return (
    <ScreenShell eyebrow="JOURNEY / 我的" title={profile.data?.display_name || '我的空间'}>
      {!sync.isOnline && <Notice tone="info">当前读取本机加密副本；画像、目标和记录修改会在联网后同步。</Notice>}
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
            <Button variant="secondary" onPress={() => router.push('/settings/profile')}>编辑画像</Button>
          </Card>
          <Card>
            <SectionTitle>当前目标</SectionTitle>
            <Text style={[styles.account, { color: theme.colors.text }]}>{goal.data ? goalLabels[goal.data.kind] : '还没有设置目标'}</Text>
            {goal.data && <Text style={[styles.meta, { color: theme.colors.textMuted }]}>目标体重 {goal.data.target_weight_kg == null ? '未设置' : `${formatNumber(goal.data.target_weight_kg, 1)} kg`} · 每日能量 {goal.data.daily_energy_target_kcal ?? '未设置'} kcal</Text>}
            <Button variant="secondary" onPress={() => router.push('/settings/goal')}>{goal.data ? '调整目标' : '设置目标'}</Button>
          </Card>
          <Card>
            <SectionTitle>同步与离线</SectionTitle>
            <Info label="网络" value={sync.isOnline ? '在线' : '离线'} />
            <Info label="待同步" value={`${sync.pendingCount} 条`} />
            <Info label="待处理冲突" value={`${sync.conflicts.length} 条`} />
            {sync.pendingCount > 0 && <Button variant="secondary" disabled={!sync.isOnline} loading={sync.status === 'syncing'} onPress={() => void sync.retryPending()}>立即重试同步</Button>}
            {sync.conflicts.map((conflict) => <View key={conflict.id} style={styles.conflict}>
              <Text style={[styles.account, { color: theme.colors.text }]}>有一项需要你选择</Text>
              <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{conflict.entity} 的这些字段在本机与云端不同：{conflictFieldNames(conflict.fields)}</Text>
              {conflict.fields.map((field) => <View key={field} style={[styles.conflictField, { borderColor: theme.colors.border }]}>
                <Text style={[styles.conflictLabel, { color: theme.colors.text }]}>{syncFieldLabels[field] ?? field}</Text>
                <Text style={[styles.meta, { color: theme.colors.textMuted }]}>本机：{conflictSide(conflict.local, field)}</Text>
                <Text style={[styles.meta, { color: theme.colors.textMuted }]}>云端：{conflictSide(conflict.server, field)}</Text>
              </View>)}
              <View style={styles.conflictActions}><Button variant="secondary" onPress={() => void sync.resolveConflict(conflict.id, 'server')}>使用云端</Button><Button onPress={() => void sync.resolveConflict(conflict.id, 'local')}>保留本机</Button></View>
            </View>)}
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>本地常识包 v{LOCAL_KNOWLEDGE_VERSION}：蛋白质与恢复、补水、睡眠。可在首页离线查询。</Text>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>{LOCAL_KNOWLEDGE_SAFETY_NOTICE}</Text>
          </Card>
          <Card>
            <SectionTitle>隐私与边界</SectionTitle>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>令牌和每账户副本密钥保存在系统安全存储；健康副本加密且退出即清除。图片、语音和视频不会被静默上传。</Text>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>Journey 提供一般健身、营养和生活方式管理，不诊断疾病、不开处方。</Text>
          </Card>
          <Card>
            <SectionTitle>生活灵感</SectionTitle>
            <Text style={[styles.meta, { color: theme.colors.textMuted }]}>主动保存公开分享链接，只作为生活灵感；不绑定账号、不后台抓取、不作为健康证据。</Text>
            <Button variant="secondary" onPress={() => router.push('/inspirations' as Href)}>管理生活灵感</Button>
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
  conflict: { gap: journeySpacing.sm, paddingTop: journeySpacing.sm }, conflictActions: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  conflictField: { borderWidth: 1, borderRadius: 10, padding: journeySpacing.sm, gap: 2 }, conflictLabel: { fontSize: journeyTypography.small, fontWeight: '800' },
});
