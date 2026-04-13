const { API_BASE_URL_ENV_KEY, DEFAULT_API_BASE_URL, DEFAULT_REQUEST_TIMEOUT, loadAppEnv } = require("./env");

const appEnv = loadAppEnv();

module.exports = {
  env: {
    NODE_ENV: '"production"'
  },
  defineConstants: {
    __API_BASE_URL__: JSON.stringify(appEnv.apiBaseUrl),
    __REQUEST_TIMEOUT__: JSON.stringify(appEnv.requestTimeout),
    __API_BASE_URL_ENV_KEY__: JSON.stringify(API_BASE_URL_ENV_KEY),
    __DEFAULT_API_BASE_URL__: JSON.stringify(DEFAULT_API_BASE_URL),
    __DEFAULT_REQUEST_TIMEOUT__: JSON.stringify(DEFAULT_REQUEST_TIMEOUT)
  },
  mini: {},
  h5: {}
};
