function toNumber(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? amount : 0;
}

function getRecordCount(summary = {}) {
  const foodCount = toNumber(summary?.extra?.record_counts?.food);
  const activityCount = toNumber(summary?.extra?.record_counts?.activity);
  return foodCount + activityCount;
}

export function buildHomeSummaryText(summary = {}) {
  const intakeKcal = toNumber(summary.intake_kcal);
  const activityKcal = toNumber(summary.activity_kcal);
  const dailyEnergyKcal = toNumber(summary.daily_energy_kcal || summary?.extra?.daily_energy?.daily_energy_kcal);
  const netKcal = toNumber(summary.net_kcal);
  const totalRecords = getRecordCount(summary);

  if (!totalRecords && !intakeKcal && !activityKcal) {
    return "今天还没有记录，先记下一餐或一项活动。";
  }

  if (activityKcal >= 2800 || netKcal <= -2800) {
    return "今日消耗明显偏高，建议检查活动记录是否准确。";
  }

  if (intakeKcal >= 3500 || netKcal >= 2200) {
    return "今日热量差值较大，建议结合实际情况再看看。";
  }

  if (Math.abs(netKcal) >= 1600) {
    return "数据波动较大，建议再补充确认今天的记录。";
  }

  if (activityKcal > dailyEnergyKcal * 0.9 && activityKcal >= 1000) {
    return "今天活动记录较多，可以顺手再确认一下时间和消耗。";
  }

  if (intakeKcal > 0 && !activityKcal) {
    return "今天已经记下饮食了，再补一条活动会更完整。";
  }

  if (activityKcal > 0 && !intakeKcal) {
    return "今天已经记下活动了，再补一条饮食会更完整。";
  }

  if (totalRecords >= 2 && Math.abs(netKcal) <= 600) {
    return "今天的记录比较完整，可以继续按实际情况补充。";
  }

  return "今天有新的记录，继续按实际情况补充就好。";
}
