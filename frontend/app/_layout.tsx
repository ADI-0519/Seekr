import { useEffect } from 'react';
import { View, StyleSheet, Platform, LogBox } from 'react-native';
import { Stack } from 'expo-router';
import { AppBackground } from '../src/design/primitives/AppBackground';
import { useFonts } from 'expo-font';
import {
    PlusJakartaSans_400Regular,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
} from '@expo-google-fonts/plus-jakarta-sans';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../src/hooks/useAuth';
import { GlobalVideoPlayer } from '../src/components/player/GlobalVideoPlayer';
import { MiniPlayerShell } from '../src/components/player/MiniPlayerShell';
import { ThemeProvider, useTheme } from '../src/theme/ThemeProvider';
import { ThemeProvider as NavThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { useAuth } from '@/hooks';
import { api } from '@/services';

const queryClient = new QueryClient();

if (Platform.OS !== 'web') {
    LogBox.ignoreLogs(['VirtualizedLists should never be nested']);
}

export default function RootLayout() {
    const [fontsLoaded] = useFonts({
        PlusJakartaSans_400Regular,
        PlusJakartaSans_500Medium,
        PlusJakartaSans_600SemiBold,
        PlusJakartaSans_700Bold,
    });

    useEffect(() => {
        if (Platform.OS !== 'web' || typeof document === 'undefined') return;

        let style = document.getElementById('seekr-animation-styles');
        if (!style) {
            style = document.createElement('style');
            style.id = 'seekr-animation-styles';
            document.head.appendChild(style);
        }

        style.textContent = `
            @keyframes cardStaggerIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pageSlideIn {
                from { opacity: 0; transform: translateY(12px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pageFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @media (prefers-reduced-motion: reduce) {
                * { animation-duration: 0s !important; transition-duration: 0s !important; }
            }
            [data-glass-card="true"] {
                position: relative;
                z-index: 0;
            }
            [data-glass-card="true"]::before {
                content: "";
                position: absolute;
                inset: 0;
                z-index: -1;
                border-radius: inherit;
                backdrop-filter: blur(48px) !important;
                -webkit-backdrop-filter: blur(48px) !important;
                pointer-events: none;
            }
        `;
    }, []);

    if (!fontsLoaded) {
        return null;
    }
    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <ThemeProvider>
                    <AppContent />
                </ThemeProvider>
            </AuthProvider>
        </QueryClientProvider>
    );
}

function AppContent() {
    const { isDark, setMode, setBackgroundStyle, setCardStyle, setVideoAnimation } = useTheme();
    const { user } = useAuth();
    const isPublicSession = !user;

    useEffect(() => {
        let cancelled = false;

        const hydrateSettings = async () => {
            if (!user) return;
            try {
                const response = await api.getUserSettings();
                if (!response.success || cancelled) return;
                setMode(response.data.themeMode);
                setBackgroundStyle(response.data.backgroundMode);
                setCardStyle(response.data.cardStyle);
                setVideoAnimation(response.data.videoAnimation);
            } catch (error) {
                console.warn('[App] Failed to hydrate user settings:', error);
            }
        };

        void hydrateSettings();

        return () => {
            cancelled = true;
        };
    }, [user?.id]);

    useEffect(() => {
        if (!user) {
            setMode('light');
            setBackgroundStyle('animated');
            setCardStyle('solid');
            setVideoAnimation(1);
        }
    }, [user, setMode, setBackgroundStyle, setCardStyle, setVideoAnimation]);

    const bgColor = isPublicSession ? '#F3F8F5' : (isDark ? '#0E1113' : '#F7FAF9');
    const showAppBackground = !isPublicSession;
    const useDarkNavigationTheme = !isPublicSession && isDark;

    const navTheme = {
        ...(useDarkNavigationTheme ? DarkTheme : DefaultTheme),
        colors: {
            ...(useDarkNavigationTheme ? DarkTheme.colors : DefaultTheme.colors),
            background: 'transparent',
        },
    };

        return (
        <View style={styles.container}>
            <View style={[styles.solidBg, { backgroundColor: bgColor }]} />

            {!showAppBackground && <PublicBackground />}

            {showAppBackground && (
                <View style={{ ...StyleSheet.absoluteFillObject, zIndex: 0 }} pointerEvents="none">
                    <AppBackground />
                </View>
            )}

            <View style={{ flex: 1, zIndex: 1 }}>
                <NavThemeProvider value={navTheme}>
                    <Stack screenOptions={{
                        headerShown: false,
                        contentStyle: { backgroundColor: 'transparent' },
                        animation: 'fade',
                        animationDuration: 220,
                        gestureEnabled: true,
                    }}>
                        <Stack.Screen name="(auth)" />
                        <Stack.Screen name="(app)" />
                        <Stack.Screen name="upload" options={{
                            presentation: 'transparentModal',
                            animation: 'fade_from_bottom',
                            animationDuration: 300,
                            gestureEnabled: true,
                            gestureDirection: 'vertical',
                        }} />
                        <Stack.Screen name="+not-found" />
                    </Stack>
                </NavThemeProvider>
            </View>

            {!isPublicSession && (
                <View style={{ ...StyleSheet.absoluteFillObject, zIndex: 2 }} pointerEvents="box-none">
                    <GlobalVideoPlayer />
                    <MiniPlayerShell />
                </View>
            )}
        </View>
    );
}

function PublicBackground() {
    const webMeshEffect =
        Platform.OS === 'web'
            ? ({
                backgroundImage:
                    'radial-gradient(rgba(16, 185, 129, 0.22) 0.8px, transparent 0.8px)',
                backgroundSize: '34px 34px',
                maskImage:
                    'radial-gradient(ellipse at center, rgba(0,0,0,0.68), rgba(0,0,0,0.12) 65%, transparent 100%)',
            } as any)
            : null;

    return (
        <View style={styles.publicBgContainer} pointerEvents="none">
            <View style={styles.publicBaseGradient} />
            <View style={styles.publicGlowTopLeft} />
            <View style={styles.publicGlowTopRight} />
            <View style={styles.publicGlowCenterSoft} />
            <View style={styles.publicGlowBottom} />
            <View style={styles.publicGlassSheetSecondary} />
            <View style={styles.publicGlassSheet} />
            <View style={styles.publicVignette} />
            {Platform.OS === 'web' ? <View style={[styles.publicMeshWeb, webMeshEffect]} /> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    solidBg: {
        ...StyleSheet.absoluteFillObject,
        zIndex: 0,
    },
    publicBgContainer: {
        ...StyleSheet.absoluteFillObject,
        zIndex: 0,
        overflow: 'hidden',
    },
    publicBaseGradient: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: '#F6FBF8',
    },
    publicGlowTopLeft: {
        position: 'absolute',
        width: 760,
        height: 760,
        top: -360,
        left: -300,
        borderRadius: 999,
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        ...(Platform.OS === 'web' ? ({ filter: 'blur(74px)' } as any) : {}),
    },
    publicGlowTopRight: {
        position: 'absolute',
        width: 620,
        height: 620,
        top: -220,
        right: -220,
        borderRadius: 999,
        backgroundColor: 'rgba(45, 212, 191, 0.08)',
        ...(Platform.OS === 'web' ? ({ filter: 'blur(70px)' } as any) : {}),
    },
    publicGlowCenterSoft: {
        position: 'absolute',
        width: 640,
        height: 640,
        top: '22%',
        left: '28%',
        borderRadius: 999,
        backgroundColor: 'rgba(110, 231, 183, 0.09)',
        ...(Platform.OS === 'web' ? ({ filter: 'blur(80px)' } as any) : {}),
    },
    publicGlowBottom: {
        position: 'absolute',
        width: 860,
        height: 860,
        bottom: -620,
        left: '12%',
        borderRadius: 999,
        backgroundColor: 'rgba(5, 150, 105, 0.10)',
        ...(Platform.OS === 'web' ? ({ filter: 'blur(88px)' } as any) : {}),
    },
    publicGlassSheet: {
        position: 'absolute',
        top: '16%',
        right: -100,
        width: 600,
        height: 360,
        borderRadius: 30,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.6)',
        backgroundColor: 'rgba(255,255,255,0.30)',
        transform: [{ rotate: '-9deg' }],
        ...(Platform.OS === 'web'
            ? ({
                backdropFilter: 'blur(32px)',
                WebkitBackdropFilter: 'blur(32px)',
            } as any)
            : {}),
    },
    publicGlassSheetSecondary: {
        position: 'absolute',
        top: '38%',
        left: -150,
        width: 500,
        height: 300,
        borderRadius: 28,
        borderWidth: 1,
        borderColor: 'rgba(255,255,255,0.45)',
        backgroundColor: 'rgba(255,255,255,0.18)',
        transform: [{ rotate: '11deg' }],
        ...(Platform.OS === 'web'
            ? ({
                backdropFilter: 'blur(26px)',
                WebkitBackdropFilter: 'blur(26px)',
            } as any)
            : {}),
    },
    publicVignette: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(6, 24, 18, 0.03)',
    },
    publicMeshWeb: {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        opacity: 0.12,
    },
});
