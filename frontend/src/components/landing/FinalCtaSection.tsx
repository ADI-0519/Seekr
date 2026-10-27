import React from 'react';
import { ArrowRight } from 'lucide-react-native';
import { Pressable, View } from 'react-native';
import { Typography } from '../ui/Typography';
import { useThemeColors } from '../../theme/ThemeProvider';
import { landingStyles as styles } from './styles';

export function FinalCtaSection({
    glassMedium,
    onGetStarted,
}: {
    glassMedium: any;
    onGetStarted: () => void;
}) {
    const colors = useThemeColors();

    return (
        <View style={[styles.finalPowerBox, glassMedium, { borderColor: colors.borderSubtle }]}>
            <Typography variant="displayLg" color={colors.textPrimary} style={styles.powerCtaTitle}>
                Stop rewatching.
            </Typography>
            <Typography variant="displayLg" color={colors.primaryEmerald} style={styles.powerCtaTitleAccent}>
                Start finding.
            </Typography>
            <Typography variant="headingSm" color={colors.textSecondary} style={styles.powerCtaBody}>
                Upload your first lecture and see how fast you can find what you're looking for.
            </Typography>
            <Pressable
                onPress={onGetStarted}
                style={[styles.powerCtaButton, { backgroundColor: colors.primaryEmerald }]}
            >
                <Typography variant="headingSm" color={colors.surfaceBase}>
                    Get started
                </Typography>
                <ArrowRight size={18} color={colors.surfaceBase} />
            </Pressable>
        </View>
    );
}
