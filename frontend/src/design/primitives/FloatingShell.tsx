import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp, Platform, ViewProps } from 'react-native';
import { theme } from '../index';
import { motion } from '../tokens/motion';
import { useThemeColors, useTheme } from '../../theme/ThemeProvider';

interface FloatingShellProps extends ViewProps {
    children: React.ReactNode;
    style?: StyleProp<ViewStyle>;
    elevation?: 'none' | 'soft' | 'hover' | 'elevated' | 'modal' | 'miniPlayer';
    radius?: keyof typeof theme.radii;
    padding?: keyof typeof theme.spacing | 'none';
    bgColor?: string;
    glass?: boolean;
}

const webShadows = {
    soft: '0 1px 3px rgba(0,0,0,0.04), 0 4px 24px rgba(0,0,0,0.06)',
    hover: '0 2px 6px rgba(0,0,0,0.05), 0 8px 32px rgba(0,0,0,0.09)',
    elevated: '0 2px 8px rgba(0,0,0,0.05), 0 12px 48px rgba(0,0,0,0.08)',
    modal: '0 4px 12px rgba(0,0,0,0.06), 0 24px 64px rgba(0,0,0,0.12)',
    miniPlayer: '0 -1px 4px rgba(0,0,0,0.04), 0 -4px 24px rgba(0,0,0,0.08)',
};

const webShadowsDark = {
    soft: '0 1px 3px rgba(0,0,0,0.12), 0 4px 24px rgba(0,0,0,0.18)',
    hover: '0 2px 6px rgba(0,0,0,0.15), 0 8px 32px rgba(0,0,0,0.22)',
    elevated: '0 2px 8px rgba(0,0,0,0.15), 0 12px 48px rgba(0,0,0,0.20)',
    modal: '0 4px 12px rgba(0,0,0,0.18), 0 24px 64px rgba(0,0,0,0.28)',
    miniPlayer: '0 -1px 4px rgba(0,0,0,0.12), 0 -4px 24px rgba(0,0,0,0.20)',
};

export const FloatingShell: React.FC<FloatingShellProps> = ({
    children,
    style,
    elevation = 'soft',
    radius = 'card',
    padding = 24,
    bgColor,
    glass,
    ...rest
}) => {
    const themeColors = useThemeColors();
    const { cardStyle } = useTheme();
    const isDark = themeColors.surfaceBase !== '#FFFFFF';

    const isGlass = glass !== undefined ? glass : cardStyle === 'transparent';

    const glassBg = isDark ? 'rgba(12, 16, 14, 0.16)' : 'rgba(255, 255, 255, 0.12)';
    const refinedBorder = 'rgba(255, 255, 255, 0.05)';

    const resolvedBg = isGlass ? glassBg : (bgColor || themeColors.surfaceBase);
    const resolvedBorder = refinedBorder;
    const paddingValue = padding === 'none' ? 0 : theme.spacing[padding];

    const shellStyle: any = {
        backgroundColor: resolvedBg,
        borderRadius: theme.radii[radius],
        padding: paddingValue,
        overflow: 'visible',
    };

    if (Platform.OS === 'web' && isGlass) {
        (shellStyle as any).backdropFilter = 'blur(10px)';
        (shellStyle as any).WebkitBackdropFilter = 'blur(10px)';
    }

    if (Platform.OS === 'web' && elevation !== 'none') {
        const shadowKey = elevation === 'soft' ? 'soft'
            : elevation === 'hover' ? 'hover'
                : elevation === 'elevated' ? 'elevated'
                    : elevation === 'modal' ? 'modal'
                        : 'miniPlayer';
        const shadowSet = themeColors.surfaceBase === '#FFFFFF' ? webShadows : webShadowsDark;
        (shellStyle as any).boxShadow = shadowSet[shadowKey];
        (shellStyle as any).transition = `box-shadow ${motion.durationBase}ms ${motion.easeInOut}, transform ${motion.durationBase}ms ${motion.easeInOut}, background-color ${motion.durationPage}ms ${motion.easeInOut}`;
    } else if (elevation !== 'none') {
        const shadowMap: Record<string, any> = {
            soft: theme.shadows.shellSoft,
            hover: theme.shadows.shellHover,
            elevated: theme.shadows.shellElevated,
            modal: theme.shadows.modal,
            miniPlayer: theme.shadows.miniPlayer,
        };
        const key = elevation === 'soft' ? 'soft'
            : elevation === 'hover' ? 'hover'
                : elevation === 'elevated' ? 'elevated'
                    : elevation === 'modal' ? 'modal'
                        : 'miniPlayer';
        Object.assign(shellStyle, shadowMap[key]);
    }

    const extraProps = Platform.OS === 'web' && isGlass ? { dataSet: { glassCard: 'true' } } : {};

    return (
        <View style={StyleSheet.flatten([shellStyle, style])} {...extraProps} {...rest}>
            {children}
        </View>
    );
};
