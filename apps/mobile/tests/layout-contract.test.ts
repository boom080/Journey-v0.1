import fs from 'node:fs';
import path from 'node:path';

const src = path.resolve(__dirname, '../src');

function read(relative: string) {
  return fs.readFileSync(path.join(src, relative), 'utf8');
}

describe('cross-platform layout invariants', () => {
  test.each([
    'app/sign-in.tsx',
    'app/record/[kind].tsx',
    'app/settings/profile.tsx',
    'app/settings/goal.tsx',
  ])('%s retains safe area, keyboard handling, scrolling and phone-width cap', (file) => {
    const source = read(file);
    expect(source).toContain('SafeAreaView');
    expect(source).toContain('KeyboardAvoidingView');
    expect(source).toContain('ScrollView');
    expect(source).toMatch(/maxWidth:\s*(620|640)/);
  });

  test('theme keeps the confirmed warm white and mint brand palette fixed', () => {
    const source = read('theme/theme-provider.tsx');
    expect(source).toContain('lightColors');
    expect(source).toContain('isDark: false');
    expect(source).toContain('DefaultTheme');
    expect(source).not.toContain('darkColors');
    expect(source).not.toContain('useColorScheme');
  });

  test('primary Agent input caps dynamic font scaling and exposes an accessibility label', () => {
    const source = read('components/home-overview.tsx');
    expect(source).toContain('accessibilityLabel="统一记录输入"');
    expect(source).toContain('maxFontSizeMultiplier={1.5}');
  });

  test('home uses the original mascot and the confirmed warm dedicated hero', () => {
    const source = read('components/home-overview.tsx');
    expect(source).toContain("require('@/assets/brand/journey-leaf-home.png')");
    expect(source).toContain('warmHomeColors');
    expect(source).toContain('离线 · 手动可用');
    expect(source).toContain('numberOfLines={1}');
    expect(source).not.toContain("你好，{`\\n`}今天轻松记");
  });
});
