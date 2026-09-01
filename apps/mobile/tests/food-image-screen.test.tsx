import { act, fireEvent, render, waitFor } from '@testing-library/react-native';

import type { FoodImageAnalysisResponse } from '@journey/contracts';

const mockAnalyzeFoodImage = jest.fn();
const mockLaunchLibrary = jest.fn();
const mockLaunchCamera = jest.fn();
const mockRequestCamera = jest.fn();
const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
const mockRouterReplace = jest.fn();
const mockSyncState = { isOnline: true };
const mockAgentDataDeletedListeners = new Set<() => void>();
let mockAgentDataRevision = 0;
let mockFoodImageEnabled = true;

jest.mock('expo-router', () => ({
  router: {
    back: (...args: unknown[]) => mockRouterBack(...args),
    push: (...args: unknown[]) => mockRouterPush(...args),
    replace: (...args: unknown[]) => mockRouterReplace(...args),
  },
}));
jest.mock('expo-image', () => ({ Image: require('react-native').Image }));
jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: (...args: unknown[]) => mockLaunchLibrary(...args),
  launchCameraAsync: (...args: unknown[]) => mockLaunchCamera(...args),
  requestCameraPermissionsAsync: (...args: unknown[]) => mockRequestCamera(...args),
}));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
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
    ApiError,
    ApiNetworkError,
    analyzeFoodImage: (...args: unknown[]) => mockAnalyzeFoodImage(...args),
    getAgentDataRevision: () => mockAgentDataRevision,
    subscribeToAgentDataDeleted: (listener: () => void) => {
      mockAgentDataDeletedListeners.add(listener);
      return () => mockAgentDataDeletedListeners.delete(listener);
    },
  };
});
jest.mock('@/config/environment', () => ({
  isFoodImageAnalysisEnabled: () => mockFoodImageEnabled,
}));

import FoodImageScreen from '@/app/food-image';

const response: FoodImageAnalysisResponse = {
  analysis_id: 'analysis-1',
  status: 'candidate',
  candidate: {
    kind: 'food',
    candidate_id: 'candidate-1',
    confirmation_token: 'confirmation-token',
    payload: {
      recorded_at: '2026-07-22T12:00:00Z',
      meal_type: 'lunch',
      name: '合成鸡肉饭',
      energy_kcal: 300,
      portion_amount: 1,
      portion_unit: '份',
      detail: '图片估算区间 180—450 kcal',
      source: 'image',
    },
    explanation: 'Mock 演示候选，未真实识别图片；请修改所有字段后再保存。',
  },
  estimate: {
    is_food: true,
    name: '合成鸡肉饭',
    items: [{ name: '合成鸡肉饭', portion_amount: 1, portion_unit: '份', energy_kcal: 300 }],
    meal_type: 'lunch',
    portion_amount: 1,
    portion_unit: '份',
    energy_kcal: 300,
    energy_min_kcal: 180,
    energy_max_kcal: 450,
    confidence: 'low',
    assumptions: ['Mock 演示值，未真实识别图片'],
    scale_reference_used: false,
    needs_user_correction: true,
  },
  message: '已生成图片估算候选，请校正后确认保存。',
  fallback_used: true,
  image_retained: false,
  usage: {
    provider: 'mock', model: 'journey-food-image-mock-v1', input_tokens: 0,
    output_tokens: 0, retries: 0, latency_ms: 1, estimated_cost_usd: 0,
  },
};

describe('Food image flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAgentDataDeletedListeners.clear();
    mockAgentDataRevision = 0;
    mockSyncState.isOnline = true;
    mockLaunchLibrary.mockResolvedValue({
      canceled: false,
      assets: [{ uri: 'file:///synthetic.jpg', base64: '/9j/4EpvdXJuZXk=', width: 640, height: 480 }],
    });
    mockRequestCamera.mockResolvedValue({ granted: true });
    mockAnalyzeFoodImage.mockResolvedValue(response);
    mockFoodImageEnabled = true;
  });

  test('feature flag disables every image acquisition action', async () => {
    mockFoodImageEnabled = false;
    const screen = await render(<FoodImageScreen />);
    expect(screen.getByText(/图片估算当前已关闭/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: '拍照' })).toBeNull();
    expect(screen.queryByRole('button', { name: '从相册选择' })).toBeNull();
    await fireEvent.press(screen.getByRole('button', { name: '使用手动饮食记录' }));
    expect(mockRouterReplace).toHaveBeenCalledWith('/record/food');
  });

  test('requires explicit upload then opens an editable image candidate', async () => {
    const screen = await render(<FoodImageScreen />);
    expect(screen.getByText('图片辅助估算（实验）')).toBeTruthy();
    expect(screen.getByText(/模型不能通过照片准确称重/)).toBeTruthy();
    expect(screen.getByText(/不要上传人脸/)).toBeTruthy();
    expect(screen.getByText(/完整盘沿、碗口或 Journey 参照卡/)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    expect(screen.getByLabelText('待分析食物照片')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(screen.getByText('合成鸡肉饭')).toBeTruthy());
    expect(mockAnalyzeFoodImage).toHaveBeenCalledWith(expect.objectContaining({
      confirm_upload: true,
      image_base64: '/9j/4EpvdXJuZXk=',
      media_type: 'image/jpeg',
      scale_reference_type: 'none',
      scale_reference_size_cm: null,
    }));
    expect(screen.getByText(/当前为 Mock 演示/)).toBeTruthy();
    expect(screen.getByText(/不是称重值 · 必须校正/)).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '打开表单校正' }));
    expect(mockRouterPush).toHaveBeenCalledWith(expect.objectContaining({
      pathname: '/record/[kind]',
      params: expect.objectContaining({ candidateSource: 'image', kind: 'food' }),
    }));
  });

  test('preserves PNG content type for the web picker', async () => {
    mockLaunchLibrary.mockResolvedValueOnce({
      canceled: false,
      assets: [{
        uri: 'blob:synthetic-png',
        base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB',
        mimeType: 'image/png',
        width: 1,
        height: 1,
      }],
    });
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(mockAnalyzeFoodImage).toHaveBeenCalledWith(
      expect.objectContaining({ media_type: 'image/png' }),
    ));
  });

  test('validates and sends a measured plate diameter reference', async () => {
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    await fireEvent.press(screen.getByRole('button', { name: '已知餐盘直径' }));
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    expect(screen.getByText(/请输入 8—60 厘米/)).toBeTruthy();
    expect(mockAnalyzeFoodImage).not.toHaveBeenCalled();

    await fireEvent.changeText(screen.getByLabelText('餐盘外沿直径（厘米）'), '24');
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(mockAnalyzeFoodImage).toHaveBeenCalledWith(
      expect.objectContaining({
        scale_reference_type: 'plate_diameter',
        scale_reference_size_cm: 24,
      }),
    ));
    expect(screen.getByText(/尺度参照：未可靠使用/)).toBeTruthy();
  });

  test('Journey card warns against personal cards and uses a fixed size', async () => {
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: 'Journey 参照卡' }));
    expect(screen.getByText(/不要使用银行卡或证件/)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(mockAnalyzeFoodImage).toHaveBeenCalledWith(
      expect.objectContaining({
        scale_reference_type: 'journey_card',
        scale_reference_size_cm: null,
      }),
    ));
  });

  test('camera denial and offline state fall back to manual entry', async () => {
    mockRequestCamera.mockResolvedValueOnce({ granted: false });
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '拍照' }));
    expect(screen.getByText(/未获得相机权限/)).toBeTruthy();

    mockSyncState.isOnline = false;
    await screen.rerender(<FoodImageScreen />);
    expect(screen.getByText(/当前离线/)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '直接手动记录饮食' }));
    expect(mockRouterPush).toHaveBeenCalledWith('/record/food');
  });

  test('deletion clears image Agent results but preserves the selected photo', async () => {
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(screen.getByText('合成鸡肉饭')).toBeTruthy());
    expect(screen.getByLabelText('待分析食物照片')).toBeTruthy();

    mockAgentDataRevision = 1;
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    expect(screen.queryByText('合成鸡肉饭')).toBeNull();
    expect(screen.getByLabelText('待分析食物照片')).toBeTruthy();
  });

  test('does not show a late image analysis response after deletion', async () => {
    let resolveAnalysis: ((value: FoodImageAnalysisResponse) => void) | undefined;
    mockAnalyzeFoodImage.mockImplementation(() => new Promise<FoodImageAnalysisResponse>((resolve) => { resolveAnalysis = resolve; }));
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    await fireEvent.press(screen.getByRole('button', { name: '同意上传并生成候选' }));
    await waitFor(() => expect(mockAnalyzeFoodImage).toHaveBeenCalled());

    mockAgentDataRevision = 1;
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    await act(async () => {
      resolveAnalysis?.(response);
    });
    expect(screen.queryByText('合成鸡肉饭')).toBeNull();
    expect(screen.getByLabelText('待分析食物照片')).toBeTruthy();
  });

  test('picker cancellation leaves no image and explains that nothing was uploaded', async () => {
    mockLaunchLibrary.mockResolvedValueOnce({ canceled: true, assets: null });
    const screen = await render(<FoodImageScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '从相册选择' }));
    expect(screen.getByText(/已取消选择/)).toBeTruthy();
    expect(mockAnalyzeFoodImage).not.toHaveBeenCalled();
  });
});
