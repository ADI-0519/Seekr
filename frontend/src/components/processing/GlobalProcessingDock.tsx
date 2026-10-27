import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, StyleSheet, Pressable, Platform, ScrollView, Animated, Easing } from 'react-native';
import { usePathname, useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, ChevronDown, ChevronUp, Loader2, X } from 'lucide-react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design';
import { useThemeColors } from '../../theme/ThemeProvider';
import { Lecture, UploadStage, UploadStatus } from '../../types';
import { useLectures, useUploadStatusPolling } from '../../hooks';
import { useBreakpointValue } from '../../hooks/useBreakpoint';
import { getStageProgress } from '../../services/uploadStatus';
import { useLectureStatusStore, applyEffectiveLectureStatus } from '../../store';

type DockStatus = 'processing' | 'ready' | 'failed';

type DockLectureEntry = {
    lecture: Lecture;
    status: DockStatus;
    observedAt: number;
};

const MAX_RESOLVED_DOCK_ITEMS = 6;

const RotatingIcon = ({ color, size = 16 }: { color: string; size?: number }) => {
    const spin = React.useRef(new Animated.Value(0)).current;

    useEffect(() => {
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
    }, [spin]);

    const spinStyle = {
        transform: [{
            rotate: spin.interpolate({
                inputRange: [0, 1],
                outputRange: ['0deg', '360deg'],
            }),
        }],
    };

    return (
        <Animated.View style={spinStyle}>
            <Loader2 color={color} size={size} />
        </Animated.View>
    );
};

function normalizeLectureStatus(status: Lecture['status']): DockStatus {
    if (status === 'failed') return 'failed';
    if (status === 'ready') return 'ready';
    return 'processing';
}

function getFallbackUploadStatus(lecture: Lecture): UploadStatus {
    const stage: UploadStage | null =
        lecture.status === 'transcribing'
            ? 'transcribing'
            : lecture.status === 'segmenting'
                ? 'segmenting'
                : null;

    return {
        lectureId: lecture.id,
        state: 'running',
        stage,
        progress: getStageProgress('running', stage),
        errorMessage: null,
        transcriptionStage: null,
        slidesStage: null,
    };
}

function getStageLabel(status: UploadStatus) {
    if (status.state === 'queued') return 'Queued';
    if (status.state === 'failed') return 'Failed';
    if (status.state === 'done') return 'Ready';

    switch (status.stage) {
        case 'extracting_audio':
            return 'Preparing audio';
        case 'parallel_processing':
            return 'Processing assets';
        case 'transcribing':
            return 'Transcribing';
        case 'extracting_slides':
            return 'Extracting slides';
        case 'segmenting':
            return 'Building topics';
        case 'summarising':
            return 'Summarising';
        case 'embedding':
            return 'Indexing search';
        default:
            return 'Processing';
    }
}

function parseTimestamp(value: string) {
    const parsed = new Date(value).getTime();
    return Number.isFinite(parsed) ? parsed : 0;
}

function getHeaderIndicator({
    processingCount,
    failedCount,
    themeColors,
}: {
    processingCount: number;
    failedCount: number;
    themeColors: ReturnType<typeof useThemeColors>;
}) {
    if (processingCount > 0) {
        return {
            Icon: Loader2,
            color: themeColors.info,
            backgroundColor: themeColors.chipBgProcessing,
        };
    }

    if (failedCount > 0) {
        return {
            Icon: AlertCircle,
            color: themeColors.error,
            backgroundColor: themeColors.chipBgFailed,
        };
    }

    return {
        Icon: CheckCircle2,
        color: themeColors.primaryEmerald,
        backgroundColor: themeColors.chipBgReady,
    };
}

function ProcessingDockItem({
    entry,
    onResolved,
}: {
    entry: DockLectureEntry;
    onResolved: (lectureId: string, status: 'ready' | 'failed') => void;
}) {
    const router = useRouter();
    const queryClient = useQueryClient();
    const themeColors = useThemeColors();
    const { status } = useUploadStatusPolling(entry.lecture.id, true);
    const terminalHandledRef = useRef(false);
    const hasLiveStatus = status !== null;
    const effectiveStatus = status ?? getFallbackUploadStatus(entry.lecture);
    const progress = Math.max(6, Math.min(100, Math.round(effectiveStatus.progress)));
    const isProcessing = effectiveStatus.state === 'queued' || effectiveStatus.state === 'running';

    useEffect(() => {
        if (terminalHandledRef.current) return;
        if (!status || (status.state !== 'done' && status.state !== 'failed')) return;

        terminalHandledRef.current = true;
        onResolved(entry.lecture.id, status.state === 'done' ? 'ready' : 'failed');

        queryClient.invalidateQueries({ queryKey: ['lectures'] });
        queryClient.invalidateQueries({ queryKey: ['lecture', entry.lecture.id] });
        queryClient.invalidateQueries({ queryKey: ['transcript', entry.lecture.id] });
        queryClient.invalidateQueries({ queryKey: ['topics', entry.lecture.id] });
        queryClient.invalidateQueries({ queryKey: ['slides', entry.lecture.id] });
        queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
    }, [entry.lecture.id, onResolved, queryClient, status]);

    return (
        <Pressable
            onPress={() => router.push(`/lectures/${entry.lecture.id}`)}
            style={({ pressed }) => [
                styles.item,
                {
                    backgroundColor: themeColors.surfaceElevated,
                    borderColor: themeColors.borderSubtle,
                },
                pressed && { opacity: 0.8 },
            ]}
        >
            <View style={styles.itemHeader}>
                <View style={styles.itemText}>
                    <Typography variant="bodySm" style={styles.itemTitle} numberOfLines={1}>
                        {entry.lecture.title}
                    </Typography>
                    <Typography variant="meta" color={themeColors.textSecondary}>
                        {hasLiveStatus ? getStageLabel(effectiveStatus) : 'Checking status'}
                    </Typography>
                </View>
                <View style={styles.itemMeta}>
                    {isProcessing && (
                        <RotatingIcon color={themeColors.primaryEmerald} size={14} />
                    )}
                    <Typography variant="meta" color={themeColors.textSecondary}>
                        {hasLiveStatus ? `${progress}%` : '...'}
                    </Typography>
                </View>
            </View>

            <View style={[styles.track, { backgroundColor: themeColors.borderSubtle }]}>
                <View
                    style={[
                        styles.fill,
                        {
                            width: `${progress}%`,
                            backgroundColor: hasLiveStatus ? themeColors.primaryEmerald : themeColors.textSecondary,
                        },
                    ]}
                />
            </View>
        </Pressable>
    );
}

function ResolvedDockItem({ entry }: { entry: DockLectureEntry }) {
    const router = useRouter();
    const themeColors = useThemeColors();
    const accentColor = entry.status === 'ready' ? themeColors.primaryEmerald : themeColors.error;

    return (
        <Pressable
            onPress={() => router.push(`/lectures/${entry.lecture.id}`)}
            style={({ pressed }) => [
                styles.item,
                {
                    backgroundColor: themeColors.surfaceElevated,
                    borderColor: themeColors.borderSubtle,
                },
                pressed && { opacity: 0.8 },
            ]}
        >
            <View style={styles.itemHeader}>
                <View style={styles.itemText}>
                    <Typography variant="bodySm" style={styles.itemTitle} numberOfLines={1}>
                        {entry.lecture.title}
                    </Typography>
                    <Typography variant="meta" color={themeColors.textSecondary}>
                        {entry.status === 'ready' ? 'Lecture ready' : 'Processing failed'}
                    </Typography>
                </View>
                <Typography variant="meta" color={accentColor}>
                    {entry.status === 'ready' ? 'Ready' : 'Failed'}
                </Typography>
            </View>

            <View style={[styles.track, { backgroundColor: themeColors.borderSubtle }]}>
                <View
                    style={[
                        styles.fill,
                        {
                            width: '100%',
                            backgroundColor: accentColor,
                        },
                    ]}
                />
            </View>
        </Pressable>
    );
}

export const GlobalProcessingDock: React.FC = () => {
    const pathname = usePathname();
    const { data: lecturesData } = useLectures();
    const queryClient = useQueryClient();
    const themeColors = useThemeColors();
    const { overrides, hydrated, hydrate, setOverride, pruneOverrides } = useLectureStatusStore();
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });
    const isDashboardRoute = pathname === '/dashboard';
    const layoutStyle = useBreakpointValue({
        sm: { top: 16, left: 16, right: 16 },
        md: { top: 24, right: 24, width: 320 },
        lg: { top: 24, right: 24, width: 320 },
        xl: { top: 24, right: 24, width: 320 },
    });
    const maxListHeight = useBreakpointValue({
        sm: 320,
        md: 260,
        lg: 280,
        xl: 300,
    });
    const [expanded, setExpanded] = useState(false);
    const [dismissed, setDismissed] = useState(false);
    const [dismissedProcessingKey, setDismissedProcessingKey] = useState<string | null>(null);
    const [isHovered, setIsHovered] = useState(false);

    useEffect(() => {
        void hydrate();
    }, [hydrate]);

    useEffect(() => {
        if (!hydrated || !lecturesData?.items) return;
        pruneOverrides(lecturesData.items);
    }, [hydrated, lecturesData?.items, pruneOverrides]);

    const dockEntries = useMemo(() => {
        const items = lecturesData?.items || [];
        const allEntries = items
            .map((lecture): DockLectureEntry => {
                const effectiveLecture = applyEffectiveLectureStatus(lecture, overrides);
                const override = overrides[lecture.id];
                const status = normalizeLectureStatus(effectiveLecture.status);
                const observedAt = override?.observedAt ?? parseTimestamp(effectiveLecture.updatedAt || effectiveLecture.createdAt);

                return {
                    lecture: effectiveLecture,
                    status,
                    observedAt,
                };
            });

        const processingEntries = allEntries
            .filter((entry) => entry.status === 'processing')
            .sort((a, b) => b.observedAt - a.observedAt);

        const resolvedEntries = allEntries
            .filter((entry) => entry.status !== 'processing')
            .sort((a, b) => b.observedAt - a.observedAt)
            .slice(0, MAX_RESOLVED_DOCK_ITEMS);

        return [...processingEntries, ...resolvedEntries];
    }, [lecturesData?.items, overrides]);

    const processingEntries = dockEntries.filter((entry) => entry.status === 'processing');
    const readyEntries = dockEntries.filter((entry) => entry.status === 'ready');
    const failedEntries = dockEntries.filter((entry) => entry.status === 'failed');
    const totalVisibleItems = dockEntries.length;
    const processingKey = processingEntries.map((entry) => entry.lecture.id).sort().join('|');
    const headerIndicator = getHeaderIndicator({
        processingCount: processingEntries.length,
        failedCount: failedEntries.length,
        themeColors,
    });

    useEffect(() => {
        if (totalVisibleItems === 0) {
            setExpanded(false);
        }
    }, [totalVisibleItems]);

    useEffect(() => {
        if (!dismissed) return;
        if (processingEntries.length === 0) return;
        if (!dismissedProcessingKey) return;
        if (processingKey !== dismissedProcessingKey) {
            setDismissed(false);
            setDismissedProcessingKey(null);
        }
    }, [dismissed, dismissedProcessingKey, processingEntries.length, processingKey]);

    useEffect(() => {
        if (processingEntries.length === 0) return;

        const interval = setInterval(() => {
            queryClient.invalidateQueries({ queryKey: ['lectures'] });
            queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
        }, 5000);

        return () => clearInterval(interval);
    }, [processingEntries.length, queryClient]);

    const handleResolved = (lectureId: string, status: 'ready' | 'failed') => {
        setOverride(lectureId, status, Date.now());
    };

    if (!hydrated || totalVisibleItems === 0 || dismissed || (isDashboardRoute && !isMobile)) {
        return null;
    }

    return (
        <View pointerEvents="box-none" style={[styles.container, layoutStyle]}>
            <FloatingShell
                padding="none"
                radius="card"
                elevation="hover"
                style={[
                    styles.shell,
                    Platform.OS === 'web' && ({ backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)' } as any),
                ]}
                glass
                {...(Platform.OS === 'web'
                    ? ({
                        onMouseEnter: () => setIsHovered(true),
                        onMouseLeave: () => setIsHovered(false),
                    } as any)
                    : {})}
            >
                <Pressable
                    onPress={() => setExpanded((value) => !value)}
                    style={({ pressed }) => [
                        styles.header,
                        { borderBottomColor: expanded ? themeColors.borderSubtle : 'transparent' },
                        pressed && { opacity: 0.85 },
                    ]}
                >
                    <View style={styles.headerLeft}>
                        <View style={[styles.spinnerBadge, { backgroundColor: headerIndicator.backgroundColor }]}>
                            {processingEntries.length > 0 ? (
                                <RotatingIcon color={headerIndicator.color} size={16} />
                            ) : (
                                <headerIndicator.Icon color={headerIndicator.color} size={16} />
                            )}
                        </View>
                        <View>
                            <Typography variant="bodyMd" style={styles.headerTitle}>
                                Lecture Updates
                            </Typography>
                            <Typography variant="meta" color={themeColors.textSecondary}>
                                {readyEntries.length} ready, {processingEntries.length} processing{failedEntries.length ? `, ${failedEntries.length} failed` : ''}
                            </Typography>
                        </View>
                    </View>
                    <View style={styles.headerRight}>
                        {(isHovered || isMobile) && (
                            <Pressable
                                onPress={(event) => {
                                    event.stopPropagation();
                                    setDismissed(true);
                                    setDismissedProcessingKey(processingKey || null);
                                    setExpanded(false);
                                }}
                                hitSlop={8}
                                style={({ pressed }) => [
                                    styles.closeButton,
                                    { borderColor: themeColors.borderSubtle },
                                    pressed && { opacity: 0.7 },
                                ]}
                            >
                                <X color={themeColors.textSecondary} size={14} />
                            </Pressable>
                        )}
                        {expanded ? (
                            <ChevronUp color={themeColors.textSecondary} size={18} />
                        ) : (
                            <ChevronDown color={themeColors.textSecondary} size={18} />
                        )}
                    </View>
                </Pressable>

                <View
                    style={[styles.listWrapper, !expanded && styles.listHidden]}
                    pointerEvents={expanded ? 'auto' : 'none'}
                >
                    <ScrollView
                        style={{ maxHeight: maxListHeight }}
                        contentContainerStyle={styles.list}
                        showsVerticalScrollIndicator={true}
                    >
                        {dockEntries.map((entry) => (
                            entry.status === 'processing' ? (
                                <ProcessingDockItem
                                    key={entry.lecture.id}
                                    entry={entry}
                                    onResolved={handleResolved}
                                />
                            ) : (
                                <ResolvedDockItem
                                    key={entry.lecture.id}
                                    entry={entry}
                                />
                            )
                        ))}
                    </ScrollView>
                </View>
            </FloatingShell>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        zIndex: 120,
    },
    shell: {
        width: '100%',
        overflow: 'hidden',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: theme.spacing[16],
        paddingVertical: theme.spacing[16],
        borderBottomWidth: 1,
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
        marginRight: theme.spacing[12],
    },
    spinnerBadge: {
        width: 32,
        height: 32,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: theme.spacing[12],
    },
    headerTitle: {
        fontWeight: '700',
    },
    headerRight: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
    },
    closeButton: {
        width: 24,
        height: 24,
        borderRadius: 12,
        borderWidth: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    listWrapper: {
        overflow: 'hidden',
    },
    list: {
        padding: theme.spacing[12],
        gap: theme.spacing[8],
    },
    listHidden: {
        display: 'none',
    },
    item: {
        borderWidth: 1,
        borderRadius: theme.radii.controlSm,
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[12],
    },
    itemHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[8],
        gap: theme.spacing[12],
    },
    itemText: {
        flex: 1,
    },
    itemMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
    },
    itemTitle: {
        fontWeight: '600',
        marginBottom: 2,
    },
    track: {
        height: 6,
        borderRadius: theme.radii.pill,
        overflow: 'hidden',
    },
    fill: {
        height: '100%',
        borderRadius: theme.radii.pill,
    },
});
