const fs = require("fs");
const path = require("path");

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const content = fs.readFileSync(filePath, "utf8");
  const lines = content.split(/\r?\n/);
  const result = {};

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const separatorIndex = line.indexOf("=");
    if (separatorIndex <= 0) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    result[key] = value;
  }

  return result;
}

function loadAppEnv() {
  const rootPath = path.resolve(__dirname, "..");
  const envPath = path.join(rootPath, ".env");
  const envFileValues = parseEnvFile(envPath);

  return {
    apiBaseUrl: process.env.TARO_APP_API_BASE_URL || envFileValues.TARO_APP_API_BASE_URL || "http://127.0.0.1:8000",
    requestTimeout: Number(process.env.TARO_APP_REQUEST_TIMEOUT || envFileValues.TARO_APP_REQUEST_TIMEOUT || 10000),
  };
}

module.exports = {
  loadAppEnv,
};
