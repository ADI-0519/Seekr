export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export const FIREBASE_CONFIG = {
    apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY || '',
    authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN || '',
    projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID || '',
    appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID || '',
};

export const GOOGLE_AUTH_CONFIG = {
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || '',
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID || '',
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID || '',
    expoClientId: process.env.EXPO_PUBLIC_GOOGLE_EXPO_CLIENT_ID || '',
};

export const APP_CONFIG = {
    name: 'Seekr',
    tagline: 'Find any moment in your lectures',
    version: '1.0.0',
};

export const FEATURES = {
    enableMockData: process.env.EXPO_PUBLIC_ENABLE_MOCK_DATA === 'true',
    enableMockAuth: process.env.EXPO_PUBLIC_ENABLE_MOCK_AUTH === 'true',
    enablePDFExport: true,
    enableLinkUpload: true,
};
