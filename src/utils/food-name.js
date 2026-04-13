const FOOD_ALIASES = [
  {
    name: "番茄炒蛋",
    patterns: [/(?:番茄|西红柿).{0,8}(?:鸡蛋|蛋)/, /(?:鸡蛋|蛋).{0,8}(?:番茄|西红柿)/]
  },
  {
    name: "鸡蛋羹",
    patterns: [/鸡蛋羹/, /蒸蛋/]
  },
  {
    name: "冰淇淋",
    patterns: [/冰淇淋/, /冰激凌/, /雪糕/]
  },
  {
    name: "蓝莓",
    patterns: [/蓝莓/]
  }
];

const LEADING_DECORATORS = [
  /^(?:我(?:今天|刚刚|刚才)?|今天|刚刚|刚才|现在|中午|晚上|早上|夜里)/,
  /^(?:吃了|喝了|来了一份|来了一碗|来了一盒|点了|买了|做了|整了|蒸了|炒了)/,
  /^(?:一大碗|一碗|一大盒|一盒|一份|一大份|一小份|一盘|一大盘|一杯|一大杯|一小杯|一桶|一个|一块|一根|一串|一整盒|半份|半碗|半盒|超大盒|大份|小份|满满一碗|不少|一些)/,
  /^(?:美味的|好吃的|嫩滑的|香香的|香浓的|新鲜的|热乎的|冰冰凉凉的)/
];

function cleanText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/[，,。；;！!？?]+$/g, "")
    .trim();
}

function stripLeadingDecorators(text) {
  let nextText = cleanText(text);
  let changed = true;

  while (changed) {
    changed = false;

    LEADING_DECORATORS.forEach((pattern) => {
      const replaced = nextText.replace(pattern, "").trim();
      if (replaced !== nextText) {
        nextText = replaced;
        changed = true;
      }
    });
  }

  return nextText.replace(/^的/, "").trim();
}

function stripExplainers(text) {
  return cleanText(text)
    .replace(/^以.+?为主料[，,、]*/g, "")
    .replace(/^由.+?(?:制作|做成|制成)的/g, "")
    .replace(/(?:加水|加入.+?)(?:蒸制|熬制|煮制|炒制|烹制|制作|做成|制成|而成)(?:而成)?的?/g, "")
    .replace(/(?:为主料|炒在一起|做在一起|混在一起)/g, "")
    .trim();
}

function matchAlias(text) {
  const rawText = cleanText(text);
  if (!rawText) {
    return "";
  }

  const matched = FOOD_ALIASES.find((item) => item.patterns.some((pattern) => pattern.test(rawText)));
  return matched?.name || "";
}

function splitCandidates(text) {
  return cleanText(text)
    .split(/[，,。；;、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeCandidate(text) {
  const directAlias = matchAlias(text);
  if (directAlias) {
    return directAlias;
  }

  let nextText = stripLeadingDecorators(stripExplainers(text));

  if (nextText.includes("的") && nextText.length > 4) {
    const tail = cleanText(nextText.split("的").pop());
    if (tail.length >= 2) {
      nextText = tail;
    }
  }

  nextText = nextText.replace(/^(?:大|小|超大|超小|满满|整盒|整份|整碗)/, "").trim();

  const aliasAfterClean = matchAlias(nextText);
  if (aliasAfterClean) {
    return aliasAfterClean;
  }

  return nextText;
}

export function normalizeFoodName(text) {
  const rawText = cleanText(text);
  if (!rawText) {
    return "";
  }

  const directAlias = matchAlias(rawText);
  if (directAlias) {
    return directAlias;
  }

  const candidates = splitCandidates(rawText);
  for (const candidate of candidates) {
    const normalized = normalizeCandidate(candidate);
    if (normalized) {
      return normalized;
    }
  }

  return normalizeCandidate(rawText);
}

export function getFoodDisplayName(record = {}, draftText = "") {
  const candidates = [
    record.confirmed_food_name,
    record.food_name,
    record.display_name,
    record.name,
    record.extra?.food_name,
    record.extra?.display_name,
    record.detail,
    record.title,
    record.content,
    draftText
  ];

  for (const candidate of candidates) {
    const normalized = normalizeFoodName(candidate);
    if (normalized) {
      return normalized;
    }
  }

  return cleanText(record.detail || record.title || draftText || "");
}
