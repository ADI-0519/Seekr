import React, { useState, useEffect, useCallback } from 'react';
import { AnimatedPage } from '../../../src/design/primitives/AnimatedPage';
import { View, ScrollView, Platform, Linking, LogBox } from 'react-native';
import { FloatingShell } from '../../../src/design/primitives/FloatingShell';
import { Typography } from '../../../src/components/ui/Typography';
import { PrimaryButton } from '../../../src/components/ui/PrimaryButton';
import { formatDuration } from '../../../src/utils/formatDuration';
import { useLocalSearchParams, usePathname, useRouter } from 'expo-router';
import { useIsFocused } from '@react-navigation/native';
import { useLecture, useTranscript, useTopics, useGenerateNotes, useSlides, useVideoPlayer, usePlayerShortcuts } from '../../../src/hooks';
import { playerEngine } from '../../../src/player/playerEngine';
import { SlideFrame } from '../../../src/types';
import { useBreakpointValue } from '../../../src/hooks/useBreakpoint';
import { useThemeColors } from '../../../src/theme/ThemeProvider';
import { Footer } from '../../../src/components/shell/Footer';
import { api } from '../../../src/services';
import { authService } from '../../../src/services/auth';
import { API_BASE_URL } from '../../../src/constants/config';
import { AskPanel } from '../../../src/components/lecture-detail/AskPanel';
import { NotesPanel } from '../../../src/components/lecture-detail/NotesPanel';
import { VideoPlayerSurface } from '../../../src/components/lecture-detail/VideoPlayerSurface';
import { TranscriptPanel } from '../../../src/components/lecture-detail/TranscriptPanel';
import { SlidesViewer } from '../../../src/components/lecture-detail/SlidesViewer';
import { SegmentsList } from '../../../src/components/lecture-detail/SegmentsList';
import { PANEL_TAB_ORDER, PanelTabKey, PanelTabsHeader } from '../../../src/components/lecture-detail/PanelTabsHeader';
import { lectureDetailStyles } from '../../../src/components/lecture-detail/lectureDetail.styles';
import { useLecturePlaybackPersistence } from '../../../src/components/lecture-detail/hooks/useLecturePlaybackPersistence';

LogBox.ignoreLogs([
    'VirtualizedLists should never be nested inside plain ScrollViews',
    'Cannot complete operation because the Video component has not yet loaded',
]);

const API_ROOT = `${API_BASE_URL}/api`;


export default function LectureDetailScreen() {
    const { id, t } = useLocalSearchParams<{ id: string; t?: string }>();
    const pathname = usePathname();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<PanelTabKey>('transcript');
    const [isVideoFullscreen, setIsVideoFullscreen] = useState(false);
    const seekTimestamp = t ? parseFloat(t) : null;
    const isFocused = useIsFocused();
    const playbackFocus = Platform.OS === 'web' ? true : isFocused;

    const { data: lectureResponse, isLoading: lectureLoading } = useLecture(id as string);
    const lecture = lectureResponse?.data;
    const { data: transcript } = useTranscript(id as string);
    const { data: topics } = useTopics(id as string);
    const generateNotesMutation = useGenerateNotes(id as string);
    const { data: slidesResponse, isLoading: slidesLoading } = useSlides(id as string);

    const { activeVideo, seekTo, loadSession, updatePlayState } = useVideoPlayer();

    const isDesktop = useBreakpointValue({ sm: false, md: false, lg: true, xl: true });
    const themeColors = useThemeColors();
    const pauseViaEngine = useCallback(() => playerEngine.pause(), []);

    useLecturePlaybackPersistence({
        lectureId: String(id),
        activeVideo,
        isFocused: playbackFocus,
        updatePlayState,
        pauseVideo: pauseViaEngine,
    });

    usePlayerShortcuts();

    useEffect(() => {
        if (lecture && lecture.videoUrl && lecture.status === 'ready') {
            if (activeVideo?.lectureId !== lecture.id) {
                loadSession(lecture, pathname, topics?.data || []);
            }
        }
    }, [lecture?.id, lecture?.videoUrl, lecture?.status, activeVideo?.lectureId, loadSession, pathname, topics?.data]);

    useEffect(() => {
        if (seekTimestamp && activeVideo?.lectureId === id && seekTimestamp > 0) {
            seekTo(seekTimestamp);
        }
    }, [seekTimestamp, activeVideo?.lectureId]);

    if (lectureLoading || !lecture) {
        return (
            <View style={styles.centered}>
                <Typography variant="bodyLg">Loading lecture...</Typography>
            </View>
        );
    }

    if (lecture.status !== 'ready') {
        return (
            <View style={styles.centered}>
                <FloatingShell padding={24} radius="card" elevation="soft" style={{ width: '100%', maxWidth: 560 }}>
                    <Typography variant="headingMd" color={themeColors.textPrimary} style={{ marginBottom: 12 }}>
                        This lecture is still processing
                    </Typography>
                    <Typography variant="bodyMd" color={themeColors.textSecondary} style={{ marginBottom: 20 }}>
                        Player, transcript, and notes become available once processing is complete.
                    </Typography>
                    <View style={{ alignSelf: 'flex-start' }}>
                        <PrimaryButton
                            label="Back to Dashboard"
                            variant="secondary"
                            onPress={() => router.replace('/(app)/dashboard')}
                        />
                    </View>
                </FloatingShell>
            </View>
        );
    }

    const slideItems = slidesResponse?.data || [];
    const hasSlides = slideItems.length > 0;

    const handleDownloadSlides = async () => {
        if (!lecture) return;
        try {
            const token = await authService.getIdToken();
            const url = `${API_ROOT}/videos/${lecture.id}/slides/download`;

            if (Platform.OS === 'web' && typeof window !== 'undefined') {
                const res = await fetch(url, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (!res.ok) throw new Error('Download failed');
                const blob = await res.blob();
                const objectUrl = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = objectUrl;
                a.download = `${lecture.title}-slides.zip`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(objectUrl);
                return;
            }

            // Mobile: Linking can't send headers so append token as query param
            Linking.openURL(`${url}?token=${token}`);
        } catch (err) {
            console.error('Slides download failed:', err);
        }
    };

    const currentTime = activeVideo?.lectureId === id ? activeVideo.currentTime : 0;
    const overviewSummary = lecture.overview || '';
    const activeTabLabel =
        activeTab === 'ask'
            ? 'Ask'
            : activeTab === 'slides'
                ? 'Slides'
                : 'Transcript';

    const renderPanelContent = ({
        compactTranscript = false,
        transcriptPaddingHorizontal = 0,
    }: {
        compactTranscript?: boolean;
        transcriptPaddingHorizontal?: number;
    }) => {
        const activeIndex = PANEL_TAB_ORDER.indexOf(activeTab);

        const getAnimatedPanelStyle = (tab: PanelTabKey) => {
            const tabIndex = PANEL_TAB_ORDER.indexOf(tab);
            const offset = tabIndex < activeIndex ? -32 : tabIndex > activeIndex ? 32 : 0;
            const isActive = tab === activeTab;

            if (Platform.OS !== 'web') {
                return [
                    styles.panelContentLayer,
                    isActive ? styles.panelContentLayerActive : styles.panelContentLayerHidden,
                ];
            }

            return [
                styles.panelContentLayer,
                isActive ? styles.panelContentLayerActive : styles.panelContentLayerInactive,
                {
                    opacity: isActive ? 1 : 0,
                    transform: [{ translateX: offset }],
                    pointerEvents: isActive ? 'auto' : 'none',
                    transition: 'transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 180ms ease-out',
                } as any,
            ];
        };

        return (
            <View style={styles.panelContentViewport}>
                <View style={getAnimatedPanelStyle('transcript')}>
                    <TranscriptPanel
                        segments={transcript?.data || []}
                        currentTime={currentTime}
                        onSeek={seekTo}
                        isFocused={isFocused && activeTab === 'transcript'}
                        contentPaddingHorizontal={transcriptPaddingHorizontal}
                        compact={compactTranscript}
                        styles={styles}
                    />
                </View>
                <View style={getAnimatedPanelStyle('slides')}>
                    <SlidesViewer
                        slides={slideItems as SlideFrame[]}
                        onDownload={handleDownloadSlides}
                        isDownloading={slidesLoading}
                        onSeek={seekTo}
                        styles={styles}
                    />
                </View>
                <View style={getAnimatedPanelStyle('ask')}>
                    <AskPanel lectureId={id as string} onSeek={seekTo} styles={styles} />
                </View>
            </View>
        );
    };

    const renderPanel = () => (
        <FloatingShell
            style={[
                styles.panelShell,
                activeTab === 'transcript' && styles.panelShellTranscript,
                activeTab === 'transcript' && { backgroundColor: themeColors.surfaceBase },
            ]}
            padding="none"
        >
            <PanelTabsHeader activeTab={activeTab} onChange={setActiveTab} styles={styles} />
            {renderPanelContent({})}
        </FloatingShell>
    );

    const renderFullscreenPanel = (onCollapse: () => void) => (
        <View style={[styles.fullscreenPanelContent, { backgroundColor: themeColors.surfaceBase }]}>
            <PanelTabsHeader activeTab={activeTab} onChange={setActiveTab} onClose={onCollapse} styles={styles} />
            {renderPanelContent({ compactTranscript: true, transcriptPaddingHorizontal: 16 })}
        </View>
    );

    return (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
            <AnimatedPage style={styles.innerContent}>
                {/* Header Area */}
                <View style={styles.header}>
                    <Typography variant="displayMd" style={styles.title}>
                        {lecture.title}
                    </Typography>
                    <View style={styles.metaRow}>
                        <Typography variant="bodySm" color={themeColors.textSecondary}>
                            Created {new Date(lecture.createdAt).toLocaleDateString()} | {formatDuration(lecture.duration)}
                        </Typography>
                    </View>
                </View>

                <View style={isDesktop ? styles.mainLayoutDesktop : styles.mainLayoutMobile}>
                    {/* Left Column (Desktop) / Main Column (Mobile) */}
                    <View style={isDesktop ? styles.videoColumn : styles.fullWidthColumn}>
                        <VideoPlayerSurface
                            lecture={lecture}
                            topics={topics?.data || []}
                            fullscreenPanelLabel={activeTabLabel}
                            renderFullscreenPanel={renderFullscreenPanel}
                            onFullscreenChange={setIsVideoFullscreen}
                            styles={styles}
                        />

                        {!isDesktop && (
                            <View style={styles.mobilePanelContainer}>
                                {renderPanel()}
                            </View>
                        )}

                        <FloatingShell style={styles.summaryShell} padding={32}>
                            <Typography variant="headingMd" style={{ marginBottom: 16 }}>
                                Overview
                            </Typography>
                            <Typography variant="bodyLg" color={themeColors.textSecondary} style={{ lineHeight: 28 }}>
                                {overviewSummary || lecture.description || "No description provided for this lecture."}
                            </Typography>
                        </FloatingShell>

                        <FloatingShell style={styles.segmentsShell} padding={32}>
                            <Typography variant="headingMd" style={{ marginBottom: 24 }}>
                                Topics
                            </Typography>
                            <SegmentsList
                                topics={topics?.data || []}
                                currentTime={currentTime}
                                onSeek={seekTo}
                                styles={styles}
                            />
                        </FloatingShell>

                        {/* Notes Section */}
                        <FloatingShell style={styles.notesShell} padding={32}>
                            <NotesPanel
                                lectureId={id as string}
                                lectureTitle={lecture.title}
                                lectureCacheToken={`${lecture.id}:${lecture.createdAt}`}
                                isReady={lecture.status === 'ready'}
                                notesQuery={generateNotesMutation}
                            />
                        </FloatingShell>
                    </View>

                    {isDesktop && !isVideoFullscreen && (
                        <View style={styles.panelColumn}>
                            {renderPanel()}
                        </View>
                    )}
                </View>

                <Footer />
            </AnimatedPage>
        </ScrollView>
    );
}

const styles = lectureDetailStyles;
