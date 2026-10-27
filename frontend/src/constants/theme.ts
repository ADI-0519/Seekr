export type ThemeMode = 'light' | 'dark';

export const LightColors = {
    primary: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
    },

    surface: {
        white: '#ffffff',
        50: '#fafafa',
        100: '#f5f5f5',
        200: '#e5e5e5',
        300: '#d4d4d4',
        400: '#a3a3a3',
        500: '#737373',
        600: '#525252',
        700: '#404040',
        800: '#262626',
        900: '#171717',
    },

    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
};

export type ThemeColors = typeof LightColors;

export const DarkColors = {
    primary: {
        50: '#0b2a22',
        100: '#0d3328',
        200: '#0f3d30',
        300: '#11553f',
        400: '#137a57',
        500: '#10b981',
        600: '#34d399',
        700: '#6ee7b7',
        800: '#a7f3d0',
        900: '#d1fae5',
    },
    surface: {
        white: '#0b0c0f',
        50: '#0f1115',
        100: '#14171c',
        200: '#1b2026',
        300: '#27303a',
        400: '#3b4654',
        500: '#637085',
        600: '#9aa5b1',
        700: '#c4ccd6',
        800: '#e1e6ed',
        900: '#f5f7fa',
    },
    success: '#34d399',
    warning: '#fbbf24',
    error: '#f87171',
    info: '#60a5fa',
};

export const Colors = LightColors;

export const Spacing = {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    '2xl': 48,
    '3xl': 64,
};

export const FontSize = {
    xs: 12,
    sm: 14,
    base: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
};

export const BorderRadius = {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,
    xl: 16,
    '2xl': 24,
    full: 9999,
};
