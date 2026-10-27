import React, { useEffect, useState } from 'react';
import { AnimatedPage } from '../../src/design/primitives/AnimatedPage';
import { View, StyleSheet, ScrollView, Switch, Pressable } from 'react-native';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { SectionHeader } from '../../src/design/primitives/SectionHeader';
import { Typography } from '../../src/components/ui/Typography';
import { theme } from '../../src/design/index';
import { Moon, Shield, HardDrive, Layers, Sparkles, Film, ChevronLeft, ChevronRight } from 'lucide-react-native';
import { useTheme, useThemeColors } from '../../src/theme/ThemeProvider';
import { api } from '../../src/services';
import { ROUTES } from '@/constants/routes';
import { useRouter } from 'expo-router';
import { PreferenceRow } from '@/components/settings/PreferenceRow';
import { UserSettings } from '@/types';

export default function SettingsScreen() {
    const [settingsState, setSettingsState] = useState<UserSettings | null>(null);
    const [settingsLoaded, setSettingsLoaded] = useState(false);
    const router = useRouter();
    const { isDark, setMode, cardStyle, setCardStyle, backgroundStyle, setBackgroundStyle, videoAnimation, setVideoAnimation, cycleVideoAnimation } = useTheme();
    const themeColors = useThemeColors();

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            try {
                const response = await api.getUserSettings();
                if (!response.success || cancelled) return;
                const settings = response.data;
                setMode(settings.themeMode);
                setBackgroundStyle(settings.backgroundMode);
                setCardStyle(settings.cardStyle);
                setVideoAnimation(settings.videoAnimation);
                setSettingsState(settings);
            } catch (error) {
                console.warn('[Settings] Failed to load user settings:', error);
            } finally {
                if (!cancelled) setSettingsLoaded(true);
            }
        };
        void load();
        return () => {
            cancelled = true;
        };
    }, []);

    const persistSettings = async (patch: Partial<{
        themeMode: 'light' | 'dark';
        backgroundMode: 'animated' | 'static';
        cardStyle: 'solid' | 'transparent';
        videoAnimation: 1 | 2 | 3 | 4 | 5 | 6 | 7;
        autoplayNext: boolean;
        pauseOnLeave: boolean;
        volumeDefault: number;
        mutedDefault: boolean;
        preferredLanguage: string;
        timezone: string | null;
    }>) => {
        if (!settingsLoaded) return;
        if (!settingsState) return;
        const nextSettings: UserSettings = {
            ...settingsState,
            ...patch,
        };
        setSettingsState(nextSettings);
        try {
            await api.updateUserSettings(nextSettings);
        } catch (error) {
            setSettingsState(settingsState);
            console.warn('[Settings] Failed to save user settings:', error);
        }
    };

    const autoplay = settingsState?.autoplayNext ?? true;
    const pauseOnLeave = settingsState?.pauseOnLeave ?? true;

    return (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
            <AnimatedPage style={styles.innerContent}>
                <View style={styles.header}>
                    <Typography variant="displayMd" color={themeColors.textPrimary}>
                        Settings
                    </Typography>
                </View>

                <View style={styles.content}>
                    <FloatingShell padding={32} style={styles.sectionShell}>
                        <SectionHeader title="Appearance" />
                        <View style={styles.settingList}>
                            <PreferenceRow
                                icon={Moon}
                                title="Dark Mode"
                                subtitle="Switch between light and dark themes"
                                trailing={
                                    <Switch
                                        value={isDark}
                                        onValueChange={(value) => {
                                            const mode = value ? 'dark' : 'light';
                                            setMode(mode);
                                            void persistSettings({ themeMode: mode });
                                        }}
                                        trackColor={{ false: themeColors.borderSubtle, true: themeColors.primaryEmerald }}
                                    />
                                }
                            />
                            <View style={[styles.rowDivider, { backgroundColor: themeColors.borderSubtle }]} />
                            <PreferenceRow
                                icon={Layers}
                                title="Card Style"
                                subtitle={cardStyle === 'transparent' ? 'Transparent (glass blur)' : 'Solid (opaque surfaces)'}
                                trailing={
                                    <Switch
                                        value={cardStyle === 'transparent'}
                                        onValueChange={(value) => {
                                            const next = value ? 'transparent' : 'solid';
                                            setCardStyle(next);
                                            void persistSettings({ cardStyle: next });
                                        }}
                                        trackColor={{ false: themeColors.borderSubtle, true: themeColors.primaryEmerald }}
                                    />
                                }
                            />
                            <View style={[styles.rowDivider, { backgroundColor: themeColors.borderSubtle }]} />
                            <PreferenceRow
                                icon={Film}
                                title="Animation Style"
                                subtitle={`Animation ${videoAnimation} of 7`}
                                trailing={
                                    <View style={styles.animationPicker}>
                                        <Pressable
                                            onPress={() => {
                                                const next = ((videoAnimation <= 1 ? 7 : videoAnimation - 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7);
                                                cycleVideoAnimation('prev');
                                                void persistSettings({ videoAnimation: next });
                                            }}
                                            style={({ pressed }) => [
                                                styles.arrowButton,
                                                { backgroundColor: themeColors.surfaceElevated },
                                                pressed && { opacity: 0.6 },
                                            ]}
                                        >
                                            <ChevronLeft color={themeColors.textPrimary} size={18} />
                                        </Pressable>
                                        <Typography variant="bodyLg" color={themeColors.textPrimary} style={{ minWidth: 24, textAlign: 'center' }}>
                                            {videoAnimation}
                                        </Typography>
                                        <Pressable
                                            onPress={() => {
                                                const next = ((videoAnimation >= 7 ? 1 : videoAnimation + 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7);
                                                cycleVideoAnimation('next');
                                                void persistSettings({ videoAnimation: next });
                                            }}
                                            style={({ pressed }) => [
                                                styles.arrowButton,
                                                { backgroundColor: themeColors.surfaceElevated },
                                                pressed && { opacity: 0.6 },
                                            ]}
                                        >
                                            <ChevronRight color={themeColors.textPrimary} size={18} />
                                        </Pressable>
                                    </View>
                                }
                            />
                            <View style={[styles.rowDivider, { backgroundColor: themeColors.borderSubtle }]} />
                            <PreferenceRow
                                icon={Sparkles}
                                title="Background Effects"
                                subtitle={backgroundStyle === 'animated' ? 'Animated (higher GPU usage)' : 'Static (performance mode)'}
                                trailing={
                                    <Switch
                                        value={backgroundStyle === 'animated'}
                                        onValueChange={(value) => {
                                            const mode = value ? 'animated' : 'static';
                                            setBackgroundStyle(mode);
                                            void persistSettings({ backgroundMode: mode });
                                        }}
                                        trackColor={{ false: themeColors.borderSubtle, true: themeColors.primaryEmerald }}
                                    />
                                }
                            />
                        </View>
                    </FloatingShell>

                    <FloatingShell padding={32} style={styles.sectionShell}>
                        <SectionHeader title="Playback" />
                        <View style={styles.settingList}>
                            <PreferenceRow
                                icon={HardDrive}
                                title="Autoplay Next"
                                subtitle="Automatically play the next lecture segment"
                                trailing={
                                    <Switch
                                        value={autoplay}
                                        onValueChange={(value) => {
                                            void persistSettings({ autoplayNext: value });
                                        }}
                                        trackColor={{ false: themeColors.borderSubtle, true: themeColors.primaryEmerald }}
                                    />
                                }
                            />
                            <View style={[styles.rowDivider, { backgroundColor: themeColors.borderSubtle }]} />
                            <PreferenceRow
                                icon={Film}
                                title="Pause When Leaving Lecture"
                                subtitle="Pause playback when you leave the lecture page"
                                trailing={
                                    <Switch
                                        value={pauseOnLeave}
                                        onValueChange={(value) => {
                                            void persistSettings({ pauseOnLeave: value });
                                        }}
                                        trackColor={{ false: themeColors.borderSubtle, true: themeColors.primaryEmerald }}
                                    />
                                }
                            />
                        </View>
                    </FloatingShell>

                    <FloatingShell padding={32} style={styles.sectionShell}>
                        <SectionHeader title="Privacy & Data" />
                        <View style={styles.settingList}>
                            <PreferenceRow
                                icon={Shield}
                                title="Privacy Policy"
                                onPress={() => { router.push(ROUTES.PRIVACY_POLICY); }}
                                trailing={
                                    <ChevronRight color={themeColors.textSecondary} size={16} />
                                }
                            />
                        </View>
                    </FloatingShell>


                </View>
            </AnimatedPage>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scroll: {
        paddingBottom: 100,
    },
    innerContent: {
        paddingTop: 34,
        paddingHorizontal: 16,
        overflow: 'visible',
    },
    header: {
        marginBottom: 40,
    },
    content: {
        maxWidth: 720,
        gap: 24,
        overflow: 'visible',
    },
    sectionShell: {},
    settingList: {
        marginTop: 16,
    },
    rowDivider: {
        height: 1,
        marginLeft: 56, // aligned to text start
    },
    animationPicker: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    arrowButton: {
        width: 34,
        height: 34,
        borderRadius: 17,
        alignItems: 'center',
        justifyContent: 'center',
    },
});
