import { DefaultTheme, ThemeProvider } from 'expo-router';
import { createContext, type PropsWithChildren, useContext, useMemo } from 'react';

import { journeyColors } from '@journey/design-tokens';

const lightColors = {
  background: journeyColors.mint50,
  surface: journeyColors.surface,
  hero: journeyColors.mint100,
  border: journeyColors.border,
  primary: journeyColors.mint700,
  primaryStrong: journeyColors.mint700,
  text: journeyColors.ink900,
  textMuted: journeyColors.ink600,
  danger: journeyColors.danger,
  dangerSoft: journeyColors.rose100,
  warning: journeyColors.amber600,
  warningSoft: journeyColors.amber100,
  info: journeyColors.blue600,
  infoSoft: journeyColors.blue100,
  food: journeyColors.rose500,
};

type JourneyColors = {
  [Key in keyof typeof lightColors]: string;
};

type JourneyTheme = { isDark: boolean; colors: JourneyColors };

const JourneyThemeContext = createContext<JourneyTheme | null>(null);

export function JourneyThemeProvider({ children }: PropsWithChildren) {
  const value = useMemo<JourneyTheme>(
    () => ({ isDark: false, colors: lightColors }),
    [],
  );

  return (
    <JourneyThemeContext.Provider value={value}>
      <ThemeProvider
        value={{
          ...DefaultTheme,
          colors: {
            ...DefaultTheme.colors,
            background: value.colors.background,
            card: value.colors.surface,
            border: value.colors.border,
            primary: value.colors.primary,
            text: value.colors.text,
          },
        }}>
        {children}
      </ThemeProvider>
    </JourneyThemeContext.Provider>
  );
}

export function useJourneyTheme(): JourneyTheme {
  const value = useContext(JourneyThemeContext);
  if (!value) {
    throw new Error('useJourneyTheme 必须在 JourneyThemeProvider 内使用');
  }
  return value;
}
