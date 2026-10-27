import { StyleSheet } from 'react-native';
import { theme } from '../../design';

export const landingStyles = StyleSheet.create({
    page: {
        flex: 1,
    },
    content: {
        paddingTop: theme.spacing[24],
        paddingBottom: theme.spacing[64],
        paddingHorizontal: theme.spacing[64],
    },
    contentMobile: {
        paddingHorizontal: theme.spacing[16],
        paddingTop: theme.spacing[16],
        paddingBottom: theme.spacing[48],
    },
    hero: {
        flexDirection: 'row',
        gap: theme.spacing[48],
        marginBottom: theme.spacing[64],
        marginTop: theme.spacing[48],
    },
    heroNarrowDesktop: {
        gap: theme.spacing[64],
        alignItems: 'flex-start',
    },
    heroMobile: {
        flexDirection: 'column',
        gap: theme.spacing[20],
        marginTop: theme.spacing[8],
        marginBottom: theme.spacing[64] * 2,
    },
    heroTextCol: {
        flex: 1,
        maxWidth: 740,
    },
    heroTextColNarrowDesktop: {
        flex: 1.15,
        maxWidth: 760,
    },
    heroTitle: {
        marginBottom: theme.spacing[12],
        lineHeight: 52,
    },
    heroTitleMobile: {
        lineHeight: 44,
        marginBottom: theme.spacing[8],
    },
    heroAccent: {
        marginBottom: theme.spacing[20],
    },
    heroAccentMobile: {
        marginBottom: theme.spacing[16],
    },
    heroBody: {
        maxWidth: 720,
        lineHeight: 25,
        marginBottom: theme.spacing[32],
    },
    heroActions: {
        flexDirection: 'row',
        gap: theme.spacing[12],
    },
    heroActionsMobile: {
        flexDirection: 'column',
    },
    heroButton: {
        minWidth: 190,
    },
    heroButtonMobile: {
        width: '100%',
    },
    heroPreview: {
        flex: 1,
        minWidth: 320,
        borderWidth: 1,
        borderRadius: 16,
        overflow: 'hidden',
    },
    heroPreviewNarrowDesktop: {
        flex: 0.92,
    },
    heroPreviewMobile: {
        minWidth: 0,
        width: '100%',
    },
    previewTitleBar: {
        borderBottomWidth: 1,
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[8],
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    previewStatusChip: {
        borderRadius: 6,
        paddingHorizontal: 6,
        paddingVertical: 2,
    },
    previewMain: {
        flexDirection: 'row',
        minHeight: 320,
    },
    previewMainMobile: {
        flexDirection: 'column',
    },
    previewVideoArea: {
        flex: 1.1,
        backgroundColor: '#0A1214',
        position: 'relative',
        overflow: 'hidden',
    },
    previewVideoAreaMobile: {
        height: 160,
    },
    previewVideoBackground: {
        ...StyleSheet.absoluteFillObject,
        width: '100%',
        height: '100%',
    },
    previewVideoSurface: {
        ...StyleSheet.absoluteFillObject,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(10, 18, 20, 0.45)',
    },
    previewPlayButton: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(255,255,255,0.15)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    previewProgressBar: {
        position: 'absolute',
        bottom: 24,
        left: 12,
        right: 12,
        height: 3,
        borderRadius: 2,
        backgroundColor: 'rgba(255,255,255,0.2)',
    },
    previewProgressFill: {
        height: '100%',
        borderRadius: 2,
    },
    previewTimeLabel: {
        position: 'absolute',
        bottom: 8,
        left: 12,
    },
    previewPanel: {
        flex: 1,
        borderLeftWidth: 1,
    },
    previewPanelMobile: {
        borderLeftWidth: 0,
        borderTopWidth: 1,
    },
    previewTabBar: {
        flexDirection: 'row',
        borderBottomWidth: 1,
    },
    panelTab: {
        flex: 1,
        alignItems: 'center',
        paddingVertical: theme.spacing[8],
        borderBottomWidth: 2,
    },
    previewTabContent: {
        flex: 1,
        padding: 10,
    },
    previewTranscript: {
        gap: theme.spacing[4],
    },
    previewTranscriptRow: {
        flexDirection: 'row',
        gap: theme.spacing[8],
        paddingVertical: theme.spacing[4],
    },
    previewTranscriptTime: {
        width: 36,
        fontSize: 10,
    },
    previewAsk: {
        gap: theme.spacing[8],
        flex: 1,
    },
    previewBotHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingLeft: 2,
    },
    previewBotAvatar: {
        width: 18,
        height: 18,
        borderRadius: 9,
        alignItems: 'center',
        justifyContent: 'center',
    },
    previewAskInput: {
        marginTop: 'auto',
        borderWidth: 1,
        borderRadius: 999,
        paddingHorizontal: 10,
        paddingVertical: 6,
        flexDirection: 'row',
        alignItems: 'center',
    },
    previewSendBtn: {
        width: 22,
        height: 22,
        borderRadius: 11,
        alignItems: 'center',
        justifyContent: 'center',
    },
    previewSlides: {
        gap: theme.spacing[8],
    },
    previewSlideHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    previewTimePill: {
        borderRadius: 4,
        paddingHorizontal: 5,
        paddingVertical: 1,
    },
    resultItem: {
        borderWidth: 1,
        borderRadius: 10,
        padding: theme.spacing[8],
        gap: 4,
    },
    resultTime: {
        letterSpacing: 0.4,
    },
    askBubbleUser: {
        alignSelf: 'flex-end',
        maxWidth: '86%',
        borderRadius: 12,
        paddingHorizontal: 10,
        paddingVertical: theme.spacing[8],
    },
    askBubbleBot: {
        alignSelf: 'flex-start',
        maxWidth: '92%',
        borderWidth: 1,
        borderRadius: 12,
        paddingHorizontal: 10,
        paddingVertical: theme.spacing[8],
    },
    askBubbleText: {
        lineHeight: 20,
        fontSize: 12,
    },
    slideGrid: {
        gap: theme.spacing[12],
    },
    slideImageCard: {
        borderWidth: 1,
        borderRadius: 8,
        padding: theme.spacing[8],
        gap: 6,
    },
    slideImage: {
        width: '100%',
        height: 64,
        borderRadius: 6,
    },
    landingSection: {
        marginBottom: theme.spacing[64] * 3,
    },
    audienceSection: {
        marginBottom: theme.spacing[64],
    },
    boxEyebrow: {
        textAlign: 'center',
        letterSpacing: 1.2,
        marginBottom: theme.spacing[12],
    },
    boxHeadline: {
        textAlign: 'center',
        marginBottom: theme.spacing[24],
        lineHeight: 58,
    },
    boxFeatureHero: {
        borderWidth: 1.5,
        borderRadius: 16,
        flexDirection: 'row',
        gap: theme.spacing[32],
        padding: theme.spacing[24],
        marginBottom: theme.spacing[24],
    },
    boxFeatureHeroMobile: {
        flexDirection: 'column',
    },
    boxFeatureLeft: {
        flex: 1,
    },
    boxFeatureRight: {
        flex: 1.1,
        justifyContent: 'center',
    },
    boxIconBadge: {
        width: 58,
        height: 58,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: theme.spacing[16],
    },
    boxFeatureTitle: {
        marginBottom: theme.spacing[12],
    },
    boxFeatureBody: {
        lineHeight: 32,
        maxWidth: 640,
    },
    boxQueryPanel: {
        borderWidth: 1.5,
        borderRadius: 14,
        padding: theme.spacing[12],
        gap: theme.spacing[12],
    },
    boxQueryRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[12],
    },
    boxQueryTag: {
        paddingHorizontal: 8,
        paddingVertical: theme.spacing[4],
        borderRadius: 6,
    },
    boxDivider: {
        height: 1,
    },
    boxFeatureGrid: {
        flexDirection: 'row',
        gap: theme.spacing[20],
        marginTop: theme.spacing[8],
    },
    boxFeatureGridMobile: {
        flexDirection: 'column',
    },
    miniFeatureCard: {
        flex: 1,
        borderWidth: 1.5,
        borderRadius: 16,
        padding: theme.spacing[24],
        minWidth: 220,
    },
    miniFeatureTitle: {
        marginBottom: theme.spacing[12],
    },
    miniFeatureBody: {
        lineHeight: 26,
    },
    workflowDivider: {
        height: 1,
        backgroundColor: 'transparent',
        marginBottom: theme.spacing[24],
        marginHorizontal: theme.spacing[8],
    },
    workflowGrid: {
        flexDirection: 'row',
        gap: theme.spacing[24],
    },
    workflowStepAnimated: {
        flex: 1,
    },
    workflowGridMobile: {
        flexDirection: 'column',
    },
    workflowCard: {
        flex: 1,
        minWidth: 220,
        paddingHorizontal: theme.spacing[8],
        paddingBottom: theme.spacing[12],
    },
    workflowNumber: {
        marginBottom: theme.spacing[8],
        letterSpacing: 0.8,
    },
    workflowTitle: {
        marginBottom: theme.spacing[16],
    },
    workflowBody: {
        lineHeight: 36,
    },
    audienceShowcase: {
        flexDirection: 'row',
        gap: theme.spacing[32],
        marginTop: theme.spacing[12],
    },
    audienceShowcaseMobile: {
        flexDirection: 'column',
        gap: theme.spacing[20],
    },
    audienceLead: {
        flex: 0.9,
        paddingTop: theme.spacing[8],
    },
    audienceLeadTitle: {
        marginBottom: theme.spacing[12],
        lineHeight: 42,
    },
    audienceLeadBody: {
        lineHeight: 28,
        maxWidth: 420,
    },
    audienceUseCaseStackWrap: {
        flex: 1.1,
        position: 'relative',
        minHeight: 0,
    },
    audienceTrackGlow: {
        position: 'absolute',
        top: theme.spacing[20],
        bottom: theme.spacing[20],
        left: 2,
        width: 4,
        borderRadius: 999,
        opacity: 0.35,
    },
    audienceTrackLine: {
        position: 'absolute',
        top: theme.spacing[20],
        bottom: theme.spacing[20],
        left: 3,
        width: 2,
        borderRadius: 999,
        opacity: 0.65,
    },
    audienceUseCaseStack: {
        flex: 1,
        borderLeftWidth: 1,
        paddingLeft: theme.spacing[24],
    },
    useCaseRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: theme.spacing[16],
        paddingVertical: theme.spacing[16],
    },
    useCaseMeta: {
        alignItems: 'center',
        gap: theme.spacing[8],
        width: 56,
    },
    useCaseIndex: {
        letterSpacing: 1.2,
    },
    useCaseIcon: {
        width: 40,
        height: 40,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
    },
    useCaseBody: {
        flex: 1,
        minWidth: 0,
    },
    useCaseTitle: {
        marginBottom: theme.spacing[8],
    },
    useCaseText: {
        lineHeight: 28,
    },
    useCaseDivider: {
        height: 1,
        marginLeft: 72,
    },
    finalPowerBox: {
        borderWidth: 1.5,
        borderRadius: 22,
        paddingVertical: theme.spacing[64],
        paddingHorizontal: theme.spacing[32],
        alignItems: 'center',
        marginTop: theme.spacing[64],
        marginBottom: theme.spacing[64],
    },
    powerCtaTitle: {
        textAlign: 'center',
        letterSpacing: -0.9,
        marginBottom: -6,
    },
    powerCtaTitleAccent: {
        textAlign: 'center',
        letterSpacing: -0.9,
        marginTop: 10,
        marginBottom: theme.spacing[16],
    },
    powerCtaBody: {
        textAlign: 'center',
        maxWidth: 760,
        marginBottom: theme.spacing[32],
    },
    powerCtaButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[12],
        borderRadius: 14,
        paddingHorizontal: theme.spacing[24],
        paddingVertical: theme.spacing[12],
    },
});
