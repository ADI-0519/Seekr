import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import Animated, {
    useSharedValue,
    useAnimatedStyle,
    withTiming,
    Easing,
    useReducedMotion,
} from 'react-native-reanimated';
import { useTheme } from '../../theme/ThemeProvider';
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

const CROSSFADE_MS = 600;
// Slightly over-scale to cover edges after blur/positioning
const SCALE = 1.15;

export const AppBackground = () => {
    const { isDark, backgroundStyle, videoAnimation } = useTheme();
    const reducedMotion = useReducedMotion();

    if (backgroundStyle === 'static') {
        const staticBg = isDark ? '#0F211B' : '#E8F7F0';
        return (
            <View style={[styles.container, { backgroundColor: staticBg }]} pointerEvents="none" />
        );
    }

    const variantKey = isDark ? 'b' : 'w';
    const source = videoSources[`${videoAnimation}-${variantKey}`];

    return (
        <View style={styles.container} pointerEvents="none">
            <VideoLayer
                source={source}
                animationKey={`${videoAnimation}-${variantKey}`}
                reducedMotion={!!reducedMotion}
            />
        </View>
    );
};


interface VideoLayerProps {
    source: any;
    animationKey: string;
    reducedMotion: boolean;
}

const VideoLayer: React.FC<VideoLayerProps> = ({ source, animationKey, reducedMotion }) => {
    // Track current and previous sources for crossfade
    const [layers, setLayers] = useState<{ key: string; source: any; entering: boolean }[]>([
        { key: animationKey, source, entering: false },
    ]);
    const prevKeyRef = useRef(animationKey);

    useEffect(() => {
        if (animationKey !== prevKeyRef.current) {
            const oldKey = prevKeyRef.current;
            prevKeyRef.current = animationKey;

            // Mount the new layer above the old one
            setLayers([
                { key: oldKey, source: layers.find(l => l.key === oldKey)?.source ?? source, entering: false },
                { key: animationKey, source, entering: true },
            ]);

            // Drop the old layer after the fade finishes
            const timer = setTimeout(() => {
                setLayers(prev => prev.filter(l => l.key === animationKey));
            }, CROSSFADE_MS + 200);

            return () => clearTimeout(timer);
        }
    }, [animationKey, source]);

    return (
        <>
            {layers.map((layer, index) => (
                <FadingVideo
                    key={layer.key}
                    source={layer.source}
                    fadeIn={layer.entering}
                    reducedMotion={reducedMotion}
                />
            ))}
        </>
    );
};


interface FadingVideoProps {
    source: any;
    fadeIn: boolean;
    reducedMotion: boolean;
}

const FadingVideo: React.FC<FadingVideoProps> = ({ source, fadeIn, reducedMotion }) => {
    const opacity = useSharedValue(fadeIn ? 0 : 1);

    useEffect(() => {
        if (fadeIn) {
            opacity.value = withTiming(1, {
                duration: reducedMotion ? 0 : CROSSFADE_MS,
                easing: Easing.inOut(Easing.ease),
            });
        }
    }, [fadeIn]);

    const animatedStyle = useAnimatedStyle(() => ({
        opacity: opacity.value,
    }));

    return (
        <Animated.View style={[styles.videoWrapper, animatedStyle]}>
            <Video
                source={source}
                shouldPlay
                isMuted
                isLooping
                resizeMode={ResizeMode.COVER}
                style={styles.video}
            />
        </Animated.View>
    );
};

const styles = StyleSheet.create({
    container: {
        ...StyleSheet.absoluteFillObject,
        zIndex: 0,
        overflow: 'hidden',
    },
    videoWrapper: {
        ...StyleSheet.absoluteFillObject,
        // Scale up slightly to avoid edge artifacts
        transform: [{ scale: SCALE }],
    },
    video: {
        width: '100%',
        height: '100%',
    },
});
