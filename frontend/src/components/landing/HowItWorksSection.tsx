import React from 'react';
import { Animated, View } from 'react-native';
import { Cpu, SearchCheck, Upload } from 'lucide-react-native';
import { Typography } from '../ui/Typography';
import { useThemeColors } from '../../theme/ThemeProvider';
import { landingStyles as styles } from './styles';

function WorkflowStep({
    number,
    icon,
    title,
    body,
}: {
    number: string;
    icon: React.ReactNode;
    title: string;
    body: string;
}) {
    const colors = useThemeColors();
    return (
        <View style={styles.workflowCard}>
            <Typography variant="displayMd" color={colors.borderSubtle} style={styles.workflowNumber}>
                {number}
            </Typography>
            <View style={[styles.boxIconBadge, { backgroundColor: colors.chipBgReady }]}>{icon}</View>
            <Typography variant="headingXl" color={colors.textPrimary} style={styles.workflowTitle}>
                {title}
            </Typography>
            <Typography variant="bodyLg" color={colors.textSecondary} style={styles.workflowBody}>
                {body}
            </Typography>
        </View>
    );
}

export function HowItWorksSection({
    isMobile,
    onLayout,
    getWorkflowCardAnimatedStyle,
}: {
    isMobile: boolean;
    onLayout?: (event: any) => void;
    getWorkflowCardAnimatedStyle: (index: number) => any;
}) {
    const colors = useThemeColors();

    return (
        <View style={styles.landingSection} onLayout={onLayout}>
            <Typography variant="meta" color={colors.primaryEmerald} style={styles.boxEyebrow}>
                HOW IT WORKS
            </Typography>
            <Typography variant="displayMd" color={colors.textPrimary} style={styles.boxHeadline}>
                Three steps to searchable lectures
            </Typography>
            <View style={[styles.workflowDivider, { backgroundColor: colors.borderSubtle }]} />

            <View style={[styles.workflowGrid, isMobile && styles.workflowGridMobile]}>
                <Animated.View style={[styles.workflowStepAnimated, getWorkflowCardAnimatedStyle(0)]}>
                    <WorkflowStep
                        number="01"
                        icon={<Upload size={22} color={colors.primaryEmerald} />}
                        title="Upload your lecture"
                        body="Upload a video file or paste a link. Supports MP4, MOV, MKV, and WebM."
                    />
                </Animated.View>
                <Animated.View style={[styles.workflowStepAnimated, getWorkflowCardAnimatedStyle(1)]}>
                    <WorkflowStep
                        number="02"
                        icon={<Cpu size={22} color={colors.primaryEmerald} />}
                        title="We process everything"
                        body="Transcript extraction, slide OCR, temporal indexing, and semantic embedding - all automatic."
                    />
                </Animated.View>
                <Animated.View style={[styles.workflowStepAnimated, getWorkflowCardAnimatedStyle(2)]}>
                    <WorkflowStep
                        number="03"
                        icon={<SearchCheck size={22} color={colors.primaryEmerald} />}
                        title="Search and ask"
                        body="Query across all your lectures. Get timestamped results and AI-grounded answers instantly."
                    />
                </Animated.View>
            </View>
        </View>
    );
}
