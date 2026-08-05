import type { PropsWithChildren, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
  type ViewStyle,
} from 'react-native';

import { journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';

import { useJourneyTheme } from '@/theme/theme-provider';

export function Card({ children, style }: PropsWithChildren<{ style?: ViewStyle }>) {
  const theme = useJourneyTheme();
  return <View style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }, style]}>{children}</View>;
}

export function SectionTitle({ children, action }: PropsWithChildren<{ action?: ReactNode }>) {
  const theme = useJourneyTheme();
  return <View style={styles.titleRow}><Text style={[styles.sectionTitle, { color: theme.colors.text }]}>{children}</Text>{action}</View>;
}

type ButtonProps = PropsWithChildren<{
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  accessibilityLabel?: string;
}>;

export function Button({ children, onPress, disabled, loading, variant = 'primary', accessibilityLabel }: ButtonProps) {
  const theme = useJourneyTheme();
  const backgroundColor = variant === 'primary' ? theme.colors.primary : variant === 'danger' ? theme.colors.danger : variant === 'secondary' ? theme.colors.hero : 'transparent';
  const color = variant === 'primary' || variant === 'danger' ? '#FFFFFF' : theme.colors.text;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={accessibilityLabel} disabled={disabled || loading} onPress={onPress}
      style={({ pressed }) => [styles.button, { backgroundColor, borderColor: theme.colors.border, opacity: disabled || loading ? 0.45 : pressed ? 0.72 : 1 }]}>
      {loading ? <ActivityIndicator color={color} /> : <Text style={[styles.buttonText, { color }]}>{children}</Text>}
    </Pressable>
  );
}

export function Field({ label, hint, error, ...props }: TextInputProps & { label: string; hint?: string; error?: string }) {
  const theme = useJourneyTheme();
  return (
    <View style={styles.fieldWrap}>
      <Text style={[styles.label, { color: theme.colors.text }]}>{label}</Text>
      <TextInput
        {...props}
        accessibilityLabel={props.accessibilityLabel ?? label}
        maxFontSizeMultiplier={1.5}
        placeholderTextColor={theme.colors.textMuted}
        style={[styles.input, { backgroundColor: theme.colors.background, borderColor: error ? theme.colors.danger : theme.colors.border, color: theme.colors.text }, props.style]}
      />
      {!!error && <Text style={[styles.hint, { color: theme.colors.danger }]}>{error}</Text>}
      {!error && !!hint && <Text style={[styles.hint, { color: theme.colors.textMuted }]}>{hint}</Text>}
    </View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected?: boolean; onPress: () => void }) {
  const theme = useJourneyTheme();
  return <Pressable accessibilityRole="button" accessibilityState={{ selected }} onPress={onPress} style={[styles.chip, { backgroundColor: selected ? theme.colors.primary : theme.colors.background, borderColor: selected ? theme.colors.primary : theme.colors.border }]}><Text style={{ color: selected ? '#FFFFFF' : theme.colors.text, fontWeight: '700' }}>{label}</Text></Pressable>;
}

export function Notice({ children, tone = 'info' }: PropsWithChildren<{ tone?: 'info' | 'warning' | 'error' | 'success' }>) {
  const theme = useJourneyTheme();
  const colors = tone === 'error' ? [theme.colors.dangerSoft, theme.colors.danger] : tone === 'warning' ? [theme.colors.warningSoft, theme.colors.warning] : tone === 'success' ? [theme.colors.hero, theme.colors.primaryStrong] : [theme.colors.infoSoft, theme.colors.info];
  return <View accessibilityLiveRegion="polite" style={[styles.notice, { backgroundColor: colors[0] as string }]}><Text style={[styles.noticeText, { color: colors[1] as string }]}>{children}</Text></View>;
}

export function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  const theme = useJourneyTheme();
  return <View style={[styles.metric, { backgroundColor: theme.colors.background }]}><Text style={[styles.metricValue, { color: accent ?? theme.colors.text }]}>{value}</Text><Text style={[styles.metricLabel, { color: theme.colors.textMuted }]}>{label}</Text></View>;
}

export function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  const theme = useJourneyTheme();
  return <Card><Text style={[styles.emptyTitle, { color: theme.colors.text }]}>{title}</Text><Text style={[styles.body, { color: theme.colors.textMuted }]}>{message}</Text>{action}</Card>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <View style={styles.errorState}><Notice tone="error">{message}</Notice><Button variant="secondary" onPress={onRetry}>重试</Button></View>;
}

export function LoadingState({ label = '正在加载…' }: { label?: string }) {
  const theme = useJourneyTheme();
  return <View style={styles.loading}><ActivityIndicator color={theme.colors.primary} /><Text style={{ color: theme.colors.textMuted }}>{label}</Text></View>;
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: journeyRadii.md, padding: journeySpacing.md, gap: journeySpacing.md },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: journeySpacing.md },
  sectionTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800', flexShrink: 1 },
  button: { minHeight: 48, borderRadius: journeyRadii.pill, borderWidth: 1, paddingHorizontal: 18, paddingVertical: 12, alignItems: 'center', justifyContent: 'center' },
  buttonText: { fontSize: journeyTypography.body, fontWeight: '800' },
  fieldWrap: { gap: 6 },
  label: { fontSize: journeyTypography.small, fontWeight: '700' },
  input: { minHeight: 50, borderWidth: 1, borderRadius: journeyRadii.sm, paddingHorizontal: 14, paddingVertical: 12, fontSize: journeyTypography.body },
  hint: { fontSize: journeyTypography.caption, lineHeight: 18 },
  chip: { borderWidth: 1, borderRadius: journeyRadii.pill, paddingHorizontal: 14, paddingVertical: 10 },
  notice: { borderRadius: journeyRadii.sm, padding: 13 },
  noticeText: { fontSize: journeyTypography.small, lineHeight: 21, fontWeight: '600' },
  metric: { flex: 1, minWidth: 92, borderRadius: journeyRadii.sm, padding: 12, gap: 4 },
  metricValue: { fontSize: 22, fontWeight: '800' },
  metricLabel: { fontSize: journeyTypography.caption },
  emptyTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  body: { fontSize: journeyTypography.body, lineHeight: 24 },
  loading: { minHeight: 120, alignItems: 'center', justifyContent: 'center', gap: journeySpacing.sm },
  errorState: { gap: journeySpacing.sm },
});
