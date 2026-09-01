const mockConstantsState: { expoConfig: { extra?: Record<string, unknown> } | null } = {
  expoConfig: null,
};

jest.mock('expo-constants', () => ({
  __esModule: true,
  default: {
    get expoConfig() {
      return mockConstantsState.expoConfig;
    },
  },
}));

import {
  getLocalTestAccount,
  isAgentDebugDetailsEnabled,
  isFoodImageAnalysisEnabled,
} from '@/config/environment';

describe('runtime capabilities', () => {
  beforeEach(() => {
    mockConstantsState.expoConfig = null;
  });

  test('fails closed when the runtime manifest is missing', () => {
    expect(isFoodImageAnalysisEnabled()).toBe(false);
    expect(isAgentDebugDetailsEnabled()).toBe(false);
    expect(getLocalTestAccount()).toBeNull();
  });

  test('allows explicitly enabled development capabilities', () => {
    mockConstantsState.expoConfig = {
      extra: {
        appVariant: 'development',
        capabilities: {
          foodImageAnalysis: true,
          localTestAccount: true,
          agentDebugDetails: true,
        },
        localTestAccount: {
          identifier: 'demo@journey.local',
          password: 'JourneyDemo2026',
        },
      },
    };

    expect(isFoodImageAnalysisEnabled()).toBe(true);
    expect(isAgentDebugDetailsEnabled()).toBe(true);
    expect(getLocalTestAccount()).toEqual({
      identifier: 'demo@journey.local',
      password: 'JourneyDemo2026',
    });
  });

  test('ignores enabled flags outside the development variant', () => {
    mockConstantsState.expoConfig = {
      extra: {
        appVariant: 'production',
        capabilities: {
          foodImageAnalysis: true,
          localTestAccount: true,
          agentDebugDetails: true,
        },
        localTestAccount: {
          identifier: 'demo@journey.local',
          password: 'JourneyDemo2026',
        },
      },
    };

    expect(isFoodImageAnalysisEnabled()).toBe(false);
    expect(isAgentDebugDetailsEnabled()).toBe(false);
    expect(getLocalTestAccount()).toBeNull();
  });
});
