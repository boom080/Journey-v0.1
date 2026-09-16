import { fireEvent, render, waitFor } from '@testing-library/react-native';

import type { JourneyProfile } from '@journey/contracts';

const mockSaveProfile = jest.fn();
const mockSubmitRecord = jest.fn();
const mockFetchProfile = jest.fn();
const mockRouterBack = jest.fn();
const mockInvalidateQueries = jest.fn();
const mockUseQuery = jest.fn();
type MockMutationOptions = {
  mutationFn: (variables: unknown) => Promise<unknown>;
  onSuccess?: (result: unknown) => Promise<void> | void;
};
const mockUseMutation = jest.fn((options: MockMutationOptions) => ({
  isPending: false,
  mutate: (variables: unknown, callbacks?: { onError?: (reason: unknown) => void }) => {
    void options.mutationFn(variables)
      .then(async (result) => { await options.onSuccess?.(result); })
      .catch((reason) => callbacks?.onError?.(reason));
  },
}));
const mockSyncState = {
  isOnline: true,
  fetchProfile: (...args: unknown[]) => mockFetchProfile(...args),
  saveProfile: (...args: unknown[]) => mockSaveProfile(...args),
  submitRecord: (...args: unknown[]) => mockSubmitRecord(...args),
};

jest.mock('expo-router', () => ({ router: { back: (...args: unknown[]) => mockRouterBack(...args) } }));
jest.mock('@tanstack/react-query', () => ({
  useMutation: (options: unknown) => mockUseMutation(options as MockMutationOptions),
  useQuery: (options: unknown) => mockUseQuery(options),
  useQueryClient: () => ({ invalidateQueries: (...args: unknown[]) => mockInvalidateQueries(...args) }),
}));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  } }),
}));

import ProfileSettingsScreen from '@/app/settings/profile';

const profile: JourneyProfile = {
  user_id: 'user-1',
  display_name: 'Journey01',
  timezone: 'Asia/Shanghai',
  locale: 'zh-CN',
  sex: 'male',
  birth_date: '2002-09-09',
  height_cm: 180,
  preferred_unit: 'metric',
  latest_weight_kg: null,
  version: 1,
  updated_at: '2026-09-02T02:00:00Z',
};

async function renderScreen() {
  return render(<ProfileSettingsScreen />);
}

describe('profile settings screen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchProfile.mockResolvedValue(profile);
    mockSaveProfile.mockResolvedValue('saved');
    mockSubmitRecord.mockResolvedValue('saved');
    mockInvalidateQueries.mockResolvedValue(undefined);
    mockUseQuery.mockReturnValue({ isLoading: false, data: profile });
  });

  test('records current weight while saving the profile and preserves the weight history model', async () => {
    const screen = await renderScreen();
    const weightField = await screen.findByLabelText('当前体重（kg）');
    await fireEvent.changeText(weightField, '72.5');
    await fireEvent.press(screen.getByRole('button', { name: '保存画像与当前体重' }));

    await waitFor(() => expect(mockSaveProfile).toHaveBeenCalledWith(profile, expect.objectContaining({
      display_name: 'Journey01',
      height_cm: 180,
    })));
    expect(mockSubmitRecord).toHaveBeenCalledWith('weight', expect.objectContaining({
      weight_kg: 72.5,
      source: 'manual',
    }));
    expect(mockSubmitRecord.mock.calls[0]![1].measured_at).toEqual(expect.any(String));
    await waitFor(() => expect(mockRouterBack).toHaveBeenCalled());
  });

  test('rejects an impossible current weight before saving anything', async () => {
    const screen = await renderScreen();
    const weightField = await screen.findByLabelText('当前体重（kg）');
    await fireEvent.changeText(weightField, '12');
    await fireEvent.press(screen.getByRole('button', { name: '保存画像与当前体重' }));

    expect(screen.getByText('当前体重需在 25—400 kg 之间')).toBeTruthy();
    expect(mockSaveProfile).not.toHaveBeenCalled();
    expect(mockSubmitRecord).not.toHaveBeenCalled();
  });
});
