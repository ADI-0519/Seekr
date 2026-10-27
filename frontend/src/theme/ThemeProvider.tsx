import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { Platform } from 'react-native';

export type ThemeMode = 'light' | 'dark';
export type CardStyle = 'solid' | 'transparent';
export type BackgroundStyle = 'animated' | 'static';
export type VideoAnimation = 1 | 2 | 3 | 4 | 5 | 6 | 7;
export const VIDEO_ANIMATION_COUNT = 7;

interface ThemeContextValue {
    mode: ThemeMode;
    isDark: boolean;
    cardStyle: CardStyle;
    backgroundStyle: BackgroundStyle;
    videoAnimation: VideoAnimation;
    toggleMode: () => void;
    setMode: (mode: ThemeMode) => void;
    toggleCardStyle: () => void;
    setCardStyle: (style: CardStyle) => void;
    toggleBackgroundStyle: () => void;
    setBackgroundStyle: (style: BackgroundStyle) => void;
    setVideoAnimation: (v: VideoAnimation) => void;
    cycleVideoAnimation: (direction: 'next' | 'prev') => void;
}

const ThemeContext = createContext<ThemeContextValue>({
    mode: 'light',
    isDark: false,
    cardStyle: 'solid',
    backgroundStyle: 'animated',
    videoAnimation: 1,
    toggleMode: () => { },
    setMode: () => { },
    toggleCardStyle: () => { },
    setCardStyle: () => { },
    toggleBackgroundStyle: () => { },
    setBackgroundStyle: () => { },
    setVideoAnimation: () => { },
    cycleVideoAnimation: () => { },
});

const DARK_CSS = `
  [data-theme="dark"] {
    --color-app-bg: #0F1A1C;
    --color-surface-base: #1A2B2E;
    --color-surface-elevated: #1E3235;
    --color-text-primary: #E8F5F0;
    --color-text-secondary: #94A8AC;
    --color-border-subtle: #2A3D40;
    --color-chip-bg-ready: #0D2818;
    --color-chip-bg-processing: #0D1B2A;
    --color-chip-bg-failed: #2A0D0D;
    --color-solid-bg: #0A1214;
  }

  [data-theme="light"] {
    --color-app-bg: #EBF8F1;
    --color-surface-base: #FFFFFF;
    --color-surface-elevated: #FAFFFE;
    --color-text-primary: #1A2B2E;
    --color-text-secondary: #6B7C80;
    --color-border-subtle: #E2EDE8;
    --color-chip-bg-ready: #ECFDF5;
    --color-chip-bg-processing: #EFF6FF;
    --color-chip-bg-failed: #FEF2F2;
    --color-solid-bg: #EBF8F1;
  }
`;

function injectDarkModeCSS() {
    if (Platform.OS !== 'web') return;
    if (document.getElementById('seekr-dark-mode-css')) return;
    const style = document.createElement('style');
    style.id = 'seekr-dark-mode-css';
    style.textContent = DARK_CSS;
    document.head.appendChild(style);
}

function setDocumentTheme(mode: ThemeMode) {
    if (Platform.OS !== 'web') return;
    document.documentElement.setAttribute('data-theme', mode);
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [mode, setModeState] = useState<ThemeMode>('light');
    const [cardStyle, setCardStyleState] = useState<CardStyle>('solid');
    const [backgroundStyle, setBackgroundStyleState] = useState<BackgroundStyle>('animated');
    const [videoAnimation, setVideoAnimationState] = useState<VideoAnimation>(1);

    useEffect(() => {
        injectDarkModeCSS();
        setDocumentTheme(mode);
    }, [mode]);

    const toggleMode = useCallback(() => {
        setModeState(prev => prev === 'light' ? 'dark' : 'light');
    }, []);

    const setMode = useCallback((m: ThemeMode) => {
        setModeState(m);
    }, []);

    const toggleCardStyle = useCallback(() => {
        setCardStyleState(prev => prev === 'solid' ? 'transparent' : 'solid');
    }, []);

    const setCardStyle = useCallback((style: CardStyle) => {
        setCardStyleState(style);
    }, []);

    const toggleBackgroundStyle = useCallback(() => {
        setBackgroundStyleState(prev => prev === 'animated' ? 'static' : 'animated');
    }, []);

    const setBackgroundStyle = useCallback((style: BackgroundStyle) => {
        setBackgroundStyleState(style);
    }, []);

    const setVideoAnimation = useCallback((v: VideoAnimation) => {
        setVideoAnimationState(v);
    }, []);

    const cycleVideoAnimation = useCallback((direction: 'next' | 'prev') => {
        setVideoAnimationState(prev => {
            if (direction === 'next') return (prev >= VIDEO_ANIMATION_COUNT ? 1 : prev + 1) as VideoAnimation;
            return (prev <= 1 ? VIDEO_ANIMATION_COUNT : prev - 1) as VideoAnimation;
        });
    }, []);

    return (
        <ThemeContext.Provider value={{
            mode,
            isDark: mode === 'dark',
            cardStyle,
            backgroundStyle,
            videoAnimation,
            toggleMode,
            setMode,
            toggleCardStyle,
            setCardStyle,
            toggleBackgroundStyle,
            setBackgroundStyle,
            setVideoAnimation,
            cycleVideoAnimation,
        }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => useContext(ThemeContext);

export const darkColors = {
    appBg: '#0F1A1C',
    surfaceBase: '#1A2B2E',
    surfaceElevated: '#1E3235',
    textPrimary: '#E8F5F0',
    textSecondary: '#94A8AC',
    borderSubtle: '#2A3D40',
    chipBgReady: '#0D2818',
    chipBgProcessing: '#0D1B2A',
    chipBgFailed: '#2A0D0D',
};

export const useThemeColors = () => {
    const { isDark } = useTheme();
    const { colors } = require('../design/index').theme;

    if (!isDark) return colors;

    return {
        ...colors,
        appBg: darkColors.appBg,
        surfaceBase: darkColors.surfaceBase,
        surfaceElevated: darkColors.surfaceElevated,
        textPrimary: darkColors.textPrimary,
        textSecondary: darkColors.textSecondary,
        borderSubtle: darkColors.borderSubtle,
        chipBgReady: darkColors.chipBgReady,
        chipBgProcessing: darkColors.chipBgProcessing,
        chipBgFailed: darkColors.chipBgFailed,
    };
};
