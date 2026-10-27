import { Platform, StyleSheet } from 'react-native';
import { theme } from '@/design';

export const lectureDetailStyles = StyleSheet.create({
    scroll: {
        paddingBottom: 100, // Mini player clearance
    },
    innerContent: {
        paddingTop: 34,
        paddingHorizontal: 16,
        overflow: 'visible',
    },
    header: {
        marginBottom: theme.spacing[40],
    },
    title: {
        marginBottom: theme.spacing[16],
    },
    metaRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    mainLayoutDesktop: {
        flexDirection: 'row',
        gap: theme.spacing[32],
    },
    mainLayoutMobile: {
        flexDirection: 'column',
        gap: theme.spacing[24],
    },
    videoColumn: {
        flex: 6.5,
    },
    panelColumn: {
        flex: 3.5,
        height: 800, // Explicit height for desktop panel
    },
    fullWidthColumn: {
        flex: 1,
    },
    mobilePanelContainer: {
        height: 500, // Explicit height for mobile panel stacking
        marginBottom: theme.spacing[24],
    },
    centered: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    videoContainer: {
        width: '100%',
        aspectRatio: 16 / 9,
        backgroundColor: '#0A1214',
        overflow: 'hidden',
        marginBottom: theme.spacing[24],
    },
    fullscreenContainer: {
        width: '100%',
        height: '100%',
        aspectRatio: 'auto',
        borderRadius: 0,
        borderWidth: 0,
    },
    videoSurfaceLayout: {
        flex: 1,
        minHeight: 0,
    },
    videoSurfaceLayoutDocked: {
        flexDirection: 'row',
        alignItems: 'stretch',
    },
    videoStage: {
        flex: 1,
        minHeight: 0,
        position: 'relative',
    },
    videoStageDocked: {
        minWidth: 0,
    },
    fullVideo: {
        ...StyleSheet.absoluteFillObject,
    },
    videoPlaceholder: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    controlsBar: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        paddingHorizontal: theme.spacing[20],
        paddingVertical: theme.spacing[16],
        backgroundColor: 'rgba(10, 18, 20, 0.7)',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    controlsBarMobile: {
        flexDirection: 'column',
        alignItems: 'stretch',
        paddingHorizontal: theme.spacing[16],
        paddingVertical: theme.spacing[12],
    },
    controlsCenterMobile: {
        width: '100%',
        marginBottom: 8,
    },
    controlsBottomRowMobile: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    controlsLeftMobile: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    controlsRightMobile: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    controlsLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        minWidth: 160,
    },
    controlsCenter: {
        flex: 1, // Scrubber takes remaining space
        marginHorizontal: theme.spacing[24],
    },
    controlsRight: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'flex-end',
        minWidth: 120,
    },
    controlButton: {
        padding: 8,
        marginRight: 8,
    },
    timeText: {
        marginLeft: 8,
        fontVariant: ['tabular-nums'],
    },
    progressBarPressable: {
        width: '100%',
        paddingVertical: 12,
        justifyContent: 'center',
    },
    progressBarBg: {
        height: 4,
        backgroundColor: 'rgba(255, 255, 255, 0.3)',
        borderRadius: 2,
        position: 'relative',
    },
    progressBarFill: {
        height: '100%',
        backgroundColor: theme.colors.primaryEmerald,
        borderRadius: 2,
    },
    topicOverlayContainer: {
        position: 'absolute',
        top: 0, left: 0, right: 0, bottom: 0,
    },
    topicMarkerWrapper: {
        position: 'absolute',
        height: '100%',
        justifyContent: 'center',
        paddingHorizontal: 0.5,
    },
    topicMarker: {
        width: '100%',
        borderRadius: 2,
    },
    topicTooltipContainer: {
        position: 'absolute',
        bottom: 12,
        left: '50%',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 4,
        borderWidth: 1,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.15,
        shadowRadius: 4,
        zIndex: 10,
        ...(Platform.OS === 'web'
            ? ({
                transition: 'opacity 220ms cubic-bezier(0.22, 1, 0.36, 1), transform 220ms cubic-bezier(0.22, 1, 0.36, 1)',
            } as any)
            : {}),
    },
    topicTooltipVisible: {
        opacity: 1,
    },
    topicTooltipHidden: {
        opacity: 0,
    },
    progressHandle: {
        position: 'absolute',
        top: -6,
        width: 16,
        height: 16,
        borderRadius: 8,
        backgroundColor: theme.colors.surfaceBase,
        borderWidth: 2,
        marginLeft: -8,
    },
    speedButton: {
        marginRight: 16,
        paddingVertical: 4,
        paddingHorizontal: 8,
        borderRadius: 4,
        backgroundColor: 'rgba(255,255,255,0.15)',
    },
    speedButtonText: {
        fontWeight: '600',
    },
    volumeContainer: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    volumeSliderHitArea: {
        height: 36, // generous hit area
        justifyContent: 'center',
        marginRight: 8,
        paddingHorizontal: 8,
    },
    volumeBarBg: {
        height: 4,
        width: '100%',
        backgroundColor: 'rgba(255, 255, 255, 0.3)',
        borderRadius: 2,
        position: 'relative',
    },
    volumeBarFill: {
        height: '100%',
        borderRadius: 2,
    },
    volumeHandle: {
        position: 'absolute',
        top: -6,
        width: 16,
        height: 16,
        borderRadius: 8,
        backgroundColor: theme.colors.surfaceBase,
        borderWidth: 2,
        marginLeft: -8,
    },
    speedMenu: {
        position: 'absolute',
        bottom: 60,
        right: 48,
        backgroundColor: theme.colors.surfaceElevated,
        borderRadius: theme.radii.controlSm,
        padding: 8,
        minWidth: 80,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
        elevation: 10,
        shadowColor: 'black',
        shadowOpacity: 0.1,
        shadowRadius: 10,
    },
    fullscreenPanelReopenButton: {
        position: 'absolute',
        top: theme.spacing[16],
        right: theme.spacing[16],
        zIndex: 7,
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: theme.radii.pill,
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[8],
        gap: theme.spacing[8],
    },
    fullscreenPanelReopenLabel: {
        fontWeight: '600',
    },
    speedMenuItem: {
        paddingVertical: 8,
        paddingHorizontal: 16,
        borderRadius: 4,
    },
    speedMenuItemActive: {
        backgroundColor: theme.colors.chipBgReady,
    },
    summaryShell: {
        marginBottom: theme.spacing[24],
    },
    segmentsShell: {
        marginBottom: theme.spacing[24],
    },
    segmentsSidebar: {
        flexDirection: 'column',
    },
    segmentItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: theme.spacing[8], // Tighter stacked rhythm
        padding: theme.spacing[16],
        borderRadius: theme.radii.controlSm,
        backgroundColor: theme.colors.surfaceElevated,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
    },
    segmentItemActive: {
        backgroundColor: theme.colors.chipBgReady,
        borderColor: 'rgba(16, 185, 129, 0.2)',
    },
    segmentDotContainer: {
        alignItems: 'center',
        marginRight: theme.spacing[16],
        width: 16,
    },
    segmentDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: theme.colors.borderSubtle,
        zIndex: 1,
    },
    segmentDotActive: {
        backgroundColor: theme.colors.primaryEmerald,
    },
    segmentLine: {
        position: 'absolute',
        top: 10,
        bottom: -32,
        width: 2,
        backgroundColor: theme.colors.borderSubtle,
    },
    segmentInfo: {
        flex: 1,
    },
    segmentTimestamp: {
        marginTop: 4,
    },
    segmentSummaryWrapper: {
        overflow: 'hidden',
    },
    segmentSummaryWrapperVisible: {
        opacity: 1,
        maxHeight: 120,
        marginTop: 8,
    },
    segmentSummaryWrapperHidden: {
        opacity: 0,
        maxHeight: 0,
        marginTop: 0,
    },
    segmentSummary: {
        lineHeight: 20,
    },
    panelShell: {
        flex: 1,
        overflow: 'hidden', // Fine here as Panel doesn't cast inner shadows to be clipped
    },
    panelShellTranscript: {
        backgroundColor: theme.colors.surfaceBase,
    },
    tabsHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.borderSubtle,
        backgroundColor: theme.colors.surfaceElevated,
    },
    tabsHeaderFullscreen: {
        paddingRight: theme.spacing[12],
    },
    tabsHeaderTabs: {
        flex: 1,
        flexDirection: 'row',
        minWidth: 0,
    },
    tabsHeaderCloseButton: {
        width: 36,
        height: 36,
        borderRadius: 18,
        borderWidth: 1,
        alignItems: 'center',
        justifyContent: 'center',
        marginLeft: theme.spacing[12],
    },
    tab: {
        flex: 1,
        paddingVertical: theme.spacing[20],
        borderBottomWidth: 2,
        borderBottomColor: 'transparent',
    },
    tabContent: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
    },
    tabActive: {
        borderBottomColor: theme.colors.primaryEmerald,
        backgroundColor: theme.colors.surfaceBase,
    },
    tabText: {
        marginLeft: theme.spacing[8],
        fontWeight: '600',
    },
    panelContentViewport: {
        flex: 1,
        minHeight: 0,
        position: 'relative',
        overflow: 'hidden',
    },
    panelContentLayer: {
        ...StyleSheet.absoluteFillObject,
        minHeight: 0,
    },
    panelContentLayerActive: {
        zIndex: 2,
    },
    panelContentLayerInactive: {
        zIndex: 1,
    },
    panelContentLayerHidden: {
        display: 'none',
    },
    panelScrollContent: {
        flex: 1,
    },
    panelScrollContentTranscript: {
        paddingHorizontal: 0,
        paddingVertical: 0,
    },
    fullscreenPanelDock: {
        width: 420,
        borderLeftWidth: 1,
        minHeight: 0,
        flexShrink: 0,
        borderTopLeftRadius: theme.radii.card,
        borderBottomLeftRadius: theme.radii.card,
        overflow: 'hidden',
    },
    fullscreenPanelDockInner: {
        flex: 1,
        minHeight: 0,
        width: '100%',
    },
    fullscreenPanelContent: {
        flex: 1,
        minHeight: 0,
        width: '100%',
    },
    transcriptPanelWrapper: {
        flex: 1,
        position: 'relative',
    },
    transcriptFadeMask: {
        position: 'absolute',
        left: 0,
        right: 0,
        height: 40,
        zIndex: 5,
    },
    transcriptFadeTop: {
        top: 0,
    },
    transcriptFadeBottom: {
        bottom: 0,
    },
    transcriptList: {
        flex: 1,
    },
    transcriptLineFocusable: {
        paddingHorizontal: theme.spacing[4],
        paddingVertical: theme.spacing[8],
        marginVertical: theme.spacing[4],
        borderRadius: 12,
    },
    transcriptLineContent: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        width: '100%',
        minWidth: 0,
    },
    timestampFocal: {
        width: 60,
        paddingTop: 6,
        textAlign: 'right',
        marginRight: 16,
        fontVariant: ['tabular-nums'],
        flexShrink: 0,
    },
    transcriptTextFocal: {
        flex: 1,
        minWidth: 0,
        flexShrink: 1,
        lineHeight: 32,
        fontSize: 18,
        ...(Platform.OS === 'web'
            ? ({ wordBreak: 'break-word', overflowWrap: 'anywhere' } as any)
            : {}),
    },
    transcriptTextFocalCompact: {
        fontSize: 16,
        lineHeight: 28,
    },
    transcriptScrubInfo: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 8,
    },
    transcriptContent: {
        paddingHorizontal: 0,
        paddingVertical: 0,
    },
    transcriptLine: {
        flexDirection: 'row',
        alignItems: "flex-start",
        marginBottom: theme.spacing[16],
        padding: theme.spacing[12],
        borderRadius: theme.radii.controlSm,
    },
    transcriptLineActive: {
        flexDirection: 'row',
        alignItems: "flex-start",
        marginBottom: theme.spacing[20],
        backgroundColor: theme.colors.chipBgReady,
        padding: theme.spacing[16],
        borderRadius: theme.radii.controlSm,
    },
    timestamp: {
        width: 60,
        paddingTop: 5,
    },

    transcriptText: {
        flex: 1,
        lineHeight: 28,
    },
    slidesPane: {
        flex: 1,
        borderRadius: theme.radii.card,
        padding: theme.spacing[24],
        borderWidth: 1,
    },
    slidesHeader: {
        marginBottom: theme.spacing[16],
    },
    slidesTitle: {
        letterSpacing: 0.2,
    },
    slidesSubtitle: {
        marginTop: theme.spacing[4],
    },
    slideActionRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[12],
    },
    slidesDownloadButton: {
        minWidth: 120,
    },
    placeholderCenter: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 60,
    },
    notesShell: {
        marginBottom: theme.spacing[24],
    },
    askPanelContainer: {
        flex: 1,
        justifyContent: 'space-between',
    },
    askMessagesScroll: {
        flex: 1,
    },
    askMessagesContent: {
        padding: theme.spacing[16],
        paddingBottom: theme.spacing[8],
        gap: 24,
    },
    askEmptyState: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 80,
    },
    botHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 6,
        paddingLeft: 2,
    },
    botAvatarBadge: {
        width: 28,
        height: 28,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 8,
    },
    botHeaderLabel: {
        fontSize: 11,
        fontWeight: '700',
        letterSpacing: 1,
    },
    chatBubble: {
        maxWidth: '80%',
        padding: theme.spacing[20],
        borderRadius: 16,
    },
    chatBubbleUser: {
        alignSelf: 'flex-end',
        borderBottomRightRadius: 4,
    },
    chatBubbleAi: {
        alignSelf: 'flex-start',
        borderBottomLeftRadius: 4,
        borderWidth: 1,
        maxWidth: '80%',
    },
    citationChip: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: 14,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
    },
    citationTimeBadge: {
        paddingHorizontal: 10,
        paddingVertical: 5,
        borderRadius: 6,
    },
    askInputBar: {
        padding: theme.spacing[16],
        borderTopWidth: 1,
    },
    askInputWrapper: {
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: 24,
        borderWidth: 1,
        paddingLeft: 16,
        paddingRight: 6,
        paddingVertical: 4,
    },
    askInput: {
        flex: 1,
        height: 40,
        fontSize: 16,
    },
    askSendButton: {
        width: 32,
        height: 32,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
    },
    askDisclaimer: {
        textAlign: 'center',
        marginTop: 8,
        fontSize: 10,
        opacity: 0.7,
    },
    slidesViewerContainer: {
        flex: 1,
        backgroundColor: 'transparent',
    },
    slidesToolbar: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: theme.spacing[16],
        paddingVertical: theme.spacing[12],
        borderBottomWidth: 1,
    },
    zoomControls: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    iconButton: {
        width: 32,
        height: 32,
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: theme.radii.button,
        backgroundColor: 'rgba(128, 128, 128, 0.1)',
    },
    slidesScrollArea: {
        flex: 1,
    },
    slidesScrollContent: {
        padding: theme.spacing[24],
        paddingBottom: theme.spacing[40],
    },
    slideCard: {
        marginBottom: theme.spacing[32],
        borderRadius: theme.radii.card,
        padding: theme.spacing[16],
        borderWidth: 1,
        width: '100%',
        maxWidth: 600,
        alignSelf: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 12,
        elevation: 2,
    },
    slideCardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[12],
    },
    timestampPill: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 16,
    },
    slideImage: {
        width: '100%',
        aspectRatio: 16 / 9,
        borderRadius: theme.radii.controlSm,
        backgroundColor: '#000000',
    },
    slidePlaceholder: {
        width: '100%',
        aspectRatio: 16 / 9,
        borderRadius: theme.radii.controlSm,
        alignItems: 'center',
        justifyContent: 'center',
    },
    segmentReadMore: {
        marginTop: 8,
        fontWeight: '600',
    },
});

export type LectureDetailStyles = typeof lectureDetailStyles;
