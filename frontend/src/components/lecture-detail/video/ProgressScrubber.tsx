import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';

import { useThemeColors } from '@/theme/ThemeProvider';
import { TopicSegment } from '@/types';
import { getRawCurrentTime } from '@/store/videoStore';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from '../lectureDetail.styles';

import { TopicMarker } from './TopicMarker';

type ActiveVideoLike = {
    currentTime: number;
    duration: number;
} | null | undefined;

export const ProgressScrubber = ({
    styles,
    lectureDuration,
    topics,
    activeVideo,
    onSeek,
    timeTextRef,
}: {
    styles: LectureDetailStyles;
    lectureDuration: number;
    topics: TopicSegment[];
    activeVideo: ActiveVideoLike;
    onSeek: (t: number) => void;
    timeTextRef: React.RefObject<Text | null>;
}) => {
    const themeColors = useThemeColors();
    const [progressBarWidth, setProgressBarWidth] = useState(0);

    const progressFillRef = useRef<View>(null);
    const progressHandleRef = useRef<View>(null);

    useEffect(() => {
        if (Platform.OS !== 'web' || !activeVideo) return;

        let animFrameId: number;
        const tick = () => {
            const duration = activeVideo.duration;
            if (duration > 0) {
                const rawTime = getRawCurrentTime();
                const pct = (rawTime / duration) * 100;

                const fillEl = (progressFillRef.current as any)?._nativeTag
                    ? undefined
                    : (progressFillRef.current as unknown as HTMLElement);
                const handleEl = (progressHandleRef.current as any)?._nativeTag
                    ? undefined
                    : (progressHandleRef.current as unknown as HTMLElement);
                const textEl = (timeTextRef.current as any)?._nativeTag
                    ? undefined
                    : (timeTextRef.current as unknown as HTMLElement);

                if (fillEl) fillEl.style.width = `${pct}%`;
                if (handleEl) handleEl.style.left = `${pct}%`;
                if (textEl) {
                    textEl.textContent = `${formatDuration(rawTime)} / ${formatDuration(duration)}`;
                }
            }
            animFrameId = requestAnimationFrame(tick);
        };

        animFrameId = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(animFrameId);
    }, [activeVideo?.duration, timeTextRef]);

    const progress = activeVideo?.duration ? (activeVideo.currentTime / activeVideo.duration) * 100 : 0;

    const scrubTo = useCallback(
        (x: number, width: number) => {
            if (!activeVideo?.duration || !width) return;
            const percentage = Math.max(0, Math.min(1, x / width));
            onSeek(percentage * activeVideo.duration);
        },
        [activeVideo?.duration, onSeek]
    );

    const handleScrubPress = (event: any) => {
        if (!progressBarWidth) return;
        const x =
            Platform.OS === 'web'
                ? event.clientX - event.currentTarget.getBoundingClientRect().left
                : event.nativeEvent.locationX;
        scrubTo(x, progressBarWidth);
    };

    const progressRectRef = useRef<{ left: number; width: number } | null>(null);

    const handleScrubMouseDown = (event: any) => {
        if (Platform.OS !== 'web') return;
        handleScrubPress(event);
        const target = event.currentTarget as HTMLElement | null;
        if (!target) return;
        const rect = target.getBoundingClientRect();
        progressRectRef.current = { left: rect.left, width: rect.width };
        const onMove = (e: MouseEvent) => {
            if (!progressRectRef.current) return;
            scrubTo(e.clientX - progressRectRef.current.left, progressRectRef.current.width);
        };
        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            progressRectRef.current = null;
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    };

    const webScrubProps =
        Platform.OS === 'web' ? ({ onMouseDown: handleScrubMouseDown, onClick: handleScrubPress } as any) : {};

    return (
        <View
            style={
                Platform.OS === 'web'
                    ? [styles.progressBarPressable, { cursor: 'pointer' as any }]
                    : styles.progressBarPressable
            }
            onLayout={(e) => setProgressBarWidth(e.nativeEvent.layout.width)}
            onStartShouldSetResponder={() => Platform.OS !== 'web'}
            onResponderGrant={(e) => scrubTo(e.nativeEvent.locationX, progressBarWidth)}
            onResponderMove={(e) => scrubTo(e.nativeEvent.locationX, progressBarWidth)}
            {...webScrubProps}
        >
            <View style={styles.progressBarBg}>
                <View
                    ref={progressFillRef}
                    style={StyleSheet.flatten([
                        styles.progressBarFill,
                        { width: `${progress}%`, backgroundColor: themeColors.primaryEmerald },
                    ])}
                />

                <View style={styles.topicOverlayContainer} pointerEvents="box-none">
                    {topics.map((topic) => {
                        const duration = activeVideo?.duration || lectureDuration || 1;
                        const leftPercent = Math.max(0, Math.min(100, (topic.startTime / duration) * 100));
                        const widthPercent = Math.max(
                            0.5,
                            Math.min(100 - leftPercent, ((topic.endTime - topic.startTime) / duration) * 100)
                        );

                        return (
                            <TopicMarker
                                key={topic.id}
                                styles={styles}
                                topic={topic}
                                leftPercent={leftPercent}
                                widthPercent={widthPercent}
                                onSeek={onSeek}
                            />
                        );
                    })}
                </View>

                <View
                    ref={progressHandleRef}
                    style={[styles.progressHandle, { left: `${progress}%`, borderColor: themeColors.primaryEmerald }]}
                />
            </View>
        </View>
    );
};
