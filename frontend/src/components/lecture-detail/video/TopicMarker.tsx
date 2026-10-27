import React, { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';

import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import { TopicSegment } from '@/types';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from '../lectureDetail.styles';

export const TopicMarker = ({
    topic,
    leftPercent,
    widthPercent,
    onSeek,
    styles,
}: {
    topic: TopicSegment;
    leftPercent: number;
    widthPercent: number;
    onSeek: (time: number) => void;
    styles: LectureDetailStyles;
}) => {
    const [hovered, setHovered] = useState(false);
    const themeColors = useThemeColors();

    return (
        <View
            style={[styles.topicMarkerWrapper, { left: `${leftPercent}%`, width: `${widthPercent}%` }]}
            pointerEvents="box-none"
        >
            <Pressable
                style={({ pressed }) => [
                    styles.topicMarker,
                    { backgroundColor: themeColors.primaryEmerald },
                    hovered ? { opacity: 0.9, height: 6 } : { opacity: 0.5, height: 4 },
                    pressed && { opacity: 1, height: 6 },
                    Platform.OS === 'web'
                        ? ({ transition: 'opacity 220ms cubic-bezier(0.22, 1, 0.36, 1), height 220ms cubic-bezier(0.22, 1, 0.36, 1)' } as any)
                        : null,
                ]}
                onPress={(e) => {
                    e.stopPropagation();
                    onSeek(topic.startTime);
                }}
                accessibilityLabel={`${topic.title} at ${formatDuration(topic.startTime)}`}
                accessibilityRole="button"
                {...(Platform.OS === 'web'
                    ? {
                          onHoverIn: () => setHovered(true),
                          onHoverOut: () => setHovered(false),
                          onMouseDown: (e: any) => e.stopPropagation(),
                          onClick: (e: any) => e.stopPropagation(),
                      }
                    : {})}
            />
            {Platform.OS === 'web' && (
                <View
                    style={[
                        styles.topicTooltipContainer,
                        {
                            backgroundColor: themeColors.surfaceElevated,
                            borderColor: themeColors.borderSubtle,
                        },
                        hovered ? styles.topicTooltipVisible : styles.topicTooltipHidden,
                        { transform: hovered ? 'translateX(-50%) translateY(0px)' : 'translateX(-50%) translateY(4px)' } as any,
                    ]}
                    pointerEvents="none"
                >
                    <Typography variant="meta" color={themeColors.textPrimary} style={{ whiteSpace: 'nowrap' } as any}>
                        {topic.title}
                    </Typography>
                </View>
            )}
        </View>
    );
};
