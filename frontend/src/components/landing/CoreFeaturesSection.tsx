import React from 'react';
import { Clock3, Eye, MessageSquare, Search } from 'lucide-react-native';
import { View } from 'react-native';
import { Typography } from '../ui/Typography';
import { useThemeColors } from '../../theme/ThemeProvider';
import { landingStyles as styles } from './styles';
import { buildGlassStyle } from './utils';

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

function MiniFeatureCard({
    icon,
    title,
    body,
}: {
    icon: React.ReactNode;
    title: string;
    body: string;
}) {
    const colors = useThemeColors();
    const cardGlass = React.useMemo(() => buildGlassStyle(colors.surfaceBase, 0.46), [colors.surfaceBase]);
    return (
        <View style={[styles.miniFeatureCard, cardGlass, { borderColor: colors.borderSubtle }]}>
            <View style={[styles.boxIconBadge, { backgroundColor: colors.chipBgReady }]}>{icon}</View>
            <Typography variant="headingSm" color={colors.textPrimary} style={styles.miniFeatureTitle}>
                {title}
            </Typography>
            <Typography variant="bodyMd" color={colors.textSecondary} style={styles.miniFeatureBody}>
                {body}
            </Typography>
        </View>
    );
}

export function CoreFeaturesSection({
    isMobile,
    glassMedium,
    glassSoft,
}: {
    isMobile: boolean;
    glassMedium: any;
    glassSoft: any;
}) {
    const colors = useThemeColors();

    return (
        <View style={styles.landingSection}>
            <Typography variant="meta" color={colors.primaryEmerald} style={styles.boxEyebrow}>
                CORE FEATURES
            </Typography>
            <Typography variant="displayMd" color={colors.textPrimary} style={styles.boxHeadline}>
                Built for how you actually study
            </Typography>

            <View style={[styles.boxFeatureHero, glassMedium, isMobile && styles.boxFeatureHeroMobile, { borderColor: colors.borderSubtle }]}>
                <View style={styles.boxFeatureLeft}>
                    <View style={[styles.boxIconBadge, { backgroundColor: colors.chipBgReady }]}>
                        <Search size={22} color={colors.primaryEmerald} />
                    </View>
                    <Typography variant="headingXl" color={colors.textPrimary} style={styles.boxFeatureTitle}>
                        Semantic search across all lectures
                    </Typography>
                    <Typography variant="bodyLg" color={colors.textSecondary} style={styles.boxFeatureBody}>
                        Type a concept, question, or topic - Seekr understands meaning, not just keywords. Results are ranked by relevance and pinpointed to exact moments.
                    </Typography>
                </View>

                <View style={styles.boxFeatureRight}>
                    <View style={[styles.boxQueryPanel, glassSoft, { borderColor: colors.borderSubtle }]}>
                        <View style={styles.boxQueryRow}>
                            <Typography variant="meta" color={colors.textSecondary} style={[styles.boxQueryTag, { backgroundColor: colors.surfaceElevated }]}>
                                query
                            </Typography>
                            <Typography variant="bodyMd" color={colors.textPrimary}>
                                "explain gradient descent intuitively"
                            </Typography>
                        </View>
                        <View style={[styles.boxDivider, { backgroundColor: colors.borderSubtle }]} />
                        <ResultItem time="23:41" text="ML Fundamentals - Lecture 4 · 94% match" />
                        <ResultItem time="1:12:08" text="Optimization Methods - Lecture 7 · 87% match" />
                        <ResultItem time="45:22" text="Deep Learning Intro - Lecture 2 · 82% match" />
                    </View>
                </View>
            </View>

            <View style={[styles.boxFeatureGrid, isMobile && styles.boxFeatureGridMobile]}>
                <MiniFeatureCard
                    icon={<Clock3 size={20} color={colors.primaryEmerald} />}
                    title="Timestamp navigation"
                    body="Jump directly to the exact moment in a lecture. Every result links to a precise timestamp."
                />
                <MiniFeatureCard
                    icon={<Eye size={20} color={colors.primaryEmerald} />}
                    title="Multi-modal understanding"
                    body="Combines transcript text with slide OCR so both spoken content and on-screen text are searchable together."
                />
                <MiniFeatureCard
                    icon={<MessageSquare size={20} color={colors.primaryEmerald} />}
                    title="Grounded answers"
                    body="Ask a question and get AI-generated answers with citations to specific lecture segments."
                />
            </View>
        </View>
    );
}
