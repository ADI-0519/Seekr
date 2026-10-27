import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FlatList, Platform, Pressable, View } from 'react-native';

import { Typography } from '@/components/ui/Typography';
import { theme } from '@/design';
import { useThemeColors } from '@/theme/ThemeProvider';
import { TranscriptSegment } from '@/types';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from './lectureDetail.styles';

function findActiveSegment(segments: TranscriptSegment[], time: number): number {
    if (!segments.length) return -1;
    const tolerance = 0.5;
    let lo = 0, hi = segments.length - 1, result = -1;
    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (time >= segments[mid].startTime - tolerance) {
            result = mid;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return result;
}

const TranscriptRow = React.memo(({ item, isActive, distance, isScrolling, onSeek, onResetInteraction, themeColors, compact = false, styles }: {
    item: TranscriptSegment;
    isActive: boolean;
    distance: number;
    isScrolling: boolean;
    onSeek: (time: number) => void;
    onResetInteraction: () => void;
    themeColors: any;
    compact?: boolean;
    styles: LectureDetailStyles;
}) => {
    const showMagnifier = !isScrolling;
    const scale = showMagnifier
        ? compact
            ? (isActive ? 1.02 : distance === 1 ? 0.99 : distance === 2 ? 0.98 : 0.97)
            : (isActive ? 1.06 : distance === 1 ? 0.99 : distance === 2 ? 0.97 : 0.95)
        : 1.0;
    const opacity = showMagnifier ? (isActive ? 1 : distance === 1 ? 0.8 : distance === 2 ? 0.6 : 0.4) : (isActive ? 1 : 0.8);
    const blur = showMagnifier ? (distance >= 3 ? (Platform.OS === 'web' && !compact ? 0.20 : 0) : 0) : 0;

    return (
        <Pressable
            onPress={() => {
                onSeek(item.startTime);
                onResetInteraction();
            }}
            style={({ pressed }) => [
                styles.transcriptLineFocusable,
                {
                    opacity,
                    transform: [{ scale }],
                    backgroundColor: isActive ? themeColors.chipBgReady : 'transparent',
                    ...(Platform.OS === 'web' ? {
                        transition: 'all 350ms cubic-bezier(0.2, 0.8, 0.2, 1)',
                        filter: blur ? `blur(${blur}px)` : 'none',
                    } : {}),
                } as any
            ]}
        >
            <View style={styles.transcriptLineContent}>
                <Typography
                    variant="meta"
                    color={isActive ? themeColors.primaryEmerald : themeColors.textSecondary}
                    style={[styles.timestampFocal, isActive && { fontWeight: '700' }]}
                >
                    {formatDuration(item.startTime)}
                </Typography>
                <Typography
                    variant="bodyLg"
                    style={[
                        styles.transcriptTextFocal,
                        compact && styles.transcriptTextFocalCompact,
                        isActive ? { color: themeColors.textPrimary, fontWeight: '700' } : { color: themeColors.textSecondary }
                    ]}
                >
                    {item.text}
                </Typography>
            </View>
        </Pressable>
    );
});

export const TranscriptPanel = React.memo(({ segments, currentTime, onSeek, isFocused, contentPaddingHorizontal = 0, compact = false, styles }: {
    segments: TranscriptSegment[],
    currentTime: number,
    onSeek: (time: number) => void,
    isFocused: boolean,
    contentPaddingHorizontal?: number,
    compact?: boolean,
    styles: LectureDetailStyles,
}) => {
    const flatListRef = useRef<FlatList>(null);
    const themeColors = useThemeColors();

    // Keep active-segment lookup cheap for longer transcripts.
    const activeIndex = useMemo(
        () => findActiveSegment(segments, currentTime),
        [segments, currentTime]
    );

    const lastScrolledIndex = useRef(-1);
    const isUserScrolling = useRef(false);
    const lastInteractionTime = useRef(0);
    const previousTimeRef = useRef(currentTime);
    const pendingScrollIndexRef = useRef<number | null>(null);
    const retryScrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

    const clearRetry = useCallback(() => {
        if (retryScrollTimeout.current) {
            clearTimeout(retryScrollTimeout.current);
            retryScrollTimeout.current = null;
        }
    }, []);

    const tryCenterIndex = useCallback((index: number, animated = true) => {
        if (!flatListRef.current || index < 0) return false;
        try {
            flatListRef.current.scrollToIndex({
                index,
                animated,
                viewPosition: 0.5,
            });
            lastScrolledIndex.current = index;
            pendingScrollIndexRef.current = null;
            return true;
        } catch {
            pendingScrollIndexRef.current = index;
            return false;
        }
    }, []);

    const scheduleRetryCenter = useCallback((index: number, delayMs = 140) => {
        clearRetry();
        retryScrollTimeout.current = setTimeout(() => {
            const success = tryCenterIndex(index, true);
            if (!success) {
                // Leave the target queued for the next layout pass.
                pendingScrollIndexRef.current = index;
            }
        }, delayMs);
    }, [clearRetry, tryCenterIndex]);

    // Reset transcript locking after large seeks.
    useEffect(() => {
        const previousTime = previousTimeRef.current;
        const delta = Math.abs(currentTime - previousTime);
        previousTimeRef.current = currentTime;

        if (!isFocused) return;

        if (delta >= 2) {
            isUserScrolling.current = false;
            setIsScrolling(false);
            lastInteractionTime.current = 0;
            lastScrolledIndex.current = -1;
        }
    }, [currentTime, isFocused]);

    useEffect(() => {
        const now = Date.now();
        const interactionCooldown = 3000;

        if (!isFocused) return;

        // Let layout settle after hidden tabs switch back on.
        const timer = setTimeout(() => {
            if (activeIndex !== -1 && activeIndex !== lastScrolledIndex.current && flatListRef.current) {
                if (isUserScrolling.current && (now - lastInteractionTime.current >= interactionCooldown)) {
                    isUserScrolling.current = false;
                }

                if (isUserScrolling.current || (now - lastInteractionTime.current < interactionCooldown)) {
                    return;
                }

                const success = tryCenterIndex(activeIndex, true);
                if (!success) {
                    scheduleRetryCenter(activeIndex, 120);
                }
            }
        }, 50);

        return () => clearTimeout(timer);
    }, [activeIndex, isFocused, tryCenterIndex, scheduleRetryCenter]);

    const [isScrolling, setIsScrolling] = useState(false);
    const scrollEndTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

    const handleScrollBegin = useCallback(() => {
        if (scrollEndTimeout.current) clearTimeout(scrollEndTimeout.current);
        isUserScrolling.current = true;
        setIsScrolling(true);
        lastInteractionTime.current = Date.now();
    }, []);

    const handleScrollEnd = useCallback(() => {
        isUserScrolling.current = false;
        lastInteractionTime.current = Date.now();

        if (scrollEndTimeout.current) clearTimeout(scrollEndTimeout.current);
        scrollEndTimeout.current = setTimeout(() => {
            setIsScrolling(false);
        }, 150);
    }, []);

    const handleResetInteraction = useCallback(() => {
        lastInteractionTime.current = 0;
    }, []);

    // Reset scrolling state when the panel regains focus.
    useEffect(() => {
        if (isFocused) {
            isUserScrolling.current = false;
            setIsScrolling(false);
            if (scrollEndTimeout.current) clearTimeout(scrollEndTimeout.current);
            // Force the next focus pass to recenter immediately.
            lastScrolledIndex.current = -1;
            if (activeIndex !== -1) {
                scheduleRetryCenter(activeIndex, 80);
            }
        }
        return () => {
            clearRetry();
        };
    }, [isFocused, activeIndex, scheduleRetryCenter, clearRetry]);

    const fadeTopStyle = Platform.OS === 'web' ? {
        background: `linear-gradient(to bottom, ${themeColors.surfaceBase}, transparent)`,
        transition: 'opacity 300ms ease-out',
        opacity: isScrolling ? 0 : 1,
    } : { opacity: isScrolling ? 0 : 0.8 };

    const fadeBottomStyle = Platform.OS === 'web' ? {
        background: `linear-gradient(to top, ${themeColors.surfaceBase}, transparent)`,
        transition: 'opacity 300ms ease-out',
        opacity: isScrolling ? 0 : 1,
    } : { opacity: isScrolling ? 0 : 0.8 };

    const renderItem = useCallback(({ item, index }: { item: TranscriptSegment; index: number }) => {
        const isActive = index === activeIndex;
        const distance = Math.abs(index - activeIndex);

        return (
            <TranscriptRow
                item={item}
                isActive={isActive}
                distance={distance}
                isScrolling={isScrolling}
                onSeek={onSeek}
                onResetInteraction={handleResetInteraction}
                themeColors={themeColors}
                compact={compact} styles={styles}
            />
        );
    }, [activeIndex, compact, isScrolling, onSeek, handleResetInteraction, themeColors]);

    return (
        <View style={styles.transcriptPanelWrapper}>
            <View style={[styles.transcriptFadeMask, styles.transcriptFadeTop, fadeTopStyle as any]} pointerEvents="none" />
            <View style={[styles.transcriptFadeMask, styles.transcriptFadeBottom, fadeBottomStyle as any]} pointerEvents="none" />

            <FlatList
                ref={flatListRef}
                data={segments}
                extraData={[activeIndex, isScrolling]}
                keyExtractor={item => item.id}
                contentContainerStyle={[styles.transcriptContent, { paddingHorizontal: contentPaddingHorizontal, paddingVertical: theme.spacing[16] }]}
                style={styles.transcriptList}
                showsVerticalScrollIndicator={true}
                scrollEventThrottle={16}
                initialNumToRender={15}
                windowSize={7}
                maxToRenderPerBatch={8}
                removeClippedSubviews={Platform.OS !== 'web'}
                onScrollBeginDrag={handleScrollBegin}
                onScrollEndDrag={handleScrollEnd}
                onMomentumScrollBegin={handleScrollBegin}
                onMomentumScrollEnd={handleScrollEnd}
                onScrollToIndexFailed={(info) => {
                    pendingScrollIndexRef.current = info.index;
                    flatListRef.current?.scrollToOffset({
                        offset: Math.max(0, info.averageItemLength * info.index),
                        animated: false,
                    });
                    scheduleRetryCenter(info.index, 160);
                }}
                onContentSizeChange={() => {
                    const pendingIndex = pendingScrollIndexRef.current;
                    if (pendingIndex !== null) {
                        scheduleRetryCenter(pendingIndex, 40);
                    }
                }}
                renderItem={renderItem}
            />
        </View>
    );
});
