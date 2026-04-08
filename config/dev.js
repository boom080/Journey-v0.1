const { loadAppEnv } = require("./env");

const appEnv = loadAppEnv();

module.exports = {
  env: {
    NODE_ENV: '"development"'
  },
  defineConstants: {
    __API_BASE_URL__: JSON.stringify(appEnv.apiBaseUrl),
    __REQUEST_TIMEOUT__: JSON.stringify(appEnv.requestTimeout)
  },
  mini: {},
  h5: {}
};
