import { Image } from 'expo-image';
import type { PropsWithChildren, ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { journeyRadii, journeySpacing } from '@journey/design-tokens';

import { useJourneyTheme } from '@/theme/theme-provider';

type DefaultHeroProps = { eyebrow: string; title: string; hero?: never };
type CustomHeroProps = { eyebrow?: never; title?: never; hero: ReactNode };
type ScreenShellProps = PropsWithChildren<(DefaultHeroProps | CustomHeroProps) & { backgroundColor?: string }>;

export function ScreenShell({ eyebrow, title, hero, backgroundColor, children }: ScreenShellProps) {
  const theme = useJourneyTheme();

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: backgroundColor ?? theme.colors.background }]} edges={['top']}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
        {hero ?? (
          <View style={[styles.hero, { backgroundColor: theme.colors.hero }]}>
            <View style={styles.heroCopy}>
              <Text style={[styles.eyebrow, { color: theme.colors.primaryStrong }]}>{eyebrow}</Text>
              <Text style={[styles.title, { color: theme.colors.text }]}>{title}</Text>
            </View>
            <Image source={require('@/assets/brand/journey-leaf-home.png')} style={styles.character} contentFit="contain" />
          </View>
        )}
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  content: {
    width: '100%',
    maxWidth: 720,
    alignSelf: 'center',
    padding: journeySpacing.lg,
    gap: journeySpacing.lg,
  },
  hero: {
    minHeight: 180,
    borderRadius: journeyRadii.lg,
    padding: journeySpacing.lg,
    overflow: 'hidden',
    flexDirection: 'row',
    alignItems: 'center',
  },
  heroCopy: { flex: 1, gap: journeySpacing.sm },
  eyebrow: { fontSize: 14, fontWeight: '700', letterSpacing: 0.5 },
  title: { fontSize: 38, lineHeight: 44, fontWeight: '800' },
  character: { width: 128, height: 128 },
});
