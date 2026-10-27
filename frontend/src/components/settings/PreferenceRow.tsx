import React, { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View, Platform } from 'react-native';
import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';

interface PreferenceRowProps {
    icon: React.ComponentType<{ color?: string; size?: number }>;
    title: string;
    subtitle?: string;
    iconColor?: string;
    titleColor?: string;
    iconBackgroundColor?: string;
    iconSize?: number;
    trailing?: React.ReactNode;
    onPress?: () => void;
}

export function PreferenceRow({
    icon: Icon,
    title,
    subtitle,
    iconColor,
    titleColor,
    iconBackgroundColor,
    iconSize = 20,
    trailing,
    onPress,
}: PreferenceRowProps) {
    const [hovered, setHovered] = useState(false);
    const themeColors = useThemeColors();

    const resolvedIconColor = iconColor || themeColors.textSecondary;
    const resolvedTitleColor = titleColor || themeColors.textPrimary;
    const resolvedIconBackground = useMemo(
        () => iconBackgroundColor || themeColors.surfaceElevated,
        [iconBackgroundColor, themeColors.surfaceElevated]
    );

    return (
        <Pressable
            style={StyleSheet.flatten([
                styles.row,
                hovered && styles.rowHover,
            ])}
            onPress={onPress}
            disabled={!onPress && !trailing}
            {...(Platform.OS === 'web'
                ? ({
                    onMouseEnter: () => setHovered(true),
                    onMouseLeave: () => setHovered(false),
                } as any)
                : {})}
        >
            <View style={[styles.iconWrap, { backgroundColor: resolvedIconBackground }]}>
                <Icon color={resolvedIconColor} size={iconSize} />
            </View>
            <View style={styles.info}>
                <Typography variant="bodyLg" color={resolvedTitleColor}>
                    {title}
                </Typography>
                {subtitle ? (
                    <Typography variant="bodySm" color={themeColors.textSecondary} style={styles.subtitle}>
                        {subtitle}
                    </Typography>
                ) : null}
            </View>
            {trailing}
        </Pressable>
    );
}

const styles = StyleSheet.create({
    row: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 16,
        paddingHorizontal: 8,
        borderRadius: 14,
    },
    rowHover: {
        backgroundColor: 'rgba(16, 185, 129, 0.03)',
    },
    iconWrap: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 16,
    },
    info: {
        flex: 1,
    },
    subtitle: {
        marginTop: 2,
    },
});
