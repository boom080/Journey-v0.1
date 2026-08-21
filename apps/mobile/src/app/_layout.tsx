import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { JourneyThemeProvider, useJourneyTheme } from '@/theme/theme-provider';
import { LoadingState } from '@/components/ui';
import { AuthProvider, useAuth } from '@/providers/auth-provider';
import { JourneyQueryProvider } from '@/providers/query-provider';
import { SyncProvider } from '@/providers/sync-provider';

function RootNavigator() {
  const theme = useJourneyTheme();
  const { session, isLoading } = useAuth();

  if (isLoading) return <LoadingState label="正在恢复 Journey 会话…" />;

  return (
    <>
      <StatusBar style={theme.isDark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: theme.colors.background } }}>
        <Stack.Protected guard={Boolean(session)}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="record/[kind]" options={{ presentation: 'modal' }} />
          <Stack.Screen name="food-image" options={{ presentation: 'modal' }} />
          <Stack.Screen name="inspirations" options={{ presentation: 'modal' }} />
          <Stack.Screen name="settings/profile" options={{ presentation: 'modal' }} />
          <Stack.Screen name="settings/goal" options={{ presentation: 'modal' }} />
        </Stack.Protected>
        <Stack.Protected guard={!session}>
          <Stack.Screen name="sign-in" />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <JourneyThemeProvider>
      <JourneyQueryProvider>
        <AuthProvider>
          <SyncProvider>
            <RootNavigator />
          </SyncProvider>
        </AuthProvider>
      </JourneyQueryProvider>
    </JourneyThemeProvider>
  );
}
