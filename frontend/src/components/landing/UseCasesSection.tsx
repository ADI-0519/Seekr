import React from 'react';
import { View } from 'react-native';
import { Typography } from '../ui/Typography';
import { useThemeColors } from '../../theme/ThemeProvider';
import { landingStyles as styles } from './styles';
import { LandingUseCase } from './types';

function UseCaseRow({
    index,
    icon,
    title,
    body,
    showDivider,
}: {
    index: number;
    icon: React.ReactNode;
    title: string;
    body: string;
    showDivider?: boolean;
}) {
    const colors = useThemeColors();
    return (
        <View>
            <View style={styles.useCaseRow}>
                <View style={styles.useCaseMeta}>
                    <Typography variant="meta" color={colors.primaryEmerald} style={styles.useCaseIndex}>
                        {String(index).padStart(2, '0')}
                    </Typography>
                    <View style={[styles.useCaseIcon, { backgroundColor: colors.chipBgReady }]}>
                        {icon}
                    </View>
                </View>
                <View style={styles.useCaseBody}>
                    <Typography variant="headingLg" color={colors.textPrimary} style={styles.useCaseTitle}>
                        {title}
                    </Typography>
                    <Typography variant="bodyLg" color={colors.textSecondary} style={styles.useCaseText}>
                        {body}
                    </Typography>
                </View>
            </View>
            {showDivider && <View style={[styles.useCaseDivider, { backgroundColor: colors.borderSubtle }]} />}
        </View>
    );
}

export function UseCasesSection({
    isMobile,
    audienceItems,
}: {
    isMobile: boolean;
    audienceItems: LandingUseCase[];
}) {
    const colors = useThemeColors();

    return (
        <View style={styles.audienceSection}>
            <Typography variant="meta" color={colors.primaryEmerald} style={styles.boxEyebrow}>
                USE CASES
            </Typography>
            <Typography variant="displayMd" color={colors.textPrimary} style={styles.boxHeadline}>
                Built for anyone who learns from lectures
            </Typography>
            <View style={[styles.audienceShowcase, isMobile && styles.audienceShowcaseMobile]}>
                <View style={styles.audienceLead}>
                    <Typography variant="headingXl" color={colors.textPrimary} style={styles.audienceLeadTitle}>
                        Different learners.
                        {'\n'}One intelligent workflow.
                    </Typography>
                    <Typography variant="bodyLg" color={colors.textSecondary} style={styles.audienceLeadBody}>
                        Seekr supports how people actually consume lecture content, from fast revision to deep exploratory research.
                    </Typography>
                </View>
                <View style={styles.audienceUseCaseStackWrap}>
                    <View style={[styles.audienceTrackGlow, { backgroundColor: colors.chipBgReady }]} />
                    <View style={[styles.audienceTrackLine, { backgroundColor: colors.borderSubtle }]} />
                    <View style={[styles.audienceUseCaseStack, { borderColor: colors.borderSubtle }]}>
                        {audienceItems.map((item, index) => (
                            <UseCaseRow
                                key={item.title}
                                index={index + 1}
                                title={item.title}
                                body={item.body}
                                icon={item.icon}
                                showDivider={index < audienceItems.length - 1}
                            />
                        ))}
                    </View>
                </View>
            </View>
        </View>
    );
}
