import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { Typography } from './Typography';
import { theme } from '../../design/index';
import { PlayCircle, Loader2, AlertCircle, CheckCircle, Tag } from 'lucide-react-native';

export type StatusVariant =
    | 'ready'
    | 'processing'
    | 'failed'
    | 'transcribed'
    | 'slides'
    | 'tag';

interface StatusChipProps {
    variant: StatusVariant;
    label?: string;
    style?: StyleProp<ViewStyle>;
}

export const StatusChip: React.FC<StatusChipProps> = ({
    variant,
    label,
    style,
}) => {

    const getVariantStyles = () => {
        switch (variant) {
            case 'ready':
                return {
                    bgColor: theme.colors.chipBgReady,
                    textColor: theme.colors.success,
                    icon: PlayCircle,
                    defaultLabel: 'Ready'
                };
            case 'processing':
                return {
                    bgColor: theme.colors.chipBgProcessing,
                    textColor: theme.colors.info,
                    icon: Loader2,
                    defaultLabel: 'Processing'
                };
            case 'failed':
                return {
                    bgColor: theme.colors.chipBgFailed,
                    textColor: theme.colors.error,
                    icon: AlertCircle,
                    defaultLabel: 'Failed'
                };
            case 'transcribed':
                return {
                    bgColor: theme.colors.chipBgReady,
                    textColor: theme.colors.success,
                    icon: CheckCircle,
                    defaultLabel: 'Transcribed'
                };
            case 'slides':
                return {
                    bgColor: theme.colors.chipBgReady,
                    textColor: theme.colors.success,
                    icon: CheckCircle,
                    defaultLabel: 'Slides'
                };
            case 'tag':
                return {
                    bgColor: theme.colors.surfaceElevated,
                    textColor: theme.colors.textSecondary,
                    icon: null,
                    defaultLabel: ''
                };
            default:
                return {
                    bgColor: theme.colors.surfaceElevated,
                    textColor: theme.colors.textSecondary,
                    icon: null,
                    defaultLabel: ''
                };
        }
    };

    const config = getVariantStyles();
    const displayLabel = label || config.defaultLabel;

    const formattedLabel = variant === 'tag' ? displayLabel : displayLabel.toUpperCase();

    const Icon = variant === 'tag' ? null : config.icon;

    return (
        <View style={StyleSheet.flatten([styles.container, { backgroundColor: config.bgColor }, style])}>
            {Icon && (
                <Icon
                    color={config.textColor}
                    size={12}
                    style={styles.icon}
                />
            )}
            {variant === 'tag' && !Icon && (
                <Tag color={config.textColor} size={10} style={styles.icon} />
            )}
            <Typography
                variant="chip"
                color={config.textColor}
                style={styles.label}
            >
                {formattedLabel}
            </Typography>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: theme.spacing[8],
        paddingVertical: theme.spacing[4],
        borderRadius: theme.radii.pill,
        alignSelf: 'flex-start',
    },
    icon: {
        marginRight: 4,
    },
    label: {
        letterSpacing: 0.5,
    }
});
