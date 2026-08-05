import assert from 'node:assert/strict';
import test from 'node:test';

import { classifyMockInput } from './mock-intent.ts';

test('饮食输入只生成待确认候选', () => {
  const result = classifyMockInput('午餐吃了鸡肉饭 520 kcal');
  assert.equal(result?.kind, 'food');
  if (result?.kind === 'food') {
    assert.equal(result.energyKcal, 520);
    assert.equal(result.mealType, 'lunch');
  }
});

test('运动输入提取时长和热量', () => {
  const result = classifyMockInput('跑步 30 分钟 180 千卡');
  assert.equal(result?.kind, 'activity');
  if (result?.kind === 'activity') {
    assert.equal(result.durationMinutes, 30);
    assert.equal(result.energyKcal, 180);
  }
});

test('体重输入提取合理数值', () => {
  const result = classifyMockInput('今天体重 65.5');
  assert.deepEqual(result && { kind: result.kind, weightKg: result.kind === 'weight' ? result.weightKg : null }, { kind: 'weight', weightKg: 65.5 });
});

test('离线常识使用版本化固定内容', () => {
  const result = classifyMockInput('睡眠会影响训练吗');
  assert.equal(result?.kind, 'knowledge');
  if (result?.kind === 'knowledge') assert.match(result.explanation, /常识包 v1/);
});

test('未知输入不会伪造 Agent 结果', () => {
  assert.equal(classifyMockInput('xyz-unknown-intent'), null);
});
