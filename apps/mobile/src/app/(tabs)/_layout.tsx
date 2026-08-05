import { Tabs } from 'expo-router';
import { Text } from 'react-native';

import { useJourneyTheme } from '@/theme/theme-provider';

export default function TabLayout() {
  const theme = useJourneyTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.textMuted,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
          minHeight: 64,
          paddingTop: 6,
        },
        tabBarLabelStyle: { fontWeight: '700', fontSize: 12 },
      }}>
      <Tabs.Screen name="index" options={{ title: '首页', tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 19 }}>⌂</Text> }} />
      <Tabs.Screen name="journey" options={{ title: 'Journey', tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>↗</Text> }} />
      <Tabs.Screen name="profile" options={{ title: '我的', tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>●</Text> }} />
    </Tabs>
  );
}
