import React, { useEffect, useRef, useState } from 'react';
import { Image, Platform, Pressable, StyleSheet, View } from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { useIsFocused } from '@react-navigation/native';
import { usePathname } from 'expo-router';
import { FileText, Play } from 'lucide-react-native';

import { FloatingShell } from '@/design/primitives/FloatingShell';
import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import { useBreakpointValue } from '@/hooks/useBreakpoint';
import { useVideoPlayer } from '@/hooks';
import { playerEngine } from '@/player/playerEngine';
import { Lecture, TopicSegment } from '@/types';
import type { LectureDetailStyles } from './lectureDetail.styles';

import { VideoControlsOverlay } from './video/VideoControlsOverlay';

export const VideoPlayerSurface = React.memo(({
    lecture,
    topics = [],
    fullscreenPanelLabel = 'Panel',
    renderFullscreenPanel,
    onFullscreenChange,
    styles,
}: {
    lecture: Lecture;
    topics?: TopicSegment[];
    fullscreenPanelLabel?: string;
    renderFullscreenPanel?: ((onCollapse: () => void) => React.ReactNode) | null;
    onFullscreenChange?: (isFullscreen: boolean) => void;
    styles: LectureDetailStyles;
}) => {
    const {
        activeVideo,
        updateTime,
        updateDuration,
        updatePlayState,
        togglePlayPause,
        seekTo,
        setPlaybackRate,
        claimEngine,
        releaseEngine,
        setVolume: setGlobalVolume,
    } = useVideoPlayer();

    const isFocused = useIsFocused();
    const pathname = usePathname();
    const [isMuted, setIsMuted] = useState(false);
    const [volume, setVolume] = useState(1);
    const [isHovered, setIsHovered] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isFullscreenPanelCollapsed, setIsFullscreenPanelCollapsed] = useState(true);

    const themeColors = useThemeColors();
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });

    const canShowFullscreenPanel = Platform.OS === 'web' && isFullscreen && !!renderFullscreenPanel;
    const showExpandedFullscreenPanel = canShowFullscreenPanel && !isFullscreenPanelCollapsed;
    const fullscreenPanelWidth = showExpandedFullscreenPanel ? 420 : 0;

    useEffect(() => {
        if (isFullscreen) {
            setIsFullscreenPanelCollapsed(true);
        }
    }, [isFullscreen, lecture.id]);

    useEffect(() => {
        onFullscreenChange?.(isFullscreen);
    }, [isFullscreen, onFullscreenChange]);

    useEffect(() => {
        if (Platform.OS === 'web') {
            const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
            document.addEventListener('fullscreenchange', onFsChange);
            return () => document.removeEventListener('fullscreenchange', onFsChange);
        }
    }, []);

    const isActive = activeVideo?.lectureId === lecture.id;
    const isEngineOwner = isActive && (Platform.OS === 'web' ? true : isFocused);
    const isOwnerInitialized = useRef(false);

    useEffect(() => {
        if (isEngineOwner) {
            claimEngine();
        } else if (isActive) {
            releaseEngine();
            isOwnerInitialized.current = false;
        }

        return () => {
            if (isEngineOwner) releaseEngine();
        };
    }, [isEngineOwner, isActive, claimEngine, releaseEngine]);

    useEffect(() => {
        if (Platform.OS !== 'web' || !isEngineOwner) return;

        const timer = setTimeout(() => {
            const element = document.getElementById('video-player-container');
            if (!element) return;

            const rect = element.getBoundingClientRect();
            const handleMouseMove = (event: MouseEvent) => {
                if (
                    event.clientX >= rect.left &&
                    event.clientX <= rect.right &&
                    event.clientY >= rect.top &&
                    event.clientY <= rect.bottom
                ) {
                    setIsHovered(true);
                }
            };

            window.addEventListener('mousemove', handleMouseMove, { once: true });
        }, 100);

        return () => clearTimeout(timer);
    }, [isEngineOwner]);

    const handleFullscreen = () => {
        if (Platform.OS === 'web') {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                const container = document.getElementById('video-player-container');
                if (container && container.requestFullscreen) {
                    container.requestFullscreen();
                } else {
                    playerEngine.getRef().current?.presentFullscreenPlayer();
                }
            }
        } else {
            playerEngine.getRef().current?.presentFullscreenPlayer();
        }
    };

    return (
        <FloatingShell
            nativeID="video-player-container"
            style={[styles.videoContainer, isFullscreen && (styles.fullscreenContainer as any)]}
            padding="none"
            radius="card"
            elevation="soft"
            {...(Platform.OS === 'web'
                ? {
                      onMouseEnter: () => setIsHovered(true),
                      onMouseLeave: () => setIsHovered(false),
                  }
                : {})}
        >
            <View style={[styles.videoSurfaceLayout, canShowFullscreenPanel && styles.videoSurfaceLayoutDocked]}>
                <View style={[styles.videoStage, canShowFullscreenPanel && styles.videoStageDocked]}>
                    <View style={styles.videoPlaceholder}>
                        {isEngineOwner && Platform.OS === 'web' && (
                            <video
                                ref={(el: HTMLVideoElement | null) => {
                                    if (isEngineOwner && el) {
                                        playerEngine.setWebVideoElement(el);
                                    }
                                }}
                                src={lecture.videoUrl || undefined}
                                muted={isMuted}
                                controls={false}
                                style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'contain',
                                    backgroundColor: 'transparent',
                                }}
                                playsInline
                                onTimeUpdate={(e: any) => {
                                    if (isEngineOwner) {
                                        updateTime(e.target.currentTime);
                                        updatePlayState(!e.target.paused);
                                    }
                                }}
                                onLoadedMetadata={(e: any) => {
                                    if (isEngineOwner) {
                                        updateDuration(e.target.duration || 0);
                                        if (!isOwnerInitialized.current && activeVideo) {
                                            isOwnerInitialized.current = true;
                                            e.target.currentTime = activeVideo.lastKnownPosition || 0;
                                            if (activeVideo.isPlaying) e.target.play().catch(() => {});
                                        }
                                    }
                                }}
                                onPlay={() => isEngineOwner && updatePlayState(true)}
                                onPause={() => isEngineOwner && updatePlayState(false)}
                            />
                        )}

                        {isEngineOwner && Platform.OS !== 'web' && (
                            <Video
                                ref={isEngineOwner ? playerEngine.getRef() : null}
                                style={styles.fullVideo}
                                videoStyle={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    bottom: 0,
                                    right: 0,
                                    width: '100%',
                                    height: '100%',
                                    objectFit: 'contain',
                                } as any}
                                resizeMode={ResizeMode.CONTAIN}
                                useNativeControls={false}
                                source={{ uri: lecture.videoUrl }}
                                isMuted={isMuted}
                                volume={volume}
                                status={{
                                    positionMillis: (activeVideo?.lastKnownPosition || 0) * 1000,
                                    shouldPlay: activeVideo?.isPlaying || false,
                                } as any}
                                onPlaybackStatusUpdate={(status) => {
                                    if (isEngineOwner && status.isLoaded) {
                                        playerEngine.onStatusUpdate(status);
                                        updateTime(status.positionMillis / 1000);
                                        updateDuration(status.durationMillis ? status.durationMillis / 1000 : 0);

                                        if (!isOwnerInitialized.current && activeVideo) {
                                            isOwnerInitialized.current = true;
                                            const ref = playerEngine.getRef().current;
                                            if (ref) {
                                                ref.setPositionAsync((activeVideo.lastKnownPosition || 0) * 1000).catch(() => {});
                                                if (activeVideo.isPlaying) ref.playAsync().catch(() => {});
                                            }
                                        } else {
                                            updatePlayState(status.isPlaying);
                                        }
                                    }
                                }}
                            />
                        )}

                        {isActive && !isEngineOwner && (
                            <Image
                                source={{ uri: activeVideo?.thumbnailUrl || lecture.thumbnailUrl }}
                                style={{ width: '100%', height: '100%', backgroundColor: '#000' }}
                                resizeMode="contain"
                            />
                        )}

                        {isActive && isEngineOwner && Platform.OS !== 'web' && (
                            <Pressable style={StyleSheet.absoluteFill} onPress={togglePlayPause} />
                        )}

                        {!isActive && (
                            <Pressable
                                style={StyleSheet.absoluteFill}
                                onPress={() => {
                                    const { loadSession } = require('../../store/videoStore').useVideoPlayerStore.getState();
                                    loadSession(lecture, pathname, topics);
                                }}
                            >
                                <View style={StyleSheet.flatten([styles.videoPlaceholder, { backgroundColor: 'rgba(0,0,0,0.4)' }])}>
                                    <Play color="#FFFFFF" size={48} />
                                </View>
                            </Pressable>
                        )}
                    </View>

                    {canShowFullscreenPanel && isFullscreenPanelCollapsed && (
                        <Pressable
                            style={[styles.fullscreenPanelReopenButton, { backgroundColor: 'rgba(10, 18, 20, 0.62)' }]}
                            onPress={() => setIsFullscreenPanelCollapsed(false)}
                        >
                            <FileText color={themeColors.primaryEmerald} size={18} />
                            <Typography variant="bodySm" color="#FFFFFF" style={styles.fullscreenPanelReopenLabel}>
                                {fullscreenPanelLabel}
                            </Typography>
                        </Pressable>
                    )}

                    {isActive && (
                        <VideoControlsOverlay
                            styles={styles}
                            lectureDuration={lecture.duration}
                            topics={topics}
                            activeVideo={activeVideo}
                            isMobile={isMobile}
                            isHovered={isHovered}
                            isMuted={isMuted}
                            setIsMuted={setIsMuted}
                            volume={volume}
                            setVolume={setVolume}
                            setGlobalVolume={setGlobalVolume}
                            onSeek={seekTo}
                            onTogglePlayPause={togglePlayPause}
                            onSetPlaybackRate={setPlaybackRate}
                            onFullscreen={handleFullscreen}
                        />
                    )}
                </View>

                {canShowFullscreenPanel && (
                    <View
                        style={[
                            styles.fullscreenPanelDock,
                            {
                                backgroundColor: themeColors.surfaceBase,
                                borderLeftColor: themeColors.borderSubtle,
                                opacity: showExpandedFullscreenPanel ? 1 : 0,
                                width: fullscreenPanelWidth,
                            },
                            Platform.OS === 'web' && {
                                transition: 'width 220ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 180ms ease-out',
                                pointerEvents: showExpandedFullscreenPanel ? 'auto' : 'none',
                            } as any,
                        ]}
                    >
                        <View
                            style={[
                                styles.fullscreenPanelDockInner,
                                Platform.OS === 'web' && {
                                    opacity: showExpandedFullscreenPanel ? 1 : 0,
                                    transform: `translateX(${showExpandedFullscreenPanel ? 0 : 18}px)`,
                                    transition: 'transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 160ms ease-out',
                                } as any,
                            ]}
                        >
                            {renderFullscreenPanel?.(() => setIsFullscreenPanelCollapsed(true))}
                        </View>
                    </View>
                )}
            </View>
        </FloatingShell>
    );
});
