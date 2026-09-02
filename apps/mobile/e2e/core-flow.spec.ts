import { expect, test } from '@playwright/test';

const SYNTHETIC_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

test('资料目标、Multi-Agent 复合输入、确认门、Journey 周总结闭环', async ({ page }) => {
  page.on('dialog', async (dialog) => dialog.accept());
  await page.goto('/');
  await expect(page.getByText('把今天轻轻记下来')).toBeVisible();
  await page.getByRole('button', { name: '使用本地测试账号' }).click();
  await expect(page.getByLabel('统一记录输入')).toBeVisible();

  await page.goto('/settings/profile');
  await expect(page.getByText('编辑画像')).toBeVisible();
  await page.getByLabel('昵称').fill('Stage 7 E2E');
  await page.getByLabel('身高（cm）').fill('170');
  await page.getByRole('button', { name: '保存画像' }).click();
  await page.goto('/profile');
  await expect(page.getByText('Stage 7 E2E')).toBeVisible();

  await page.goto('/settings/goal');
  await expect(page.getByText('目标设置')).toBeVisible();
  await page.getByRole('button', { name: '保持' }).click();
  await page.getByLabel('目标体重（kg）').fill('65');
  await page.getByLabel('每日能量目标（kcal）').fill('2000');
  await page.getByRole('button', { name: '保存目标' }).click();
  await page.goto('/profile');
  await expect(page.getByText('目标体重 65 kg · 每日能量 2000 kcal')).toBeVisible();

  await page.goto('/');
  await page.getByLabel('统一记录输入').fill('今天中午吃了一份牛肉面，晚上跑了5公里，我这周减脂情况怎么样？');
  await page.getByRole('button', { name: '理解并处理' }).click();
  await expect(page.getByText('Agent 执行计划')).toBeVisible();
  await expect(page.getByText(/Orchestrator → Record Agent → Summary Agent → Knowledge Agent/)).toBeVisible();
  await expect(page.getByText('Record Agent · food.parse_candidate', { exact: true })).toBeVisible();
  await expect(page.getByText('Record Agent · activity.parse_candidate', { exact: true })).toBeVisible();
  await expect(page.getByText('Summary Agent · weekly_summary.generate', { exact: true })).toBeVisible();
  await expect(page.getByText(/校验：写入候选已生成/)).toBeVisible();
  await expect(page.getByRole('button', { name: '打开并确认候选' })).toHaveCount(2);
  await page.getByRole('button', { name: '打开并确认候选' }).first().click();
  await expect(page.getByText('这是 Agent 生成的候选。请核对并修改字段；只有点击下方按钮后才会写入。')).toBeVisible();
  await page.getByRole('button', { name: /确认候选并/ }).click();

  await expect(page.getByRole('button', { name: '打开并确认候选' })).toHaveCount(1);
  await page.getByRole('button', { name: '打开并确认候选' }).click();
  await page.getByRole('button', { name: /确认候选并/ }).click();
  await expect(page.getByText(/近 7 天记录覆盖/)).toBeVisible();
  await expect(page.getByText(/运行模式：MOCK/)).toBeVisible();

  await page.goto('/journey');
  await expect(page.getByText(/牛肉面/).first()).toBeVisible();
  await expect(page.getByText(/跑了5公里/).first()).toBeVisible();
  await page.getByRole('button', { name: '生成' }).click();
  await expect(page.getByText(/近 7 天记录覆盖/)).toBeVisible();
  await expect(page.getByText(/依据：/).first()).toBeVisible();
});

test('食物图片只生成 Mock 候选，用户校正后才写入', async ({ page }) => {
  page.on('dialog', async (dialog) => dialog.accept());
  await page.goto('/');
  await page.getByRole('button', { name: '使用本地测试账号' }).click();
  await expect(page.getByLabel('统一记录输入')).toBeVisible();

  await page.goto('/food-image');
  await expect(page.getByText('图片辅助估算（实验）')).toBeVisible();
  await expect(page.getByText(/模型不能通过照片准确称重/)).toBeVisible();
  await expect(page.getByText(/不要上传人脸/)).toBeVisible();
  const chooserPromise = page.waitForEvent('filechooser');
  await page.getByRole('button', { name: '从相册选择' }).click();
  const chooser = await chooserPromise;
  await chooser.setFiles({
    name: 'stage9-synthetic-food.png',
    mimeType: 'image/png',
    buffer: SYNTHETIC_PNG,
  });
  await expect(page.getByRole('img', { name: '待分析食物照片' })).toBeAttached();
  await page.getByLabel('可选说明').fill('Stage9 合成测试餐');
  await page.getByRole('button', { name: '同意上传并生成候选' }).click();
  await expect(page.getByText(/当前为 Mock 演示/)).toBeVisible();
  await expect(page.getByText('Stage9 合成测试餐', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '打开表单校正' }).click();
  await expect(page.getByText(/这是图片估算候选/)).toBeVisible();
  await page.getByLabel('食物名称').fill('Stage9 用户校正餐');
  await page.getByLabel('热量（kcal）').fill('486');
  await page.getByRole('button', { name: '确认候选并保存' }).click();

  await page.goto('/journey');
  await expect(page.getByText('Stage9 用户校正餐').first()).toBeVisible();
  await expect(page.getByText('486 kcal').first()).toBeVisible();
});
