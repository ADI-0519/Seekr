import React, { useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import { theme } from '@/design';
import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import { TopicSegment } from '@/types';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from './lectureDetail.styles';
const SegmentItem = React.memo(({
    topic,
    isActive,
    onSeek,
    isLast,
    styles,
}: {
    topic: TopicSegment;
    isActive: boolean;
    onSeek: (time: number) => void;
    isLast: boolean;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();
    const [hovered, setHovered] = useState(false);
    const [focused, setFocused] = useState(false);

    const shouldShowSummary = Platform.OS === 'web' ? hovered || focused : false;

    return (
        <Pressable
            onPress={() => onSeek(topic.startTime)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            {...(Platform.OS === 'web'
                ? {
                    onMouseEnter: () => setHovered(true),
                    onMouseLeave: () => setHovered(false),
                } as any
                : {})}
            style={StyleSheet.flatten([
                styles.segmentItem,
                {
                    backgroundColor: themeColors.surfaceElevated,
                    borderColor: themeColors.borderSubtle,
                },
                isActive && [
                    styles.segmentItemActive,
                    { backgroundColor: themeColors.chipBgReady },
                ],
            ])}
        >
            <View style={styles.segmentDotContainer}>
                <View
                    style={StyleSheet.flatten([
                        styles.segmentDot,
                        { backgroundColor: themeColors.borderSubtle },
                        isActive && [
                            styles.segmentDotActive,
                            { backgroundColor: themeColors.primaryEmerald },
                        ],
                    ])}
                />
                {!isLast && (
                    <View
                        style={[
                            styles.segmentLine,
                            { backgroundColor: themeColors.borderSubtle },
                        ]}
                    />
                )}
            </View>

            <View style={styles.segmentInfo}>
                <Typography
                    variant="bodyLg"
                    color={isActive ? themeColors.primaryEmerald : themeColors.textPrimary}
                    style={{ fontWeight: '500' }}
                >
                    {topic.title}
                </Typography>

                <Typography
                    variant="meta"
                    color={themeColors.textSecondary}
                    style={styles.segmentTimestamp}
                >
                    {formatDuration(topic.startTime)}
                </Typography>

                {topic.summary ? (
                    <View
                        style={[
                            styles.segmentSummaryWrapper,
                            shouldShowSummary ? styles.segmentSummaryWrapperVisible : styles.segmentSummaryWrapperHidden,
                            Platform.OS === 'web'
                                ? ({
                                    transition: [
                                        `max-height ${theme.motion.durationBase}ms ${theme.motion.easeInOut}`,
                                        `opacity ${theme.motion.durationBase}ms ${theme.motion.easeOut}`,
                                        `margin-top ${theme.motion.durationFast}ms ${theme.motion.easeInOut}`,
                                    ].join(', '),
                                } as any)
                                : {},
                        ]}
                        pointerEvents="none"
                    >
                        <Typography
                            variant="bodySm"
                            color={themeColors.textSecondary}
                            style={styles.segmentSummary}
                        >
                            {topic.summary}
                        </Typography>
                    </View>
                ) : null}
            </View>
        </Pressable>
    );
});
export const SegmentsList = React.memo(({
    topics,
    currentTime,
    onSeek,
    styles,
}: {
    topics: TopicSegment[];
    currentTime: number;
    onSeek: (time: number) => void;
    styles: LectureDetailStyles;
}) => {
    const hasPlaybackProgress = currentTime > 0;

    return (
        <View style={styles.segmentsSidebar}>
            {topics.map((topic, index) => (
                <SegmentItem
                    key={topic.id}
                    topic={topic}
                    isActive={hasPlaybackProgress && currentTime >= topic.startTime && currentTime <= topic.endTime}
                    onSeek={onSeek}
                    isLast={index === topics.length - 1} styles={styles}
                />
            ))}
        </View>
    );
});
