import { useState, useEffect, useRef } from 'react';
import { AnimatedPage } from '../../src/design/primitives/AnimatedPage';
import { View, StyleSheet, ScrollView, Platform, Alert } from 'react-native';
import { TopHeroShell } from '../../src/components/shell/TopHeroShell';
import { Footer } from '../../src/components/shell/Footer';
import { ContinueWatchingCard } from '../../src/components/cards/ContinueWatchingCard';
import { LectureCard } from '../../src/components/cards/LectureCard';
import { ProcessingCard } from '../../src/components/cards/ProcessingCard';
import { SectionHeader } from '../../src/design/primitives/SectionHeader';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { theme } from '../../src/design/index';
import { BookOpen, Loader, UploadCloud, Activity } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useLectures, useAuth, useUploadStatusPolling, useCancelUpload } from '../../src/hooks';
import { Typography } from '../../src/components/ui/Typography';
import { PrimaryButton } from '../../src/components/ui/PrimaryButton';
import { useQueryClient } from '@tanstack/react-query';
import { useBreakpointValue } from '../../src/hooks/useBreakpoint';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { Lecture, UploadStatus } from '../../src/types';
import { getStageProgress } from '../../src/services/uploadStatus';
import { getResponsiveGridItemStyle, getWebStaggerStyle } from '@/utils/responsiveGrid';

const STALE_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes

function getFallbackProcessingStatus(lecture: Lecture): UploadStatus {
    const fallbackStage =
        lecture.status === 'transcribing'
            ? 'transcribing'
            : lecture.status === 'segmenting'
                ? 'segmenting'
                : null;

    return {
        lectureId: lecture.id,
        state: 'running',
        stage: fallbackStage,
        progress: getStageProgress('running', fallbackStage),
        errorMessage: null,
        transcriptionStage: null,
        slidesStage: null,
    };
}

function ProcessingActivityItem({
    lecture,
    isStale,
    onOpen,
    onCancel,
}: {
    lecture: Lecture;
    isStale: boolean;
    onOpen: () => void;
    onCancel: () => void;
}) {
    const { status } = useUploadStatusPolling(lecture.id, true);

    return (
        <ProcessingCard
            title={lecture.title}
            isStale={isStale}
            onCancel={onCancel}
            onPress={onOpen}
            status={status ?? getFallbackProcessingStatus(lecture)}
        />
    );
}

export default function HomeScreen() {
    const router = useRouter();
    const { user } = useAuth();
    const { data: lecturesData, isLoading } = useLectures();
    const cancelMutation = useCancelUpload();
    const queryClient = useQueryClient();
    const themeColors = useThemeColors();

    const isDesktop = useBreakpointValue({ sm: false, md: false, lg: true, xl: true });
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });
    const gridCols = useBreakpointValue({ sm: 1, md: 2, lg: 3, xl: 4 });

    const allLectures = lecturesData?.items || [];
    const readyLectures = allLectures.filter(l => l.status === 'ready');
    const processingLectures = allLectures.filter(l =>
        l.status === 'processing' || l.status === 'transcribing' || l.status === 'segmenting'
    );

    const sortedReady = [...readyLectures].sort((a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
    const latestLecture = sortedReady[0];
    const otherRecent = sortedReady.slice(1, 9);

    const processingSignature = processingLectures
        .map((lecture) => `${lecture.id}:${lecture.status}`)
        .sort()
        .join('|');

    const [staleMap, setStaleMap] = useState<Record<string, boolean>>({});
    const lastStatusMap = useRef<Record<string, { stage: string; time: number }>>({});

    useEffect(() => {
        if (processingLectures.length === 0) return;

        const interval = setInterval(() => {
            queryClient.invalidateQueries({ queryKey: ['lectures'] });

            const now = Date.now();
            const newStaleMap: Record<string, boolean> = {};
            processingLectures.forEach(l => {
                const prev = lastStatusMap.current[l.id];
                if (prev && prev.stage === l.status && (now - prev.time) > STALE_THRESHOLD_MS) {
                    newStaleMap[l.id] = true;
                } else if (!prev || prev.stage !== l.status) {
                    lastStatusMap.current[l.id] = { stage: l.status, time: now };
                }
            });
            setStaleMap(newStaleMap);
        }, 5000);

        return () => clearInterval(interval);
    }, [processingSignature, queryClient]);

    const handleCancel = async (lectureId: string, lectureTitle: string) => {
        const runCancel = async () => {
            try {
                clearStaleEntry(lectureId);
                await cancelMutation.mutateAsync(lectureId);
            } catch (error: unknown) {
                const message = error instanceof Error ? error.message : 'Failed to cancel this processing job.';
                if (Platform.OS === 'web' && typeof window !== 'undefined') {
                    window.alert(`Cancel Failed\n\n${message}`);
                    return;
                }
                Alert.alert('Cancel Failed', message);
            }
        };

        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            if (window.confirm(`Cancel processing for "${lectureTitle}"? The lecture will be removed.`)) {
                void runCancel();
            }
            return;
        }

        Alert.alert(
            'Cancel Processing',
            `Cancel processing for "${lectureTitle}"? The lecture will be removed.`,
            [
                { text: 'Keep Processing', style: 'cancel' },
                { text: 'Cancel Lecture', style: 'destructive', onPress: () => void runCancel() },
            ]
        );
    };

    const clearStaleEntry = (lectureId: string) => {
        if (!staleMap[lectureId] && !lastStatusMap.current[lectureId]) {
            return;
        }

        setStaleMap((current) => {
            const { [lectureId]: _removed, ...remaining } = current;
            return remaining;
        });
        delete lastStatusMap.current[lectureId];
    };

    const hasLibraryContent = allLectures.length > 0;

    const renderRightRail = () => (
        <View style={isDesktop ? styles.activityColumn : styles.activityColumnMobile}>
            <SectionHeader title="Processing Activity" />
            <FloatingShell padding={24} style={styles.activityShell}>
                {processingLectures.length > 0 ? (
                    <View style={{ gap: 16 }}>
                        {processingLectures.map(lecture => (
                            <ProcessingActivityItem
                                key={lecture.id}
                                lecture={lecture}
                                isStale={!!staleMap[lecture.id]}
                                onCancel={() => void handleCancel(lecture.id, lecture.title)}
                                onOpen={() => router.push(`/lectures/${lecture.id}`)}
                            />
                        ))}
                    </View>
                ) : (
                    <View style={styles.emptyActivity}>
                        <View style={styles.emptyActivityIcon}>
                            <Loader color={themeColors.borderSubtle} size={24} />
                        </View>
                        <Typography variant="bodyMd" color={themeColors.textSecondary} style={styles.emptyActivityText}>
                            System Idle
                        </Typography>
                        <Typography variant="bodySm" color={themeColors.textSecondary} style={styles.emptyActivitySubtext}>
                            Upload a lecture to see real-time extraction
                        </Typography>
                    </View>
                )}
            </FloatingShell>

            <SectionHeader title="Quick Stats" style={{ marginTop: 48 }} />
            <FloatingShell padding={24}>
                <View style={styles.statRow}>
                    <BookOpen color={themeColors.textSecondary} size={18} />
                    <Typography variant="bodyLg" style={{ marginLeft: 12, flex: 1 }}>
                        Ready Lectures
                    </Typography>
                    <Typography variant="headingMd" style={styles.statValue}>
                        {readyLectures.length}
                    </Typography>
                </View>
                <View style={[styles.statRow, { marginTop: 16 }]}>
                    <Activity color={themeColors.textSecondary} size={18} />
                    <Typography variant="bodyLg" style={{ marginLeft: 12, flex: 1 }}>
                        Processing
                    </Typography>
                    <Typography variant="headingMd" style={styles.statValue}>
                        {processingLectures.length}
                    </Typography>
                </View>
            </FloatingShell>
        </View>
    );

    return (
        <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={[styles.scrollContent, isMobile && { paddingBottom: 100 }]}
        >
            <AnimatedPage style={[styles.innerContent, isMobile && { paddingTop: 16 }]}>
                <View style={styles.mainSection}>
                    <TopHeroShell userName={user?.displayName || 'Seekr'} />

                    <View style={isDesktop ? styles.mainLayoutDesktop : styles.mainLayoutMobile}>
                        <View style={styles.contentColumn}>
                            {latestLecture && (
                                <>
                                    <SectionHeader title="Continue Watching" />
                                    <View style={styles.sectionGap}>
                                        <ContinueWatchingCard
                                            lecture={latestLecture}
                                            onPress={() => router.push(`/lectures/${latestLecture.id}`)}
                                        />
                                    </View>
                                </>
                            )}

                            {otherRecent.length > 0 && (
                                <>
                                    <SectionHeader title="Recent Lectures" />
                                    <View style={styles.gridContainer}>
                                        {otherRecent.map((lecture, index) => (
                                            <View
                                                key={lecture.id}
                                                style={[
                                                    getResponsiveGridItemStyle({ gridCols }),
                                                    getWebStaggerStyle({
                                                        index,
                                                        maxAnimatedItems: gridCols,
                                                        fillMode: 'backwards',
                                                    }),
                                                ]}
                                            >
                                                <LectureCard lecture={lecture} onPress={() => router.push(`/lectures/${lecture.id}`)} />
                                            </View>
                                        ))}
                                    </View>
                                </>
                            )}

                            {!isLoading && !hasLibraryContent && (
                                <>
                                    <SectionHeader title="Library" />
                                    <View style={styles.sectionGap}>
                                        <FloatingShell padding={48} style={styles.emptyShell}>
                                            <View style={styles.emptyIconCircle}>
                                                <BookOpen color={themeColors.primaryEmerald} size={32} />
                                            </View>
                                            <Typography variant="headingMd" style={styles.emptyTitle}>
                                                Your library is empty
                                            </Typography>
                                            <Typography variant="bodyMd" color={themeColors.textSecondary} style={styles.emptyBody}>
                                                Upload your first lecture to get started. We'll transcribe, segment, and index it automatically.
                                            </Typography>
                                            <PrimaryButton
                                                label="Upload Lecture"
                                                icon={UploadCloud}
                                                onPress={() => router.push('/upload')}
                                                style={{ marginTop: 24 }}
                                            />
                                        </FloatingShell>
                                    </View>
                                </>
                            )}
                        </View>

                        {renderRightRail()}
                    </View>
                </View>
                <Footer />
            </AnimatedPage>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scrollContent: {
        paddingBottom: 24,
        flexGrow: 1,
    },
    innerContent: {
        paddingTop: 24,
        paddingHorizontal: 16,
        overflow: 'visible',
        flex: 1,
        minHeight: '100%',
    },
    mainLayoutDesktop: {
        flexDirection: 'row',
        gap: 32,
    },
    mainLayoutMobile: {
        flexDirection: 'column',
        gap: 32,
    },
    mainSection: {
        flex: 1,
        paddingBottom: theme.spacing[64] + theme.spacing[32],
    },
    contentColumn: {
        flex: 1,
    },
    sectionGap: {
        paddingBottom: 12,
        marginBottom: 8,
    },
    gridContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 24,
        paddingBottom: 24,
    },
    activityColumn: {
        width: 360,
        flexShrink: 0,
    },
    activityColumnMobile: {
        width: '100%',
    },
    activityShell: {
        minHeight: 180,
    },
    emptyShell: {
        alignItems: 'center',
    },
    emptyIconCircle: {
        width: 72,
        height: 72,
        borderRadius: 36,
        backgroundColor: theme.colors.chipBgReady,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 20,
    },
    emptyTitle: {
        marginBottom: 8,
        textAlign: 'center',
    },
    emptyBody: {
        textAlign: 'center',
        maxWidth: 360,
        lineHeight: 24,
    },
    emptyActivity: {
        alignItems: 'center',
        paddingVertical: 24,
    },
    emptyActivityIcon: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: theme.colors.surfaceElevated,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 12,
    },
    emptyActivityText: {
        textAlign: 'center',
    },
    emptyActivitySubtext: {
        textAlign: 'center',
        opacity: 0.7,
        marginTop: 4,
    },
    statRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    statValue: {
        minWidth: 24,
        textAlign: 'right',
        fontVariant: ['tabular-nums'],
    },
});
