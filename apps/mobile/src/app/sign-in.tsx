import { Image } from 'expo-image';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, Field, Notice } from '@/components/ui';
import { getLocalTestAccount, type LocalTestAccount } from '@/config/environment';
import { ApiError } from '@/lib/api';
import { useAuth } from '@/providers/auth-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const USERNAME_PATTERN = /^[a-zA-Z][a-zA-Z0-9_]{2,31}$/;

function utf8ByteLength(value: string) {
  return Array.from(value).reduce((total, character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    if (codePoint <= 0x7f) return total + 1;
    if (codePoint <= 0x7ff) return total + 2;
    if (codePoint <= 0xffff) return total + 3;
    return total + 4;
  }, 0);
}

function getDisplayNameError(value: string) {
  if (!value) return '';
  const normalized = value.trim();
  if (!normalized) return '昵称不能只包含空格';
  if (Array.from(normalized).length > 50) return '昵称不能超过 50 个字符';
  return '';
}

function getEmailError(value: string) {
  if (!value) return '';
  if (!EMAIL_PATTERN.test(value.trim())) return '请输入有效邮箱，例如 name@example.com';
  return '';
}

function getUsernameError(value: string) {
  if (!value) return '';
  if (!USERNAME_PATTERN.test(value.trim())) return '用户名需为 3—32 位，以字母开头，只能包含字母、数字或下划线';
  return '';
}

function getPasswordError(value: string) {
  if (!value) return '';
  const byteLength = utf8ByteLength(value);
  if (byteLength < 10) return '密码至少需要 10 个 UTF-8 字节';
  if (byteLength > 72) return '密码不能超过 72 个 UTF-8 字节';
  if (!/[a-z]/.test(value) || !/[A-Z]/.test(value) || !/\d/.test(value)) {
    return '密码必须同时包含大写字母、小写字母和数字';
  }
  return '';
}

export default function SignInScreen() {
  const theme = useJourneyTheme();
  const { signIn, signUp } = useAuth();
  const localTestAccount = getLocalTestAccount();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const displayNameError = getDisplayNameError(displayName);
  const emailError = getEmailError(email);
  const usernameError = getUsernameError(username);
  const passwordError = getPasswordError(password);
  const registrationComplete = Boolean(displayName.trim() && email.trim() && username.trim() && password);
  const registrationValid = registrationComplete && !displayNameError && !emailError && !usernameError && !passwordError;
  const visibleRegistrationErrorCount = [displayNameError, emailError, usernameError, passwordError].filter(Boolean).length;

  async function submit(testAccount?: LocalTestAccount) {
    setPending(true);
    setError('');
    try {
      if (testAccount) await signIn(testAccount);
      else if (mode === 'login') await signIn({ identifier: identifier.trim(), password });
      else await signUp({ email: email.trim(), username: username.trim(), password, display_name: displayName.trim() });
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '暂时无法登录，请稍后重试');
    } finally {
      setPending(false);
    }
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
          <View style={[styles.hero, { backgroundColor: theme.colors.hero }]}>
            <View style={styles.heroCopy}>
              <Text style={[styles.eyebrow, { color: theme.colors.primaryStrong }]}>JOURNEY / 即刻</Text>
              <Text style={[styles.title, { color: theme.colors.text }]}>把今天轻轻记下来</Text>
              <Text style={[styles.lead, { color: theme.colors.textMuted }]}>饮食、运动与体重，由你确认后再写入。</Text>
            </View>
            <Image source={require('@/assets/brand/journey-leaf-home.png')} contentFit="contain" style={styles.character} />
          </View>
          <Card>
            <View style={styles.chips}>
              <Chip label="登录" selected={mode === 'login'} onPress={() => { setMode('login'); setError(''); }} />
              <Chip label="创建账号" selected={mode === 'register'} onPress={() => { setMode('register'); setError(''); }} />
            </View>
            {mode === 'login' ? (
              <>
                <Field label="邮箱或用户名" value={identifier} onChangeText={setIdentifier} autoCapitalize="none" autoCorrect={false} textContentType="username" />
                <Field label="密码" value={password} onChangeText={setPassword} secureTextEntry textContentType="password" />
                <Button loading={pending} disabled={!identifier.trim() || !password} onPress={() => void submit()}>进入 Journey</Button>
                {localTestAccount && (
                  <Button variant="secondary" disabled={pending} onPress={() => void submit(localTestAccount)}>
                    使用本地测试账号
                  </Button>
                )}
              </>
            ) : (
              <>
                <Field label="昵称" error={displayNameError} value={displayName} onChangeText={setDisplayName} />
                <Field label="邮箱" error={emailError} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
                <Field label="用户名" hint="3—32 位，以字母开头，可使用字母、数字和下划线" error={usernameError} value={username} onChangeText={setUsername} autoCapitalize="none" />
                <Field label="密码" hint="至少 10 位，包含大写字母、小写字母和数字" error={passwordError} value={password} onChangeText={setPassword} secureTextEntry />
                {visibleRegistrationErrorCount > 0 && (
                  <Notice tone="warning">还有 {visibleRegistrationErrorCount} 项格式不正确，请按红色提示修改。</Notice>
                )}
                <Button loading={pending} disabled={!registrationValid} onPress={() => void submit()}>创建并登录</Button>
              </>
            )}
            {!!error && <Notice tone="error">{error}</Notice>}
          </Card>
          <Text style={[styles.footnote, { color: theme.colors.textMuted }]}>本应用用于一般健身、营养和生活方式管理，不提供医疗诊断或治疗建议。</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 }, flex: { flex: 1 },
  content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg, gap: journeySpacing.lg, justifyContent: 'center', flexGrow: 1 },
  hero: { minHeight: 220, borderRadius: journeyRadii.lg, padding: journeySpacing.lg, flexDirection: 'row', alignItems: 'center', overflow: 'hidden' },
  heroCopy: { flex: 1, gap: journeySpacing.sm },
  eyebrow: { fontSize: journeyTypography.caption, fontWeight: '800', letterSpacing: 1 },
  title: { fontSize: 34, lineHeight: 41, fontWeight: '900' },
  lead: { fontSize: journeyTypography.body, lineHeight: 24 },
  character: { width: 120, height: 150 },
  chips: { flexDirection: 'row', gap: journeySpacing.sm },
  footnote: { textAlign: 'center', fontSize: journeyTypography.caption, lineHeight: 18, paddingHorizontal: journeySpacing.md },
});
