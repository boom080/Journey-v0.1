import { fireEvent, render, waitFor } from '@testing-library/react-native';
import type { LifeInspiration } from '@journey/contracts';

const mockPreview = jest.fn();
const mockCreate = jest.fn();
const mockDelete = jest.fn();
const mockRefetch = jest.fn();
const mockSyncState = { isOnline: true };
let mockItems: LifeInspiration[] = [];

jest.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ isLoading: false, data: { items: mockItems, meta: { limit: 100, offset: 0, total: mockItems.length } }, refetch: mockRefetch }),
}));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
jest.mock('@/components/screen-shell', () => ({ ScreenShell: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ isDark: false, colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  }}),
}));
jest.mock('@/lib/api', () => {
  class ApiError extends Error {}
  class ApiNetworkError extends Error {}
  return {
    ApiError, ApiNetworkError,
    previewInspiration: (...args: unknown[]) => mockPreview(...args),
    createInspiration: (...args: unknown[]) => mockCreate(...args),
    deleteInspiration: (...args: unknown[]) => mockDelete(...args),
    listInspirations: jest.fn(),
  };
});

import InspirationsScreen from '@/app/inspirations';

const saved: LifeInspiration = {
  id: 'inspiration-1', source_url: 'https://www.xiaohongshu.com/explore/public-note',
  source_name: '小红书', title: '周末轻徒步', summary: '和朋友去近郊走走', tags: ['周末', '户外'],
  evidence_level: 'inspiration_only', source_checked_at: '2026-08-09T08:00:00Z',
  created_at: '2026-08-09T08:01:00Z', updated_at: '2026-08-09T08:01:00Z',
};

describe('Life inspiration active-share flow', () => {
  beforeEach(() => {
    jest.clearAllMocks(); mockItems = []; mockSyncState.isOnline = true;
    mockPreview.mockResolvedValue({
      status: 'preview', source_url: saved.source_url, source_name: '小红书',
      title: saved.title, summary: saved.summary, source_checked_at: saved.source_checked_at,
      safety_flags: ['untrusted_external_content', 'inspiration_only'], message: '请确认后保存。',
    });
    mockCreate.mockResolvedValue(saved); mockDelete.mockResolvedValue({ message: 'deleted' });
    mockRefetch.mockResolvedValue(undefined);
  });

  test('requires a user-triggered preview and explicit confirmation before save', async () => {
    const screen = await render(<InspirationsScreen />);
    expect(screen.getByText(/不绑定账号、不读取 Cookie、不后台抓取/)).toBeTruthy();
    await fireEvent.changeText(screen.getByLabelText('公开分享链接'), saved.source_url);
    await fireEvent.press(screen.getByRole('button', { name: '预览公开链接' }));
    await waitFor(() => expect(screen.getByLabelText('标题').props.value).toBe('周末轻徒步'));
    expect(screen.getByText(/生活灵感 · 非健康证据/)).toBeTruthy();
    expect(mockCreate).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByRole('button', { name: '我确认由自己主动保存' }));
    await fireEvent.press(screen.getByRole('button', { name: '确认保存生活灵感' }));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      confirmed: true, source_url: saved.source_url, title: saved.title,
    })));
    expect(mockRefetch).toHaveBeenCalled();
  });

  test('keeps the link and allows manual metadata when public preview is unavailable', async () => {
    mockPreview.mockResolvedValueOnce({
      status: 'manual_required', source_url: saved.source_url, source_name: '小红书',
      title: null, summary: null, source_checked_at: saved.source_checked_at,
      safety_flags: ['untrusted_external_content', 'fetch_failed'],
      message: '公开页面不可读取；请手动填写。',
    });
    const screen = await render(<InspirationsScreen />);
    await fireEvent.changeText(screen.getByLabelText('公开分享链接'), saved.source_url);
    await fireEvent.press(screen.getByRole('button', { name: '预览公开链接' }));
    await waitFor(() => expect(screen.getByText('改为手动填写')).toBeTruthy());
    expect(screen.getByLabelText('公开分享链接').props.value).toBe(saved.source_url);
    expect(screen.getByLabelText('标题').props.value).toBe('');
  });

  test('does not call the backend while offline', async () => {
    mockSyncState.isOnline = false;
    const screen = await render(<InspirationsScreen />);
    expect(screen.getByText(/当前离线/)).toBeTruthy();
    await fireEvent.changeText(screen.getByLabelText('公开分享链接'), saved.source_url);
    await fireEvent.press(screen.getByRole('button', { name: '预览公开链接' }));
    expect(mockPreview).not.toHaveBeenCalled();
  });

  test('uses a two-step user confirmation before deletion', async () => {
    mockItems = [saved];
    const screen = await render(<InspirationsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '删除 周末轻徒步' }));
    expect(mockDelete).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByRole('button', { name: '确认删除 周末轻徒步' }));
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('inspiration-1'));
  });
});
