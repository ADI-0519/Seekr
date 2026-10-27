import React from 'react';
import { Animated, Image, Pressable, View, Platform } from 'react-native';
import { useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { Play, Send } from 'lucide-react-native';
import { Typography } from '../ui/Typography';
import { PrimaryButton } from '../ui/PrimaryButton';
import { landingStyles as styles } from './styles';
import { useThemeColors } from '../../theme/ThemeProvider';

type PreviewTab = 'transcript' | 'ask' | 'slides';

function TabButton({
    text,
    active,
    onPress,
}: {
    text: string;
    active: boolean;
    onPress: () => void;
}) {
    const colors = useThemeColors();
    return (
        <Pressable
            onPress={onPress}
            style={[
                styles.panelTab,
                {
                    borderBottomColor: active ? colors.primaryEmerald : 'transparent',
                    backgroundColor: active ? 'transparent' : 'transparent',
                },
                Platform.OS === 'web' && { cursor: 'pointer' } as any,
            ]}
        >
            <Typography
                variant="meta"
                color={active ? colors.primaryEmerald : colors.textSecondary}
                style={{ fontWeight: active ? '600' : '400' }}
            >
                {text}
            </Typography>
        </Pressable>
    );
}

function ResultItem({ time, text }: { time: string; text: string }) {
    const colors = useThemeColors();
    return (
        <View style={[styles.resultItem, { borderColor: colors.borderSubtle }]}>
            <Typography variant="meta" color={colors.primaryEmerald} style={styles.resultTime}>
                {time}
            </Typography>
            <Typography variant="bodySm" color={colors.textSecondary}>
                {text}
            </Typography>
        </View>
    );
}

export function HeroSection({
    isMobile,
    glassStrong,
    getHeroPartStyle,
}: {
    isMobile: boolean;
    glassStrong: any;
    getHeroPartStyle?: (index: number) => any;
}) {
    const router = useRouter();
    const colors = useThemeColors();
    const { width } = useWindowDimensions();
    const isNarrowDesktop = !isMobile && width < 1240;
    const [activeTab, setActiveTab] = React.useState<PreviewTab>('transcript');

    return (
        <View style={[styles.hero, isMobile && styles.heroMobile, isNarrowDesktop && styles.heroNarrowDesktop]}>
            <View style={[styles.heroTextCol, isNarrowDesktop && styles.heroTextColNarrowDesktop]}>
                <Animated.View style={getHeroPartStyle?.(0)}>
                    <Typography
                        variant={isMobile || isNarrowDesktop ? 'displayMd' : 'displayLg'}
                        color={colors.textPrimary}
                        style={[styles.heroTitle, isMobile && styles.heroTitleMobile]}
                    >
                        Learn faster from lectures
                    </Typography>
                </Animated.View>
                <Animated.View style={getHeroPartStyle?.(1)}>
                    <Typography
                        variant={isMobile || isNarrowDesktop ? 'headingLg' : 'headingXl'}
                        color={colors.primaryEmerald}
                        style={[styles.heroAccent, isMobile && styles.heroAccentMobile]}
                    >
                        Search, ask, and navigate lecture content instantly
                    </Typography>
                </Animated.View>
                <Animated.View style={getHeroPartStyle?.(2)}>
                    <Typography variant="bodyLg" color={colors.textSecondary} style={styles.heroBody}>
                        Seekr turns long, dense recordings into searchable, structured, and interactive study
                        workflows with timestamped retrieval and grounded answers.
                    </Typography>
                </Animated.View>
                <Animated.View style={getHeroPartStyle?.(3)}>
                    <View style={[styles.heroActions, isMobile && styles.heroActionsMobile]}>
                        <PrimaryButton
                            label="Start using Seekr"
                            size="lg"
                            onPress={() => router.push('/(auth)/register')}
                            style={[styles.heroButton, isMobile && styles.heroButtonMobile]}
                        />
                        <PrimaryButton
                            label="Log in"
                            size="lg"
                            variant="secondary"
                            onPress={() => router.push('/(auth)/login')}
                            style={[styles.heroButton, isMobile && styles.heroButtonMobile]}
                        />
                    </View>
                </Animated.View>
            </View>

            {/* App preview matching real layout */}
            <Animated.View style={[styles.heroPreview, isMobile && styles.heroPreviewMobile, isNarrowDesktop && styles.heroPreviewNarrowDesktop, glassStrong, { borderColor: colors.borderSubtle }, getHeroPartStyle?.(4)]}>
                {/* Lecture title bar */}
                <View style={[styles.previewTitleBar, { borderColor: colors.borderSubtle }]}>
                    <Typography variant="meta" color={colors.textSecondary}>
                        Deep Learning – Week 4
                    </Typography>
                    <View style={[styles.previewStatusChip, { backgroundColor: colors.chipBgReady }]}>
                        <Typography variant="meta" color={colors.primaryEmerald} style={{ fontSize: 10, fontWeight: '600' }}>
                            READY
                        </Typography>
                    </View>
                </View>

                {/* Main area: video left + panel right */}
                <View style={[styles.previewMain, isMobile && styles.previewMainMobile]}>
                    {/* Video player area */}
                    <View style={[styles.previewVideoArea, isMobile && styles.previewVideoAreaMobile]}>
                        <Image
                            source={require('../../../assets/Slide1.jpg')}
                            style={styles.previewVideoBackground}
                            resizeMode="cover"
                        />
                        <View style={styles.previewVideoSurface}>
                            <View style={styles.previewPlayButton}>
                                <Play size={20} color="#FFFFFF" style={{ marginLeft: 2 }} />
                            </View>
                            {/* Progress bar */}
                            <View style={styles.previewProgressBar}>
                                <View style={[styles.previewProgressFill, { backgroundColor: colors.primaryEmerald, width: '35%' }]} />
                            </View>
                            <View style={styles.previewTimeLabel}>
                                <Typography variant="meta" color="#FFFFFF" style={{ fontSize: 10, opacity: 0.8 }}>
                                    12:34 / 52:18
                                </Typography>
                            </View>
                        </View>
                    </View>

                    {/* Panel area with tabs */}
                    <View style={[styles.previewPanel, isMobile && styles.previewPanelMobile, { borderColor: colors.borderSubtle }]}>
                        {/* Tab header */}
                        <View style={[styles.previewTabBar, { borderColor: colors.borderSubtle }]}>
                            <TabButton text="Transcript" active={activeTab === 'transcript'} onPress={() => setActiveTab('transcript')} />
                            <TabButton text="Ask" active={activeTab === 'ask'} onPress={() => setActiveTab('ask')} />
                            <TabButton text="Slides" active={activeTab === 'slides'} onPress={() => setActiveTab('slides')} />
                        </View>

                        {/* Tab content */}
                        <View style={styles.previewTabContent}>
                            {activeTab === 'transcript' && (
                                <View style={styles.previewTranscript}>
                                    {/* Active line */}
                                    <View style={styles.previewTranscriptRow}>
                                        <Typography variant="meta" color={colors.primaryEmerald} style={styles.previewTranscriptTime}>
                                            12:34
                                        </Typography>
                                        <Typography variant="bodySm" color={colors.textPrimary} style={{ flex: 1 }}>
                                            The vanishing gradient problem gets worse as we add more layers to the network.
                                        </Typography>
                                    </View>
                                    {/* Other lines */}
                                    <View style={[styles.previewTranscriptRow, { opacity: 0.5 }]}>
                                        <Typography variant="meta" color={colors.textSecondary} style={styles.previewTranscriptTime}>
                                            12:41
                                        </Typography>
                                        <Typography variant="bodySm" color={colors.textSecondary} style={{ flex: 1 }}>
                                            Each layer multiplies small gradients together, shrinking the signal.
                                        </Typography>
                                    </View>
                                    <View style={[styles.previewTranscriptRow, { opacity: 0.35 }]}>
                                        <Typography variant="meta" color={colors.textSecondary} style={styles.previewTranscriptTime}>
                                            12:49
                                        </Typography>
                                        <Typography variant="bodySm" color={colors.textSecondary} style={{ flex: 1 }}>
                                            Skip connections solve this by letting gradients flow directly.
                                        </Typography>
                                    </View>
                                    <View style={[styles.previewTranscriptRow, { opacity: 0.2 }]}>
                                        <Typography variant="meta" color={colors.textSecondary} style={styles.previewTranscriptTime}>
                                            12:56
                                        </Typography>
                                        <Typography variant="bodySm" color={colors.textSecondary} style={{ flex: 1 }}>
                                            ResNets introduced this idea and enabled much deeper architectures.
                                        </Typography>
                                    </View>
                                </View>
                            )}

                            {activeTab === 'ask' && (
                                <View style={styles.previewAsk}>
                                    <View style={[styles.askBubbleUser, { backgroundColor: colors.primaryEmerald }]}>
                                        <Typography variant="bodySm" color={colors.surfaceBase} style={styles.askBubbleText}>
                                            Why do deeper nets struggle to train?
                                        </Typography>
                                    </View>
                                    {/* Bot header */}
                                    <View style={styles.previewBotHeader}>
                                        <View style={[styles.previewBotAvatar, { backgroundColor: colors.chipBgReady }]}>
                                            <Image
                                                source={require('../../../assets/seekr-logo.png')}
                                                style={{ width: 12, height: 12 }}
                                                resizeMode="contain"
                                            />
                                        </View>
                                        <Typography variant="meta" color={colors.textSecondary} style={{ fontSize: 10, fontWeight: '600', letterSpacing: 0.6 }}>
                                            SEEKR AI
                                        </Typography>
                                    </View>
                                    <View style={[styles.askBubbleBot, { borderColor: colors.borderSubtle }]}>
                                        <Typography variant="bodySm" color={colors.textPrimary} style={styles.askBubbleText}>
                                            Gradients diminish across many layers, making it harder for earlier
                                            layers to learn{' '}
                                            <Typography variant="meta" color={colors.primaryEmerald} style={{ fontWeight: '700' }}>[1]</Typography>
                                            . Mitigation strategies such as skip connections are compared shortly
                                            after{' '}
                                            <Typography variant="meta" color={colors.primaryEmerald} style={{ fontWeight: '700' }}>[2]</Typography>
                                            .
                                        </Typography>
                                    </View>
                                    {/* Input */}
                                    <View style={[styles.previewAskInput, { borderColor: colors.borderSubtle }]}>
                                        <Typography variant="bodySm" color={colors.textSecondary} style={{ flex: 1, opacity: 0.6 }}>
                                            Ask a question or search...
                                        </Typography>
                                        <View style={[styles.previewSendBtn, { backgroundColor: colors.borderSubtle }]}>
                                            <Send size={10} color="#FFFFFF" />
                                        </View>
                                    </View>
                                </View>
                            )}

                            {activeTab === 'slides' && (
                                <View style={styles.previewSlides}>
                                    <View style={[styles.slideImageCard, { borderColor: colors.borderSubtle }]}>
                                        <View style={styles.previewSlideHeader}>
                                            <Typography variant="meta" color={colors.textSecondary} style={{ fontWeight: '500' }}>
                                                Slide 1
                                            </Typography>
                                            <View style={[styles.previewTimePill, { backgroundColor: colors.chipBgReady }]}>
                                                <Typography variant="meta" color={colors.primaryEmerald} style={{ fontSize: 10 }}>
                                                    12:34
                                                </Typography>
                                            </View>
                                        </View>
                                        <Image
                                            source={require('../../../assets/Slide1.jpg')}
                                            style={styles.slideImage}
                                            resizeMode="cover"
                                        />
                                    </View>
                                    <View style={[styles.slideImageCard, { borderColor: colors.borderSubtle }]}>
                                        <View style={styles.previewSlideHeader}>
                                            <Typography variant="meta" color={colors.textSecondary} style={{ fontWeight: '500' }}>
                                                Slide 2
                                            </Typography>
                                            <View style={[styles.previewTimePill, { backgroundColor: colors.chipBgReady }]}>
                                                <Typography variant="meta" color={colors.primaryEmerald} style={{ fontSize: 10 }}>
                                                    24:10
                                                </Typography>
                                            </View>
                                        </View>
                                        <Image
                                            source={require('../../../assets/Slide2.jpg')}
                                            style={styles.slideImage}
                                            resizeMode="cover"
                                        />
                                    </View>
                                </View>
                            )}
                        </View>
                    </View>
                </View>
            </Animated.View>
        </View>
    );
}
