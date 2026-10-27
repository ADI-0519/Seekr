import React, { useState } from 'react';
import { View, StyleSheet, Image, Pressable, Platform } from 'react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { StatusChip, StatusVariant } from '../ui/StatusChip';
import { theme } from '../../design/index';
import { motion } from '../../design/tokens/motion';
import { formatDuration } from '../../utils/formatDuration';
import { Lecture } from '../../types';
import { useThemeColors, useTheme } from '../../theme/ThemeProvider';
import { useVideoPlayerStore } from '../../store/videoStore';

interface LectureCardProps {
    lecture: Lecture;
    onPress: () => void;
}

export const LectureCard: React.FC<LectureCardProps> = ({ lecture, onPress }) => {
    const [hovered, setHovered] = useState(false);
    const themeColors = useThemeColors();
    const { isDark, cardStyle } = useTheme();
    const progressByLecture = useVideoPlayerStore((state) => state.progressByLecture);
    const progressState = progressByLecture[lecture.id];
    const duration = lecture.duration || progressState?.duration || 0;
    const currentTime = progressState?.currentTime ?? lecture.resumePosition ?? 0;
    const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;

    const glassHoverBg = isDark ? 'rgba(12, 16, 14, 0.26)' : 'rgba(255, 255, 255, 0.22)';

    const styles = React.useMemo(() => getStyles(themeColors), [themeColors]);

    const getStatusVariant = (): StatusVariant | null => {
        switch (lecture.status) {
            case 'ready': return 'ready';
            case 'processing': return 'processing';
            case 'failed': return 'failed';
            case 'transcribing': return 'transcribed';
            case 'segmenting': return 'ready';
            default: return null;
        }
    };

    const statusVariant = getStatusVariant();

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
                    padding="none"
                    radius="card"
                    elevation={hovered ? 'hover' : 'soft'}
                    {...(Platform.OS === 'web' ? {
                        style: StyleSheet.flatten([
                            styles.container,
                            {
                                transition: `transform ${motion.durationBase}ms ${motion.easeInOut}, background-color ${motion.durationBase}ms ${motion.easeInOut}, border-color ${motion.durationBase}ms ${motion.easeInOut}`,
                                transform: hovered ? `translateY(${motion.cardLiftY}px)` : pressed ? 'scale(0.98)' : 'none',
                                ...(cardStyle === 'transparent' && hovered ? { backgroundColor: glassHoverBg } : {}),
                            } as any,
                        ]),
                    } : {
                        style: StyleSheet.flatten([
                            styles.container,
                            pressed && styles.pressed,
                            hovered && styles.hovered,
                        ]),
                    })}
                >
                    <View style={styles.imageContainer}>
                        {lecture.thumbnailUrl ? (
                            <Image
                                source={{ uri: lecture.thumbnailUrl }}
                                style={styles.image}
                                resizeMode="cover"
                            />
                        ) : (
                            <View style={[styles.image, styles.fallbackImage]}>
                                <View style={styles.fallbackIcon}>
                                    <View style={styles.fallbackTriangle} />
                                </View>
                            </View>
                        )}

                        <View style={styles.durationBadge}>
                            <Typography variant="chip" color="#FFFFFF">
                                {formatDuration(lecture.duration)}
                            </Typography>
                        </View>
                    </View>

                    <View style={styles.content}>
                        <Typography variant="headingMd" color={themeColors.textPrimary} style={styles.title} numberOfLines={2}>
                            {lecture.title}
                        </Typography>

                        <View style={styles.metaRow}>
                            <Typography variant="bodySm" color={themeColors.textSecondary} style={styles.meta} numberOfLines={1}>
                                {new Date(lecture.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} • {formatDuration(lecture.duration)}
                            </Typography>
                        </View>

                        <View style={styles.footer}>
                            {statusVariant && <StatusChip variant={statusVariant} />}
                            {progressPercent > 0 && (
                                <View style={styles.progressRow}>
                                    <View style={styles.progressBarBg}>
                                        <View style={[styles.progressBarFill, { width: `${progressPercent}%` }]} />
                                        <View style={[styles.progressHandle, { left: `${progressPercent}%` }]} />
                                    </View>
                                </View>
                            )}
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
    },
    hovered: {
        transform: [{ translateY: -2 }],
    },
    pressed: {
        transform: [{ scale: 0.98 }],
        opacity: 0.95,
    },
    imageContainer: {
        width: '100%',
        aspectRatio: 16 / 9,
        backgroundColor: themeColors.borderSubtle,
        position: 'relative',
        overflow: 'hidden',
        borderTopLeftRadius: theme.radii.card,
        borderTopRightRadius: theme.radii.card,
        borderBottomLeftRadius: 4,
        borderBottomRightRadius: 4,
    },
    image: {
        ...StyleSheet.absoluteFillObject,
        width: '100%',
        height: '100%',
        ...(Platform.OS === 'web'
            ? ({ objectFit: 'cover', objectPosition: 'center center' } as any)
            : {}),
    },
    fallbackImage: {
        backgroundColor: themeColors.surfaceElevated,
        alignItems: 'center',
        justifyContent: 'center',
    },
    fallbackIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: themeColors.surfaceBase,
        alignItems: 'center',
        justifyContent: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 8,
        elevation: 2,
    },
    fallbackTriangle: {
        width: 0,
        height: 0,
        backgroundColor: 'transparent',
        borderStyle: 'solid',
        borderLeftWidth: 14,
        borderRightWidth: 0,
        borderBottomWidth: 10,
        borderTopWidth: 10,
        borderLeftColor: themeColors.borderSubtle,
        borderRightColor: 'transparent',
        borderBottomColor: 'transparent',
        borderTopColor: 'transparent',
        marginLeft: 4, // Opic centre align
    },
    durationBadge: {
        position: 'absolute',
        bottom: theme.spacing[12],
        right: theme.spacing[12],
        backgroundColor: 'rgba(26, 43, 46, 0.75)',
        paddingHorizontal: theme.spacing[8],
        paddingVertical: theme.spacing[4],
        borderRadius: theme.radii.pill,
    },
    content: {
        padding: theme.spacing[24],
        flex: 1,
        justifyContent: 'space-between',
    },
    title: {
        marginBottom: theme.spacing[8],
        lineHeight: 26,
        height: 52, // Force exact 2 lines height for standardisation
    },
    metaRow: {
        marginBottom: theme.spacing[16],
    },
    meta: {
        letterSpacing: 0.2,
    },
    footer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: theme.spacing[12],
        marginTop: 'auto',
    },
    progressRow: {
        flex: 1,
    },
    progressBarBg: {
        height: 4,
        backgroundColor: themeColors.borderSubtle,
        borderRadius: theme.radii.pill,
        position: 'relative',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: themeColors.primaryEmerald,
        borderRadius: theme.radii.pill,
    },
    progressHandle: {
        position: 'absolute',
        top: -6,
        width: 16,
        height: 16,
        borderRadius: 8,
        backgroundColor: themeColors.surfaceBase,
        borderWidth: 2,
        borderColor: themeColors.primaryEmerald,
        marginLeft: -8,
    },
});
