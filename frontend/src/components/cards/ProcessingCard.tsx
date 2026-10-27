import React, { useState } from 'react';
import { View, StyleSheet, Pressable, Platform, Animated, Easing } from 'react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design/index';
import { motion } from '../../design/tokens/motion';
import { UploadStatus } from '../../types';
import { Mic, Image as ImageIcon, CheckCircle, AlertCircle, Loader2, XCircle, Clock } from 'lucide-react-native';
import { useThemeColors } from '../../theme/ThemeProvider';

interface ProcessingCardProps {
    title: string;
    status: UploadStatus;
    isStale?: boolean; // True if status hasn't changed in >10 minutes
    onPress?: () => void;
    onCancel?: () => void;
}

const PROCESSING_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes

export const ProcessingCard: React.FC<ProcessingCardProps> = ({ title, status, isStale, onPress, onCancel }) => {
    const [hovered, setHovered] = useState(false);
    const themeColors = useThemeColors();
    const spin = React.useRef(new Animated.Value(0)).current;

    const styles = React.useMemo(() => getStyles(themeColors), [themeColors]);
    const shouldSpinIcon = status.state === 'queued' || status.state === 'running';

    React.useEffect(() => {
        if (!shouldSpinIcon) {
            spin.stopAnimation();
            spin.setValue(0);
            return;
        }

        const loop = Animated.loop(
            Animated.timing(spin, {
                toValue: 1,
                duration: 1200,
                easing: Easing.linear,
                useNativeDriver: Platform.OS !== 'web',
            })
        );

        loop.start();
        return () => loop.stop();
    }, [shouldSpinIcon, spin]);

    const spinStyle = {
        transform: [{
            rotate: spin.interpolate({
                inputRange: [0, 1],
                outputRange: ['0deg', '360deg'],
            }),
        }],
    };

    const getVisuals = () => {
        if (status.state === 'failed') {
            return {
                icon: <AlertCircle color={themeColors.error} size={24} />,
                iconBg: themeColors.chipBgFailed,
                color: themeColors.error,
                label: 'Failed',
            };
        }

        if (status.state === 'done') {
            return {
                icon: <CheckCircle color={themeColors.success} size={24} />,
                iconBg: themeColors.chipBgReady,
                color: themeColors.success,
                label: 'Complete',
            };
        }

        if (isStale) {
            return {
                icon: <Clock color={themeColors.warning} size={24} />,
                iconBg: '#FFFBEB',
                color: themeColors.warning,
                label: 'PROCESSING DELAYED',
            };
        }

        if (status.state === 'queued') {
            return {
                icon: <Clock color={themeColors.textSecondary} size={24} />,
                iconBg: themeColors.surfaceElevated,
                color: themeColors.textSecondary,
                label: 'QUEUED...',
            };
        }

        switch (status.stage) {
            case 'extracting_audio':
            case 'transcribing':
                return {
                    icon: <Mic color={themeColors.warning} size={24} />,
                    iconBg: '#FFFBEB',
                    color: themeColors.warning,
                    label: 'TRANSCRIBING AUDIO...',
                };
            case 'extracting_slides':
                return {
                    icon: <ImageIcon color={themeColors.info} size={24} />,
                    iconBg: themeColors.chipBgProcessing,
                    color: themeColors.info,
                    label: 'EXTRACTING SLIDES...',
                };
            case 'embedding':
                return {
                    icon: <Loader2 color={themeColors.info} size={24} />,
                    iconBg: themeColors.chipBgProcessing,
                    color: themeColors.info,
                    label: 'INDEXING FOR SEARCH...',
                };
            case 'segmenting':
                return {
                    icon: <Loader2 color={themeColors.primaryEmerald} size={24} />,
                    iconBg: themeColors.chipBgReady,
                    color: themeColors.primaryEmerald,
                    label: 'SEGMENTING...',
                };
            case 'summarising':
                return {
                    icon: <Loader2 color={themeColors.primaryEmerald} size={24} />,
                    iconBg: themeColors.chipBgReady,
                    color: themeColors.primaryEmerald,
                    label: 'GENERATING SUMMARY...',
                };
            case 'parallel_processing':
                return {
                    icon: <Loader2 color={themeColors.primaryEmerald} size={24} />,
                    iconBg: themeColors.chipBgReady,
                    color: themeColors.primaryEmerald,
                    label: 'PROCESSING IN PARALLEL...',
                };
            default:
                return {
                    icon: <Loader2 color={themeColors.primaryEmerald} size={24} />,
                    iconBg: themeColors.chipBgReady,
                    color: themeColors.primaryEmerald,
                    label: 'PROCESSING...',
                };
        }
    };

    const visuals = getVisuals();
    const progressText = status.state === 'queued'
        ? 'Waiting for an available worker'
        : status.state === 'running'
            ? `${Math.max(0, Math.min(100, Math.round(status.progress)))}% complete`
            : null;

    return (
        <Pressable
            onPress={onPress}
            disabled={!onPress}
            {...(Platform.OS === 'web' ? {
                onMouseEnter: () => setHovered(true),
                onMouseLeave: () => setHovered(false),
            } as any : {})}
        >
            <FloatingShell
                style={StyleSheet.flatten([
                    styles.container,
                    hovered && styles.hovered,
                    ...(Platform.OS === 'web' ? [{
                        transition: `transform ${motion.durationBase}ms ${motion.easeInOut}`,
                    } as any] : []),
                ])}
                padding={24}
                elevation={hovered ? 'hover' : 'soft'}
            >
                <View style={styles.row}>
                    <View style={[styles.iconContainer, { backgroundColor: visuals.iconBg }]}>
                        {shouldSpinIcon ? (
                            <Animated.View style={spinStyle}>
                                {visuals.icon}
                            </Animated.View>
                        ) : (
                            visuals.icon
                        )}
                    </View>

                    <View style={styles.content}>
                        <Typography variant="headingMd" color={themeColors.textPrimary} style={styles.title} numberOfLines={1}>
                            {title}
                        </Typography>

                        <View style={styles.statusRow}>
                            <View style={[styles.dot, { backgroundColor: visuals.color }]} />
                            <Typography variant="chip" color={visuals.color}>
                                {visuals.label}
                            </Typography>
                        </View>

                        {(status.state === 'queued' || status.state === 'running') && (
                            <>
                                <View style={styles.progressBarBg}>
                                    <View
                                        style={StyleSheet.flatten([
                                            styles.progressBarFill,
                                            {
                                                width: `${status.progress}%` as any,
                                                backgroundColor: visuals.color,
                                            }
                                        ])}
                                    />
                                </View>
                                {progressText && (
                                    <Typography
                                        variant="bodySm"
                                        color={themeColors.textSecondary}
                                        style={styles.progressText}
                                    >
                                        {progressText}
                                    </Typography>
                                )}
                            </>
                        )}

                        {/* Stale/timeout warning */}
                        {isStale && (status.state === 'queued' || status.state === 'running') && (
                            <Typography variant="bodySm" color={themeColors.warning} style={{ marginTop: 8 }}>
                                This job has been processing for a while. You can cancel and retry.
                            </Typography>
                        )}

                        {/* Error message */}
                        {status.state === 'failed' && status.errorMessage && (
                            <Typography variant="bodySm" color={themeColors.error} style={{ marginTop: 8 }} numberOfLines={2}>
                                {status.errorMessage}
                            </Typography>
                        )}
                    </View>

                    {/* Cancel button */}
                    {onCancel && (status.state === 'queued' || status.state === 'running') && (
                        <Pressable
                            onPress={(event) => {
                                event?.stopPropagation?.();
                                onCancel();
                            }}
                            style={styles.cancelBtn}
                            hitSlop={8}
                        >
                            <XCircle color={themeColors.textSecondary} size={20} />
                        </Pressable>
                    )}
                </View>
            </FloatingShell>
        </Pressable>
    );
};

const getStyles = (themeColors: any) => StyleSheet.create({
    container: {
        width: '100%',
    },
    hovered: {
        transform: [{ translateY: -1 }],
    },
    row: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    iconContainer: {
        width: 52,
        height: 52,
        borderRadius: 26,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: theme.spacing[20],
    },
    content: {
        flex: 1,
        justifyContent: 'center',
    },
    title: {
        fontWeight: '600',
        marginBottom: theme.spacing[8],
    },
    statusRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: theme.spacing[12],
    },
    dot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginRight: theme.spacing[8],
    },
    progressBarBg: {
        height: 6,
        backgroundColor: themeColors.borderSubtle,
        borderRadius: theme.radii.pill,
        width: '100%',
        overflow: 'hidden',
    },
    progressBarFill: {
        height: '100%',
        borderRadius: theme.radii.pill,
        transition: 'width 0.3s ease',
    } as any,
    progressText: {
        marginTop: theme.spacing[8],
    },
    cancelBtn: {
        padding: 8,
        marginLeft: 12,
    },
});
