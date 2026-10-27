import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Platform, Pressable, Text, View } from 'react-native';
import { Maximize, Pause, Play, Volume2, VolumeX } from 'lucide-react-native';

import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import { TopicSegment } from '@/types';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from '../lectureDetail.styles';
import { ProgressScrubber } from './ProgressScrubber';

type ActiveVideoLike = {
    currentTime: number;
    duration: number;
    playbackRate?: number;
    isPlaying?: boolean;
} | null | undefined;

export const VideoControlsOverlay = ({
    styles,
    lectureDuration,
    topics,
    activeVideo,
    isMobile,
    isHovered,
    isMuted,
    setIsMuted,
    volume,
    setVolume,
    setGlobalVolume,
    onSeek,
    onTogglePlayPause,
    onSetPlaybackRate,
    onFullscreen,
}: {
    styles: LectureDetailStyles;
    lectureDuration: number;
    topics: TopicSegment[];
    activeVideo: ActiveVideoLike;
    isMobile: boolean;
    isHovered: boolean;
    isMuted: boolean;
    setIsMuted: (v: boolean) => void;
    volume: number;
    setVolume: (v: number) => void;
    setGlobalVolume: (v: number) => void;
    onSeek: (t: number) => void;
    onTogglePlayPause: () => void;
    onSetPlaybackRate: (rate: number) => void;
    onFullscreen: () => void;
}) => {
    const themeColors = useThemeColors();
    const [speedMenuVisible, setSpeedMenuVisible] = useState(false);
    const [isVolumeHovered, setIsVolumeHovered] = useState(false);

    useEffect(() => {
        if (!isHovered) setSpeedMenuVisible(false);
    }, [isHovered]);

    const timeTextRef = useRef<Text>(null);

    const volumeTo = useCallback(
        (x: number, width: number) => {
            if (!width) return;
            const adjustedX = x - 8;
            const innerWidth = width - 16;
            const percentage = innerWidth > 0 ? Math.max(0, Math.min(1, adjustedX / innerWidth)) : 0;

            setVolume(percentage);
            setGlobalVolume(percentage);
            setIsMuted(percentage <= 0);
        },
        [setGlobalVolume, setIsMuted, setVolume]
    );


    const handleVolumePress = (event: any) => {
        const width = 76;
        const x =
            Platform.OS === 'web'
                ? event.clientX - event.currentTarget.getBoundingClientRect().left
                : event.nativeEvent.locationX;
        volumeTo(x, width);
    };

    const volumeRectRef = useRef<{ left: number; width: number } | null>(null);

    const handleVolumeMouseDown = (event: any) => {
        if (Platform.OS !== 'web') return;
        handleVolumePress(event);
        const target = event.currentTarget as HTMLElement | null;
        if (!target) return;
        const rect = target.getBoundingClientRect();
        volumeRectRef.current = { left: rect.left, width: rect.width };
        const onMove = (e: MouseEvent) => {
            if (!volumeRectRef.current) return;
            volumeTo(e.clientX - volumeRectRef.current.left, volumeRectRef.current.width);
        };
        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            volumeRectRef.current = null;
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    };

    const webVolumeProps =
        Platform.OS === 'web' ? ({ onMouseDown: handleVolumeMouseDown, onClick: handleVolumePress } as any) : {};

    const toggleMute = () => setIsMuted(!isMuted);
    const stopAndRun = useCallback((event: any, action: () => void) => {
        event?.stopPropagation?.();
        action();
    }, []);

    return (
        <View
            style={[
                styles.controlsBar,
                isMobile && (styles.controlsBarMobile as any),
                Platform.OS === 'web' &&
                    ({
                        opacity: isHovered ? 1 : 0,
                        transition: 'opacity 300ms ease-in-out',
                        pointerEvents: isHovered ? 'auto' : 'none',
                    } as any),
            ]}
        >
            {isMobile ? (
                <>
                    <View style={styles.controlsCenterMobile}>
                        <ProgressScrubber
                            styles={styles}
                            lectureDuration={lectureDuration}
                            topics={topics}
                            activeVideo={activeVideo}
                            onSeek={onSeek}
                            timeTextRef={timeTextRef}
                        />
                    </View>
                    <View style={styles.controlsBottomRowMobile}>
                        <View style={styles.controlsLeftMobile}>
                            <Pressable onPress={(e) => stopAndRun(e, onTogglePlayPause)} style={styles.controlButton}>
                                {activeVideo?.isPlaying ? (
                                    <Pause color="#FFFFFF" size={20} fill="#FFFFFF" />
                                ) : (
                                    <Play color="#FFFFFF" size={20} fill="#FFFFFF" />
                                )}
                            </Pressable>

                            <Typography ref={timeTextRef as any} variant="meta" color="#FFFFFF" style={styles.timeText}>
                                {formatDuration(activeVideo?.currentTime)} / {formatDuration(activeVideo?.duration)}
                            </Typography>
                        </View>

                        <View style={styles.controlsRightMobile}>
                            <Pressable
                                onPress={(e) => stopAndRun(e, () => setSpeedMenuVisible(!speedMenuVisible))}
                                style={styles.speedButton}
                            >
                                <Typography variant="meta" color="#FFFFFF" style={styles.speedButtonText}>
                                    {activeVideo?.playbackRate || 1}x
                                </Typography>
                            </Pressable>

                            <Pressable onPress={(e) => stopAndRun(e, onFullscreen)} style={styles.controlButton}>
                                <Maximize color="#FFFFFF" size={20} />
                            </Pressable>
                        </View>
                    </View>
                </>
            ) : (
                <>
                    <View style={styles.controlsLeft}>
                        <Pressable onPress={(e) => stopAndRun(e, onTogglePlayPause)} style={styles.controlButton}>
                            {activeVideo?.isPlaying ? (
                                <Pause color="#FFFFFF" size={20} fill="#FFFFFF" />
                            ) : (
                                <Play color="#FFFFFF" size={20} fill="#FFFFFF" />
                            )}
                        </Pressable>

                        <View
                            style={styles.volumeContainer}
                            {...(Platform.OS === 'web'
                                ? {
                                      onMouseEnter: () => setIsVolumeHovered(true),
                                      onMouseLeave: () => setIsVolumeHovered(false),
                                  }
                                : {})}
                        >
                            <Pressable onPress={(e) => stopAndRun(e, toggleMute)} style={[styles.controlButton, { marginRight: 8 }]}>
                                {isMuted || volume === 0 ? (
                                    <VolumeX color="#FFFFFF" size={20} />
                                ) : (
                                    <Volume2 color="#FFFFFF" size={20} />
                                )}
                            </Pressable>

                            <View
                                style={[
                                    styles.volumeSliderHitArea,
                                    Platform.OS === 'web' && {
                                        width: isVolumeHovered ? 76 : 0,
                                        opacity: isVolumeHovered ? 1 : 0,
                                        marginRight: isVolumeHovered ? 8 : 0,
                                        overflow: 'hidden',
                                        transition:
                                            'width 200ms ease-out, opacity 200ms ease-out, margin-right 200ms ease-out',
                                        cursor: 'pointer' as any,
                                    },
                                ]}
                                onStartShouldSetResponder={() => Platform.OS !== 'web'}
                                onResponderGrant={(e) => volumeTo(e.nativeEvent.locationX, 76)}
                                onResponderMove={(e) => volumeTo(e.nativeEvent.locationX, 76)}
                                {...webVolumeProps}
                            >
                                <View style={styles.volumeBarBg}>
                                    <View
                                        style={[
                                            styles.volumeBarFill,
                                            {
                                                width: `${(isMuted ? 0 : volume) * 100}%`,
                                                backgroundColor: themeColors.primaryEmerald,
                                            },
                                        ]}
                                    />
                                    <View
                                        style={[
                                            styles.volumeHandle,
                                            {
                                                left: `${(isMuted ? 0 : volume) * 100}%`,
                                                borderColor: themeColors.primaryEmerald,
                                            },
                                        ]}
                                    />
                                </View>
                            </View>
                        </View>

                        <Typography ref={timeTextRef as any} variant="meta" color="#FFFFFF" style={styles.timeText}>
                            {formatDuration(activeVideo?.currentTime)} / {formatDuration(activeVideo?.duration)}
                        </Typography>
                    </View>

                    <View style={styles.controlsCenter}>
                        <ProgressScrubber
                            styles={styles}
                            lectureDuration={lectureDuration}
                            topics={topics}
                            activeVideo={activeVideo}
                            onSeek={onSeek}
                            timeTextRef={timeTextRef}
                        />
                    </View>

                    <View style={styles.controlsRight}>
                        <Pressable onPress={(e) => stopAndRun(e, () => setSpeedMenuVisible(!speedMenuVisible))} style={styles.speedButton}>
                            <Typography variant="meta" color="#FFFFFF" style={styles.speedButtonText}>
                                {activeVideo?.playbackRate || 1}x
                            </Typography>
                        </Pressable>

                        <Pressable onPress={(e) => stopAndRun(e, onFullscreen)} style={styles.controlButton}>
                            <Maximize color="#FFFFFF" size={20} />
                        </Pressable>
                    </View>
                </>
            )}

            {speedMenuVisible && (
                <View
                    style={[
                        styles.speedMenu,
                        { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle },
                    ]}
                >
                    {[1, 1.25, 1.5, 2].map((rate) => (
                        <Pressable
                            key={rate}
                            style={[
                                styles.speedMenuItem,
                                activeVideo?.playbackRate === rate && styles.speedMenuItemActive,
                                activeVideo?.playbackRate === rate && { backgroundColor: themeColors.chipBgReady },
                            ]}
                            onPress={(e) => stopAndRun(e, () => {
                                onSetPlaybackRate(rate);
                                setSpeedMenuVisible(false);
                            })}
                        >
                            <Typography
                                variant="bodyMd"
                                style={{ fontWeight: activeVideo?.playbackRate === rate ? '600' : '400' }}
                            >
                                {rate}x
                            </Typography>
                        </Pressable>
                    ))}
                </View>
            )}
        </View>
    );
};
