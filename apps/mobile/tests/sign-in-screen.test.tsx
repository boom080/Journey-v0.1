import { fireEvent, render, waitFor } from '@testing-library/react-native';

const mockSignIn = jest.fn();
const mockSignUp = jest.fn();

jest.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({ signIn: (...args: unknown[]) => mockSignIn(...args), signUp: (...args: unknown[]) => mockSignUp(...args) }),
}));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  }}),
}));
jest.mock('expo-image', () => ({ Image: () => null }));
jest.mock('@/lib/api', () => {
  class ApiError extends Error {}
  return { ApiError };
});

import SignInScreen from '@/app/sign-in';

describe('sign-in page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignIn.mockResolvedValue(undefined);
    mockSignUp.mockResolvedValue(undefined);
  });

  test('local test account remains a one-click deterministic login', async () => {
    const screen = await render(<SignInScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '使用本地测试账号' }));
    await waitFor(() => expect(mockSignIn).toHaveBeenCalledWith({
      identifier: 'demo@journey.local',
      password: 'JourneyDemo2026',
    }));
  });

  test('registration validates fields and sends the stable contract', async () => {
    const screen = await render(<SignInScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '创建账号' }));
    await fireEvent.changeText(screen.getByLabelText('昵称'), 'Stage 7');
    await fireEvent.changeText(screen.getByLabelText('邮箱'), 'stage7@example.com');
    await fireEvent.changeText(screen.getByLabelText('用户名'), 'stage7_user');
    await fireEvent.changeText(screen.getByLabelText('密码'), 'JourneyPass2026');
    await fireEvent.press(screen.getByRole('button', { name: '创建并登录' }));
    await waitFor(() => expect(mockSignUp).toHaveBeenCalledWith({
      email: 'stage7@example.com', username: 'stage7_user', password: 'JourneyPass2026', display_name: 'Stage 7',
    }));
  });

  test('authentication failure renders an explicit error state', async () => {
    mockSignIn.mockRejectedValueOnce(new Error('offline'));
    const screen = await render(<SignInScreen />);
    await fireEvent.changeText(screen.getByLabelText('邮箱或用户名'), 'stage7');
    await fireEvent.changeText(screen.getByLabelText('密码'), 'wrong-password');
    await fireEvent.press(screen.getByRole('button', { name: '进入 Journey' }));
    await waitFor(() => expect(screen.getByText('暂时无法登录，请稍后重试')).toBeTruthy());
  });
});
