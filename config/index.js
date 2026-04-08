const config = {
  projectName: "journey-miniapp",
  date: "2026-04-07",
  designWidth(input) {
    if (input && input.file) {
      return 750;
    }

    return 750;
  },
  deviceRatio: {
    640: 2.34 / 2,
    750: 1,
    828: 1.81 / 2
  },
  sourceRoot: "src",
  outputRoot: "dist",
  framework: "react",
  compiler: "webpack5",
  cache: {
    enable: true
  },
  mini: {
    postcss: {
      pxtransform: {
        enable: true,
        config: {}
      },
      url: {
        enable: true,
        config: {
          limit: 1024
        }
      },
      cssModules: {
        enable: false
      }
    }
  },
  h5: {
    publicPath: "/",
    staticDirectory: "static"
  }
};

module.exports = function (merge) {
  const baseConfig = config;

  if (process.env.NODE_ENV === "development") {
    return merge({}, baseConfig, require("./dev"));
  }

  return merge({}, baseConfig, require("./prod"));
};
