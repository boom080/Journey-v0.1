import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { JourneyProfile } from '@journey/contracts';
import { journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, Field, LoadingState, Notice, SectionTitle } from '@/components/ui';
import { ApiError, fetchProfile, updateProfile } from '@/lib/api';
import { useJourneyTheme } from '@/theme/theme-provider';

type Sex = NonNullable<JourneyProfile['sex']>;
const sexes: { value: Sex; label: string }[] = [
  { value: 'female', label: '女性' }, { value: 'male', label: '男性' },
  { value: 'other', label: '其他' }, { value: 'undisclosed', label: '不透露' },
];

export default function ProfileSettingsScreen() {
  const theme = useJourneyTheme();
  const profile = useQuery({ queryKey: ['profile'], queryFn: fetchProfile });
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}>
      <KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Header title="编辑画像" />
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          {profile.isLoading ? <LoadingState /> : profile.data ? <ProfileForm initial={profile.data} /> : <Notice tone="error">画像暂时无法读取，请返回重试。</Notice>}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function ProfileForm({ initial }: { initial: JourneyProfile }) {
  const theme = useJourneyTheme();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(initial.display_name);
  const [height, setHeight] = useState(initial.height_cm == null ? '' : String(initial.height_cm));
  const [birthDate, setBirthDate] = useState(initial.birth_date ?? '');
  const [sex, setSex] = useState<Sex>(initial.sex ?? 'undisclosed');
  const [unit, setUnit] = useState<'metric' | 'imperial'>(initial.preferred_unit);
  const [error, setError] = useState('');
  const save = useMutation({ mutationFn: updateProfile, onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['profile'] }); router.back(); } });

  function submit() {
    const heightValue = height ? Number(height) : null;
    if (!displayName.trim()) { setError('昵称不能为空'); return; }
    if (heightValue != null && (heightValue < 80 || heightValue > 250)) { setError('身高需在 80—250 cm 之间'); return; }
    if (birthDate && !/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) { setError('生日格式应为 YYYY-MM-DD'); return; }
    setError('');
    save.mutate({ display_name: displayName.trim(), height_cm: heightValue, birth_date: birthDate || null, sex, preferred_unit: unit, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai', locale: 'zh-CN' }, { onError: (reason) => setError(reason instanceof ApiError ? reason.message : '保存失败') });
  }

  return <Card><SectionTitle>基础资料</SectionTitle><Field label="昵称" value={displayName} onChangeText={setDisplayName} /><Text style={[styles.label, { color: theme.colors.text }]}>性别</Text><View style={styles.chips}>{sexes.map((item) => <Chip key={item.value} label={item.label} selected={sex === item.value} onPress={() => setSex(item.value)} />)}</View><Field label="生日" hint="YYYY-MM-DD，可留空" value={birthDate} onChangeText={setBirthDate} keyboardType="numbers-and-punctuation" /><Field label="身高（cm）" value={height} onChangeText={setHeight} keyboardType="decimal-pad" /><Text style={[styles.label, { color: theme.colors.text }]}>显示单位</Text><View style={styles.chips}><Chip label="公制" selected={unit === 'metric'} onPress={() => setUnit('metric')} /><Chip label="英制" selected={unit === 'imperial'} onPress={() => setUnit('imperial')} /></View>{!!error && <Notice tone="error">{error}</Notice>}<Button loading={save.isPending} onPress={submit}>保存画像</Button></Card>;
}

function Header({ title }: { title: string }) {
  const theme = useJourneyTheme();
  return <View style={[styles.header, { borderBottomColor: theme.colors.border }]}><Button variant="ghost" onPress={() => router.back()}>取消</Button><Text style={[styles.title, { color: theme.colors.text }]}>{title}</Text><View style={styles.spacer} /></View>;
}

const styles = StyleSheet.create({ safe: { flex: 1 }, header: { minHeight: 58, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: journeySpacing.md }, title: { fontSize: journeyTypography.subtitle, fontWeight: '800' }, spacer: { width: 72 }, content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg }, label: { fontSize: journeyTypography.small, fontWeight: '700' }, chips: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm } });
