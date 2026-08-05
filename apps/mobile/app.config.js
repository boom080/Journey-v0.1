const variant = process.env.APP_VARIANT || 'development';
const variants = {
  development: {
    name: 'Journey (Dev)',
    identifier: 'com.boom080.journey.dev',
    scheme: 'journey-dev',
  },
  preview: {
    name: 'Journey (Preview)',
    identifier: 'com.boom080.journey.preview',
    scheme: 'journey-preview',
  },
  production: {
    name: 'Journey',
    identifier: 'com.boom080.journey',
    scheme: 'journey',
  },
};

if (!Object.hasOwn(variants, variant)) {
  throw new Error(`APP_VARIANT must be one of: ${Object.keys(variants).join(', ')}`);
}

const selected = variants[variant];
const isDevelopment = variant === 'development';

module.exports = {
  name: selected.name,
  slug: 'journey-mobile',
  version: '0.1.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: selected.scheme,
  userInterfaceStyle: 'automatic',
  ios: {
    icon: './assets/expo.icon',
    bundleIdentifier: selected.identifier,
    buildNumber: '1',
    supportsTablet: true,
  },
  android: {
    package: selected.identifier,
    versionCode: 1,
    adaptiveIcon: {
      backgroundColor: '#E6F4FE',
      foregroundImage: './assets/images/android-icon-foreground.png',
      backgroundImage: './assets/images/android-icon-background.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },
  web: {
    output: 'static',
    favicon: './assets/images/favicon.png',
  },
  plugins: [
    'expo-router',
    ['expo-dev-client', { addGeneratedScheme: isDevelopment }],
    [
      'expo-splash-screen',
      {
        backgroundColor: '#F1FBF6',
        image: './assets/brand/journey-leaf-home.png',
        imageWidth: 160,
      },
    ],
    ['expo-secure-store', { configureAndroidBackup: true }],
    [
      'expo-image-picker',
      {
        photosPermission: '允许 Journey 选择你主动用于饮食估算的照片。',
        cameraPermission: '允许 Journey 拍摄你主动用于饮食估算的照片。',
        microphonePermission: false,
      },
    ],
    [
      'expo-build-properties',
      {
        android: {
          // Local Android emulators reach the development API over 10.0.2.2.
          // Preview and production remain HTTPS-only.
          usesCleartextTraffic: isDevelopment,
        },
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
    reactCompiler: true,
  },
  extra: {
    appVariant: variant,
  },
};
