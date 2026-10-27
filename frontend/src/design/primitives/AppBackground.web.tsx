import React, { useState, useEffect, useRef, useCallback } from 'react';
import { View, StyleSheet } from 'react-native';
import { useTheme, useThemeColors } from '../../theme/ThemeProvider';
import type { VideoAnimation } from '../../theme/ThemeProvider';

const videoSources: Record<`${VideoAnimation}-${'w' | 'b'}`, any> = {
    '1-w': require('../../../assets/videos/1-w.mp4'),
    '1-b': require('../../../assets/videos/1-b.mp4'),
    '2-w': require('../../../assets/videos/2-w.mp4'),
    '2-b': require('../../../assets/videos/2-b.mp4'),
    '3-w': require('../../../assets/videos/3-w.mp4'),
    '3-b': require('../../../assets/videos/3-b.mp4'),
    '4-w': require('../../../assets/videos/4-w.mp4'),
    '4-b': require('../../../assets/videos/4-b.mp4'),
    '5-w': require('../../../assets/videos/5-w.mp4'),
    '5-b': require('../../../assets/videos/5-b.mp4'),
    '6-w': require('../../../assets/videos/6-w.mp4'),
    '6-b': require('../../../assets/videos/6-b.mp4'),
    '7-w': require('../../../assets/videos/7-w.mp4'),
    '7-b': require('../../../assets/videos/7-b.mp4'),
};

function resolveSource(src: any): string {
    if (typeof src === 'string') return src;
    if (src && typeof src === 'object' && src.uri) return src.uri;
    if (src && typeof src === 'object' && src.default) return src.default;
    return String(src);
}

const CROSSFADE_MS = 800;

interface VideoLayer {
    animation: VideoAnimation;
    exiting: boolean;
    uid: number;
}

let layerUid = 0;

export const AppBackground = () => {
    const { isDark, backgroundStyle, videoAnimation } = useTheme();
    const themeColors = useThemeColors();

    const [layers, setLayers] = useState<VideoLayer[]>(() => [
        { animation: videoAnimation, exiting: false, uid: ++layerUid },
    ]);
    const prevAnimRef = useRef(videoAnimation);

    const [delayedIsDark, setDelayedIsDark] = useState(isDark);

    useEffect(() => {
        let timer: ReturnType<typeof setTimeout>;
        if (delayedIsDark !== isDark) {
            timer = setTimeout(() => {
                setDelayedIsDark(isDark);
            }, 600);
        }
        return () => clearTimeout(timer);
    }, [isDark, delayedIsDark]);

    const mountLight = !isDark || !delayedIsDark;
    const mountDark = isDark || delayedIsDark;

    useEffect(() => {
        if (videoAnimation !== prevAnimRef.current) {
            prevAnimRef.current = videoAnimation;

            setLayers(prev => [
                ...prev.map(l => ({ ...l, exiting: true })),
                { animation: videoAnimation, exiting: false, uid: ++layerUid },
            ]);

            const timer = setTimeout(() => {
                setLayers(prev => prev.filter(l => !l.exiting));
            }, CROSSFADE_MS + 100);

            return () => clearTimeout(timer);
        }
    }, [videoAnimation]);

    const containerClasses = [
        'app-background-container',
        isDark ? 'theme-dark' : 'theme-light'
    ].join(' ');

    return (
        <View style={styles.container} pointerEvents="none">
            <style dangerouslySetInnerHTML={{ __html: cssString }} />
            <div className={containerClasses}>
                {backgroundStyle === 'animated' ? (
                    <>
                        {layers.map((layer) => (
                            <div
                                key={layer.uid}
                                className={layer.exiting ? 'bg-layer bg-layer-exit' : 'bg-layer bg-layer-enter'}
                            >
                                {mountLight && (
                                    <NativeVideo
                                        src={resolveSource(videoSources[`${layer.animation}-w`])}
                                        shouldPlay={!isDark && !layer.exiting}
                                        opacity={isDark ? 0 : 1}
                                        filter="blur(12px) brightness(0.9) contrast(0.95) saturate(0.9)"
                                        zIndex={1}
                                    />
                                )}

                                {mountDark && (
                                    <NativeVideo
                                        src={resolveSource(videoSources[`${layer.animation}-b`])}
                                        shouldPlay={isDark && !layer.exiting}
                                        opacity={isDark ? 1 : 0}
                                        filter="blur(22px) brightness(0.9) contrast(1) saturate(1)"
                                        zIndex={2}
                                    />
                                )}
                            </div>
                        ))}
                        <div className="bg-grain" />
                    </>
                ) : (
                    <div style={{
                        position: 'absolute',
                        inset: 0,
                        backgroundColor: themeColors.appBg,
                        backgroundImage: isDark
                            ? 'radial-gradient(1200px 800px at 20% 10%, rgba(16, 185, 129, 0.12), transparent 60%), radial-gradient(900px 700px at 80% 90%, rgba(34, 197, 94, 0.08), transparent 55%)'
                            : 'radial-gradient(1200px 800px at 20% 10%, rgba(16, 185, 129, 0.10), transparent 60%), radial-gradient(900px 700px at 80% 90%, rgba(34, 197, 94, 0.08), transparent 55%)',
                    }} />
                )}
            </div>
        </View>
    );
};

interface NativeVideoProps {
    src: string;
    shouldPlay: boolean;
    opacity: number;
    filter: string;
    zIndex: number;
}

const NativeVideo: React.FC<NativeVideoProps> = ({ src, shouldPlay, opacity, filter, zIndex }) => {
    const videoRef = useRef<HTMLVideoElement>(null);

    const tryPlay = useCallback(() => {
        const video = videoRef.current;
        if (!video || !shouldPlay) return;
        video.muted = true;
        const p = video.play();
        if (p) p.catch(() => {});
    }, [shouldPlay]);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        if (shouldPlay) {
            if (video.readyState >= 2) {
                tryPlay();
            }
        } else {
            video.pause();
        }
    }, [shouldPlay, src, tryPlay]);

    return (
        <video
            ref={videoRef}
            src={src}
            loop
            muted
            playsInline
            preload={shouldPlay ? 'auto' : 'none'}
            onLoadedData={tryPlay}
            style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                objectFit: 'cover',
                filter,
                transform: 'scale(1.08)',
                zIndex,
                opacity,
                transition: 'opacity 0.5s ease-in-out',
                pointerEvents: 'none',
            }}
        />
    );
};

const styles = StyleSheet.create({
    container: {
        ...StyleSheet.absoluteFillObject,
        zIndex: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
    },
});

const cssString = `
    .app-background-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        pointer-events: none;
        overflow: hidden;
        z-index: 0;
        background-color: #000;
    }

    .bg-layer {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
    }

    @keyframes bgFadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    @keyframes bgFadeOut {
        from { opacity: 1; }
        to   { opacity: 0; }
    }

    .bg-layer-enter {
        animation: bgFadeIn 800ms ease-in-out forwards;
    }

    .bg-layer-exit {
        animation: bgFadeOut 800ms ease-in-out forwards;
    }

    .bg-grain {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 3;
        opacity: 0.01;
        pointer-events: none;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    }

    @media (prefers-reduced-motion: reduce) {
        .app-background-container video {
            transition: none !important;
        }
        .bg-layer-enter,
        .bg-layer-exit {
            animation: none !important;
            opacity: 1 !important;
        }
    }
`;
