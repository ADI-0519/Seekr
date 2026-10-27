import React, { useRef, useEffect } from 'react';
import { View, StyleSheet, Image, Pressable, Platform } from 'react-native';
import { Play, Pause, ChevronUp, X } from 'lucide-react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design/index';
import { motion } from '../../design/tokens/motion';
import { useVideoPlayerStore, getRawCurrentTime } from '../../store/videoStore';
import { playerEngine } from '../../player/playerEngine';
import { useBreakpointValue } from '../../hooks/useBreakpoint';
import { useRouter, usePathname } from 'expo-router';
import { useThemeColors } from '../../theme/ThemeProvider';
import { useEntryAnimation } from '../../hooks/useEntryAnimation';

export const MiniPlayerShell: React.FC = () => {
    const { state, activeVideo, togglePlayPause, expandPlayer, closePlayer } = useVideoPlayerStore();
    const router = useRouter();
    const pathname = usePathname();
    const themeColors = useThemeColors();

    const layoutStyle = useBreakpointValue({
        sm: { left: 16, right: 16, bottom: 104 }, // Float above bottom nav
        md: { left: 72 + 32, right: 32, bottom: 24 }, // Icon rail offset
        lg: { left: 240 + 48, right: 40, bottom: 24 }, // Full sidebar offset
        xl: { left: 240 + 48, right: 40, bottom: 24 },
    });

    // Must stay before the early return to preserve hook order.
    const entryStyle = useEntryAnimation({
        direction: 'up',
        duration: motion.durationMedium,
        offset: motion.miniPlayerOffsetY,
    });
    const rectRef = React.useRef<{ left: number; width: number } | null>(null);

    const progressFillRef = useRef<View>(null);
    const progressHandleRef = useRef<View>(null);

    useEffect(() => {
        if (Platform.OS !== 'web' || state !== 'mini' || !activeVideo) return;

        let animFrameId: number;
        const tick = () => {
            const duration = activeVideo.duration;
            if (duration > 0) {
                const pct = (getRawCurrentTime() / duration) * 100;
                const fillEl = (progressFillRef.current as any)?._nativeTag
                    ? undefined // native — skip
                    : (progressFillRef.current as unknown as HTMLElement);
                const handleEl = (progressHandleRef.current as any)?._nativeTag
                    ? undefined
                    : (progressHandleRef.current as unknown as HTMLElement);

                if (fillEl) fillEl.style.width = `${pct}%`;
                if (handleEl) handleEl.style.left = `${pct}%`;
            }
            animFrameId = requestAnimationFrame(tick);
        };
        animFrameId = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(animFrameId);
    }, [state, activeVideo?.lectureId, activeVideo?.duration]);

    const hasSession = !!activeVideo?.lectureId;
    const isOnOwnerRoute = activeVideo?.sourceRoute === pathname || pathname.includes(`/lectures/${activeVideo?.lectureId}`);
    const shouldShowMiniPlayer = hasSession && !isOnOwnerRoute;

    if (!shouldShowMiniPlayer) {
        return null;
    }

    const progress = activeVideo.duration > 0
        ? (activeVideo.currentTime / activeVideo.duration) * 100
        : 0;

    const handleScrub = (event: any) => {
        if (!activeVideo || activeVideo.duration === 0) return;

        let clickX = 0;
        let width = 0;

        if (Platform.OS === 'web') {
            const rect = event.currentTarget.getBoundingClientRect();
            clickX = event.clientX - rect.left;
            width = rect.width;
        } else {
            clickX = event.nativeEvent.locationX;
            width = 300;
        }

        const percentage = Math.max(0, Math.min(1, clickX / width));
        const newTime = percentage * activeVideo.duration;
        playerEngine.seekTo(newTime);
    };

    const handleScrubMouseDown = (event: any) => {
        if (Platform.OS !== 'web') return;
        handleScrub(event);
        const target = event.currentTarget as HTMLElement | null;
        if (!target) return;
        const rect = target.getBoundingClientRect();
        rectRef.current = { left: rect.left, width: rect.width };
        const onMove = (e: MouseEvent) => {
            if (!activeVideo || activeVideo.duration === 0 || !rectRef.current) return;
            const percentage = Math.max(0, Math.min(1, (e.clientX - rectRef.current.left) / rectRef.current.width));
            playerEngine.seekTo(percentage * activeVideo.duration);
        };
        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            rectRef.current = null;
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    };

    const webScrubProps = Platform.OS === 'web'
        ? ({ onMouseDown: handleScrubMouseDown, onClick: handleScrub } as any)
        : {};

    return (
        <View style={[styles.container, layoutStyle, entryStyle]}>
            <FloatingShell
                style={styles.shell}
                padding={12}
                radius="miniPlayer"
                elevation="soft"
            >
                <View style={styles.content}>
                    <Image
                        source={{ uri: activeVideo.thumbnailUrl || 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=100' }}
                        style={[styles.thumbnail, { backgroundColor: themeColors.borderSubtle }]}
                    />

                    <View style={styles.infoArea}>
                        <Pressable onPress={expandPlayer} style={styles.titleArea}>
                            <Typography variant="bodyMd" numberOfLines={1}>
                                {activeVideo.title}
                            </Typography>
                        </Pressable>

                        <View
                            style={Platform.OS === 'web' ? [styles.scrubberHitArea, { cursor: 'pointer' } as any] : styles.scrubberHitArea}
                            onStartShouldSetResponder={() => Platform.OS !== 'web'}
                            onResponderGrant={handleScrub}
                            onResponderMove={handleScrub}
                            {...webScrubProps}
                        >
                            <View style={[styles.progressBarBg, { backgroundColor: themeColors.borderSubtle }]}>
                                <View
                                    ref={progressFillRef}
                                    style={[styles.progressBarFill, { width: `${progress}%`, backgroundColor: themeColors.primaryEmerald }]}
                                />
                                <View
                                    ref={progressHandleRef}
                                    style={[styles.progressHandle, { left: `${progress}%`, borderColor: themeColors.primaryEmerald }]}
                                />
                            </View>
                        </View>
                    </View>

                    <View style={styles.actions}>
                        <Pressable onPress={togglePlayPause} style={styles.actionButton}>
                            {activeVideo.isPlaying ? (
                                <Pause color={themeColors.primaryEmerald} size={20} fill={themeColors.primaryEmerald} />
                            ) : (
                                <Play color={themeColors.primaryEmerald} size={20} fill={themeColors.primaryEmerald} />
                            )}
                        </Pressable>

                        <Pressable onPress={() => {
                            if (activeVideo?.lectureId) {
                                expandPlayer();
                                router.push(`/lectures/${activeVideo.lectureId}`);
                            }
                        }} style={styles.actionButton}>
                            <ChevronUp color={themeColors.textSecondary} size={20} />
                        </Pressable>

                        <Pressable onPress={closePlayer} style={styles.actionButton}>
                            <X color={themeColors.textSecondary} size={18} />
                        </Pressable>
                    </View>
                </View>
            </FloatingShell>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        zIndex: 1000,
    },
    shell: {
        width: '100%',
    },
    content: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    thumbnail: {
        width: 48,
        height: 48,
        borderRadius: 12,
        backgroundColor: theme.colors.borderSubtle,
    },
    infoArea: {
        flex: 1,
        marginHorizontal: theme.spacing[16],
        justifyContent: 'center',
    },
    titleArea: {
        marginBottom: 2,
        paddingVertical: 4,
    },
    scrubberHitArea: {
        paddingVertical: 8, // Increase hit area
        marginVertical: -8, // Offset padding visually
    },
    progressBarBg: {
        height: 4,
        backgroundColor: theme.colors.borderSubtle,
        borderRadius: 2,
        position: 'relative',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: theme.colors.primaryEmerald,
    },
    progressHandle: {
        position: 'absolute',
        top: -6,
        width: 16,
        height: 16,
        borderRadius: 8,
        backgroundColor: theme.colors.surfaceBase,
        borderWidth: 2,
        marginLeft: -8,
    },
    actions: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingRight: theme.spacing[8],
    },
    actionButton: {
        padding: 10,
        marginLeft: 4,
        justifyContent: 'center',
        alignItems: 'center',
    }
});
