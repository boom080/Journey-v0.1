import { fireEvent, render } from '@testing-library/react-native';
import { Text } from 'react-native';

import { Button, EmptyState, ErrorState, Field, LoadingState, Notice } from '@/components/ui';

const colors = {
  background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
  primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
  danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
  info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
};

jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ isDark: false, colors }),
}));

describe('shared UI states', () => {
  test('button is accessible, fires once, and loading disables it', async () => {
    const onPress = jest.fn();
    const screen = await render(<Button onPress={onPress}>保存</Button>);
    await fireEvent.press(screen.getByRole('button', { name: '保存' }));
    expect(onPress).toHaveBeenCalledTimes(1);

    await screen.rerender(<Button loading onPress={onPress}>保存</Button>);
    await fireEvent.press(screen.getByRole('button'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  test('field exposes label, hint, error and dynamic font cap', async () => {
    const screen = await render(<Field label="热量（kcal）" hint="可手动修正" value="520" />);
    expect(screen.getByLabelText('热量（kcal）').props.maxFontSizeMultiplier).toBe(1.5);
    expect(screen.getByText('可手动修正')).toBeTruthy();
    await screen.rerender(<Field label="热量（kcal）" error="请输入有效热量" value="" />);
    expect(screen.getByText('请输入有效热量')).toBeTruthy();
  });

  test('loading, empty, error and notice states remain explicit', async () => {
    const retry = jest.fn();
    const screen = await render(<LoadingState label="正在读取" />);
    expect(screen.getByText('正在读取')).toBeTruthy();
    await screen.rerender(<EmptyState title="还没有记录" message="先新增一条" action={<Text>开始</Text>} />);
    expect(screen.getByText('还没有记录')).toBeTruthy();
    await screen.rerender(<ErrorState message="网络错误" onRetry={retry} />);
    await fireEvent.press(screen.getByRole('button', { name: '重试' }));
    expect(retry).toHaveBeenCalledTimes(1);
    await screen.rerender(<Notice tone="warning">当前离线</Notice>);
    expect(screen.getByText('当前离线')).toBeTruthy();
  });
});
