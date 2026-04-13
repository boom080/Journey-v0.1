import { safeList } from "./day";

export const JOURNEY_PAGE_SIZE = 5;

function toPageSize(value) {
  const size = Number(value || JOURNEY_PAGE_SIZE);
  return Number.isFinite(size) && size > 0 ? size : JOURNEY_PAGE_SIZE;
}

function chunkDays(items, pageSize = JOURNEY_PAGE_SIZE) {
  const normalizedSize = toPageSize(pageSize);
  const days = safeList(items);
  const pages = [];

  for (let index = 0; index < days.length; index += normalizedSize) {
    pages.push(days.slice(index, index + normalizedSize));
  }

  return pages;
}

function flattenPages(pages) {
  return safeList(pages).flatMap((page) => safeList(page));
}

function normalizeCurrentPage(currentPage, pagesLength) {
  if (!pagesLength) {
    return 1;
  }

  const page = Number(currentPage || 1);
  if (!Number.isFinite(page) || page < 1) {
    return 1;
  }

  return Math.min(page, pagesLength);
}

function dateDistance(a, b) {
  if (!a || !b) {
    return Number.MAX_SAFE_INTEGER;
  }

  return Math.abs(new Date(a).getTime() - new Date(b).getTime());
}

export function createJourneyBrowser(cache = {}, pageSize = JOURNEY_PAGE_SIZE) {
  const normalizedPageSize = toPageSize(pageSize);
  const cachedPages = safeList(cache.pages);
  const pages = cachedPages.length ? cachedPages.map((page) => safeList(page)) : chunkDays(cache.items, normalizedPageSize);

  return {
    items: flattenPages(pages),
    pages,
    nextCursor: cache.nextCursor || "",
    hasMore: Boolean(cache.hasMore),
    currentPage: normalizeCurrentPage(cache.currentPage, pages.length),
    pageSize: normalizedPageSize
  };
}

export function createJourneyBrowserFromPayload(payload = {}, pageSize = JOURNEY_PAGE_SIZE) {
  const normalizedPageSize = toPageSize(pageSize);
  const firstPage = safeList(payload.items);
  const pages = firstPage.length ? [firstPage] : [];

  return {
    items: flattenPages(pages),
    pages,
    nextCursor: payload.next_cursor || "",
    hasMore: Boolean(payload.has_more),
    currentPage: pages.length ? 1 : 1,
    pageSize: normalizedPageSize
  };
}

export function appendJourneyBrowserPage(browser = {}, payload = {}) {
  const nextPage = safeList(payload.items);
  const pages = nextPage.length ? [...safeList(browser.pages), nextPage] : [...safeList(browser.pages)];
  const currentPage = nextPage.length ? pages.length : browser.currentPage || 1;

  return {
    ...browser,
    items: flattenPages(pages),
    pages,
    nextCursor: payload.next_cursor || "",
    hasMore: Boolean(payload.has_more),
    currentPage
  };
}

export function setJourneyCurrentPage(browser = {}, currentPage = 1) {
  return {
    ...browser,
    currentPage: normalizeCurrentPage(currentPage, safeList(browser.pages).length)
  };
}

export function getJourneyVisibleDays(browser = {}) {
  const pageIndex = normalizeCurrentPage(browser.currentPage, safeList(browser.pages).length) - 1;
  return safeList(browser.pages)[pageIndex] || [];
}

export function getJourneyTotalPages(browser = {}) {
  return browser.hasMore ? 0 : safeList(browser.pages).length;
}

export function findJourneyPageByDate(browser = {}, targetDate = "") {
  const pages = safeList(browser.pages);

  for (let index = 0; index < pages.length; index += 1) {
    if (safeList(pages[index]).some((item) => String(item?.record_date || item?.id || "") === targetDate)) {
      return index + 1;
    }
  }

  return 0;
}

export function getOldestLoadedJourneyDate(browser = {}) {
  const items = safeList(browser.items);
  const oldestItem = items[items.length - 1];
  return String(oldestItem?.record_date || oldestItem?.id || "");
}

export function shouldFetchMoreForDate(browser = {}, targetDate = "") {
  if (!browser.hasMore || !targetDate) {
    return false;
  }

  const oldestLoadedDate = getOldestLoadedJourneyDate(browser);
  if (!oldestLoadedDate) {
    return true;
  }

  return targetDate < oldestLoadedDate;
}

export function findClosestJourneyPage(browser = {}, targetDate = "") {
  const pages = safeList(browser.pages);

  if (!pages.length) {
    return 1;
  }

  let closestPage = 1;
  let closestDistance = Number.MAX_SAFE_INTEGER;

  pages.forEach((page, pageIndex) => {
    safeList(page).forEach((item) => {
      const recordDate = String(item?.record_date || item?.id || "");
      const nextDistance = dateDistance(recordDate, targetDate);

      if (nextDistance < closestDistance) {
        closestDistance = nextDistance;
        closestPage = pageIndex + 1;
      }
    });
  });

  return closestPage;
}
