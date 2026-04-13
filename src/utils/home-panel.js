import { safeList } from "./day";

export const HOME_UPDATES_PAGE_SIZE = 3;
const STICKER_MIN_LENGTH = 30;
const STICKER_MAX_LENGTH = 55;
const DEFAULT_STICKER_TEXT = "把节奏放轻一点，先把眼前这一小步接住，剩下的就慢慢来。";

function cleanText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
}

function squashWhitespace(text) {
  return cleanText(text).replace(/\s+/g, " ");
}

function stripStickerPrefix(text) {
  return squashWhitespace(text)
    .replace(/^(今日贴纸|今日建议|今日提醒|今天的小提醒|小提醒|提醒|建议)[：:]\s*/u, "")
    .replace(/^(AI|系统)(建议|提醒|播报)?[：:]\s*/iu, "")
    .replace(/^[\-•·]\s*/u, "")
    .trim();
}

function ensurePunctuation(text) {
  if (!text) {
    return "";
  }

  if (/[。！？!?]$/u.test(text)) {
    return text;
  }

  return `${text}。`;
}

function softenSentence(text) {
  const baseText = cleanText(text).replace(/[。！？!?]+$/u, "");

  if (!baseText) {
    return DEFAULT_STICKER_TEXT;
  }

  if (baseText.length >= STICKER_MIN_LENGTH) {
    return ensurePunctuation(baseText);
  }

  if (/(异常|偏高|偏低|波动|确认|检查|过头)/u.test(baseText)) {
    return ensurePunctuation(`步子先放慢一点，${baseText}，回头再轻轻确认一下就好`);
  }

  return ensurePunctuation(`把节奏放轻一点，${baseText}，剩下的就慢慢来`);
}

function clampStickerLength(text) {
  const baseText = ensurePunctuation(text);
  if (baseText.length <= STICKER_MAX_LENGTH) {
    return baseText;
  }

  const sliced = baseText.slice(0, STICKER_MAX_LENGTH);
  const cutIndex = Math.max(
    sliced.lastIndexOf("，"),
    sliced.lastIndexOf("。"),
    sliced.lastIndexOf("！"),
    sliced.lastIndexOf("？"),
    sliced.lastIndexOf(","),
    sliced.lastIndexOf("."),
    sliced.lastIndexOf("!"),
    sliced.lastIndexOf("?")
  );

  if (cutIndex >= STICKER_MIN_LENGTH - 1) {
    return ensurePunctuation(sliced.slice(0, cutIndex));
  }

  return ensurePunctuation(sliced.slice(0, STICKER_MAX_LENGTH - 1));
}

export function getHomeUpdatePageCount(items = [], pageSize = HOME_UPDATES_PAGE_SIZE) {
  const total = safeList(items).length;
  return total ? Math.ceil(total / pageSize) : 1;
}

export function getHomeUpdatePageItems(items = [], page = 1, pageSize = HOME_UPDATES_PAGE_SIZE) {
  const normalizedItems = safeList(items);
  const pageCount = getHomeUpdatePageCount(normalizedItems, pageSize);
  const safePage = Math.min(Math.max(Number(page || 1), 1), pageCount);
  const start = (safePage - 1) * pageSize;
  return normalizedItems.slice(start, start + pageSize);
}

export function buildStickerText(text) {
  const baseText = stripStickerPrefix(text)
    .replace(/\n+/gu, " ")
    .replace(/(当前|今日)?(数据|记录|热量)(显示|提示|表明)/gu, "")
    .replace(/^(今天|今日)/u, "")
    .replace(/^[，,]\s*/u, "")
    .trim();

  if (!baseText) {
    return DEFAULT_STICKER_TEXT;
  }

  return clampStickerLength(softenSentence(baseText));
}

export function buildStickerLoadingText() {
  return "贴纸正在慢慢贴好...";
}
