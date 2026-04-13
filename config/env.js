const fs = require("fs");
const path = require("path");
const API_BASE_URL_ENV_KEY = "TARO_APP_API_BASE_URL";
const REQUEST_TIMEOUT_ENV_KEY = "TARO_APP_REQUEST_TIMEOUT";
const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_REQUEST_TIMEOUT = 10000;

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
    apiBaseUrl: process.env[API_BASE_URL_ENV_KEY] || envFileValues[API_BASE_URL_ENV_KEY] || DEFAULT_API_BASE_URL,
    requestTimeout: Number(
      process.env[REQUEST_TIMEOUT_ENV_KEY] || envFileValues[REQUEST_TIMEOUT_ENV_KEY] || DEFAULT_REQUEST_TIMEOUT
    )
  };
}

module.exports = {
  API_BASE_URL_ENV_KEY,
  REQUEST_TIMEOUT_ENV_KEY,
  DEFAULT_API_BASE_URL,
  DEFAULT_REQUEST_TIMEOUT,
  loadAppEnv,
};
