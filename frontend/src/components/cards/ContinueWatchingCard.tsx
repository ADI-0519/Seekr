import React, { useState } from 'react';
import { View, StyleSheet, Pressable, Image, Platform } from 'react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design/index';
import { motion } from '../../design/tokens/motion';
import { formatDuration } from '../../utils/formatDuration';
import { Lecture } from '../../types';
import { useThemeColors } from '../../theme/ThemeProvider';
import { useVideoPlayerStore } from '../../store/videoStore';

interface ContinueWatchingCardProps {
    lecture: Lecture;
    onPress: () => void;
}

export const ContinueWatchingCard: React.FC<ContinueWatchingCardProps> = ({
    lecture,
    onPress,
}) => {
    const themeColors = useThemeColors();
    const styles = React.useMemo(() => getStyles(themeColors), [themeColors]);
    const [hovered, setHovered] = useState(false);
    const progressByLecture = useVideoPlayerStore((state) => state.progressByLecture);
    const progressState = progressByLecture[lecture.id];
    const duration = lecture.duration || progressState?.duration || 0;
    const currentTime = progressState?.currentTime ?? lecture.resumePosition ?? 0;
    const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;
    const remaining = Math.max(0, duration - currentTime);
    const timeLeft = remaining > 0 ? `${Math.round(remaining / 60)} mins left` : 'Up next';

    return (
        <Pressable
            onPress={onPress}
            {...(Platform.OS === 'web' ? {
                onMouseEnter: () => setHovered(true),
                onMouseLeave: () => setHovered(false),
            } as any : {})}
        >
            {({ pressed }) => (
                <FloatingShell
                    style={[
                        styles.container,
                        pressed && { transform: [{ scale: 0.99 }] },
                        ...(Platform.OS === 'web' ? [{
                            transition: `transform ${motion.durationBase}ms ${motion.easeInOut}`,
                            transform: hovered ? `translateY(${motion.cardLiftY}px)` : pressed ? 'scale(0.99)' : 'none',
                        } as any] : []),
                    ]}
                    padding="none"
                    elevation={hovered ? 'hover' : 'soft'}
                >
                    <View style={styles.inner}>
                        {/* Left Half: Image */}
                        <View style={styles.imageContainer}>
                            <Image
                                source={{ uri: lecture.thumbnailUrl }}
                                style={styles.image}
                                resizeMode="cover"
                            />
                            <View style={styles.durationBadge}>
                                <Typography variant="chip" color={themeColors.surfaceBase}>
                                    {formatDuration(duration * (progressPercent / 100))} / {formatDuration(duration)}
                                </Typography>
                            </View>
                        </View>

                        {/* Right Half: Content */}
                        <View style={styles.contentContainer}>
                            <Typography variant="headingXl" color={themeColors.textPrimary} style={styles.title} numberOfLines={2}>
                                {lecture.title}
                            </Typography>

                            <Typography variant="bodyLg" color={themeColors.textSecondary} style={styles.description} numberOfLines={3}>
                                {lecture.overview || lecture.description || 'Open lecture to generate notes and overview.'}
                            </Typography>

                            <View style={styles.progressSection}>
                                <View style={styles.progressHeader}>
                                    <Typography variant="bodySm" color={themeColors.textSecondary}>
                                        {Math.round(progressPercent)}% Completed
                                    </Typography>
                                    <Typography variant="bodySm" color={themeColors.textSecondary}>
                                        {timeLeft}
                                    </Typography>
                                </View>
                                <View style={styles.progressBarBg}>
                                    <View style={[styles.progressBarFill, { width: `${progressPercent}%` }]} />
                                    <View style={[styles.progressHandle, { left: `${progressPercent}%` }]} />
                                </View>
                            </View>
                        </View>
                    </View>
                </FloatingShell>
            )}
        </Pressable>
    );
};

const getStyles = (themeColors: any) => StyleSheet.create({
    container: {
        width: '100%',
        marginBottom: theme.spacing[40],
    },
    inner: {
        flexDirection: 'row',
        height: 380,
    },
    imageContainer: {
        flex: 1.2,
        backgroundColor: themeColors.borderSubtle,
        position: 'relative',
        overflow: 'hidden',
        borderTopLeftRadius: theme.radii.card,
        borderBottomLeftRadius: theme.radii.card,
        borderTopRightRadius: 8,
        borderBottomRightRadius: 8,
    },
    image: {
        ...StyleSheet.absoluteFillObject,
    },
    durationBadge: {
        position: 'absolute',
        bottom: theme.spacing[16],
        right: theme.spacing[16],
        backgroundColor: 'rgba(26, 43, 46, 0.75)',
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[4],
        borderRadius: theme.radii.pill,
    },
    contentContainer: {
        flex: 1,
        padding: theme.spacing[40],
        justifyContent: 'center',
    },
    title: {
        marginBottom: theme.spacing[20], // Increased from 16 to breathe more
    },
    description: {
        marginBottom: 'auto',
        lineHeight: 30, // Increased from 28
    },
    progressSection: {
        marginTop: theme.spacing[32],
    },
    progressHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[12],
    },
    progressBarBg: {
        height: 8,
        backgroundColor: themeColors.borderSubtle,
        borderRadius: theme.radii.pill,
        position: 'relative',
        justifyContent: 'center',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: themeColors.primaryEmerald,
        borderRadius: theme.radii.pill,
    },
    progressHandle: {
        position: 'absolute',
        width: 16,
        height: 16,
        borderRadius: 8,
        backgroundColor: themeColors.surfaceBase,
        borderWidth: 2,
        borderColor: themeColors.primaryEmerald,
        marginLeft: -8, // center horizontally
        top: -6,
    }
});
