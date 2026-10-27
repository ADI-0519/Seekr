import React, { useState } from 'react';
import { Pressable, StyleSheet, View, ViewStyle, StyleProp, ActivityIndicator, Platform } from 'react-native';
import { Typography } from './Typography';
import { theme } from '../../design/index';
import { motion } from '../../design/tokens/motion';
import { LucideIcon } from 'lucide-react-native';
import { useThemeColors } from '../../theme/ThemeProvider';

interface PrimaryButtonProps {
    label: string;
    onPress: () => void;
    icon?: LucideIcon | React.ReactNode;
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
    size?: 'md' | 'lg';
    disabled?: boolean;
    loading?: boolean;
    style?: StyleProp<ViewStyle>;
}

export const PrimaryButton: React.FC<PrimaryButtonProps> = ({
    label,
    onPress,
    icon,
    variant = 'primary',
    size = 'md',
    disabled = false,
    loading = false,
    style,
}) => {
    const themeColors = useThemeColors();

    const getBgColor = (pressed: boolean) => {
        if (disabled) return themeColors.borderSubtle;
        switch (variant) {
            case 'primary': return pressed ? themeColors.primaryHover : themeColors.primaryEmerald;
            case 'secondary': return pressed ? themeColors.borderSubtle : themeColors.surfaceElevated;
            case 'outline': return pressed ? themeColors.borderSubtle : 'transparent';
            case 'ghost': return pressed ? themeColors.chipBgReady : 'transparent';
        }
    };

    const getTextColor = () => {
        if (disabled) return themeColors.textSecondary;
        switch (variant) {
            case 'primary': return themeColors.surfaceBase;
            case 'secondary': return themeColors.textPrimary;
            case 'outline': return themeColors.textPrimary;
            case 'ghost': return themeColors.primaryEmerald;
        }
    };

    const getBorderStyles = () => {
        if (variant === 'outline') {
            return {
                borderWidth: 1,
                borderColor: disabled ? themeColors.borderSubtle : themeColors.borderSubtle,
            };
        }
        return {};
    };

    const [hovered, setHovered] = useState(false);

    const getShadowStyles = () => {
        if (variant === 'primary' && !disabled && Platform.OS === 'web') {
            return {
                boxShadow: hovered
                    ? '0 2px 8px rgba(16,185,129,0.25), 0 8px 24px rgba(16,185,129,0.15)'
                    : '0 1px 4px rgba(16,185,129,0.15), 0 4px 12px rgba(16,185,129,0.10)',
                transition: `box-shadow ${motion.durationQuick}ms ${motion.easeInOut}, transform ${motion.durationFast}ms ${motion.easeSnap}`,
            } as any;
        }
        if (variant === 'primary' && !disabled) {
            return {
                shadowColor: themeColors.primaryEmerald,
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.15,
                shadowRadius: 8,
                elevation: 4,
            };
        }
        return {};
    };

    return (
        <Pressable
            onPress={onPress}
            disabled={disabled}
            {...(Platform.OS === 'web' ? {
                onMouseEnter: () => setHovered(true),
                onMouseLeave: () => setHovered(false),
            } as any : {})}
            style={({ pressed }) => StyleSheet.flatten([
                styles.container,
                {
                    backgroundColor: getBgColor(pressed),
                    borderRadius: theme.radii.button,
                    height: size === 'md' ? 44 : 52,
                    paddingHorizontal: size === 'md' ? theme.spacing[20] : theme.spacing[32],
                    opacity: disabled ? 0.6 : 1,
                    transform: [{ scale: hovered && !pressed ? 1.02 : pressed ? 0.98 : 1 }],
                },
                getBorderStyles(),
                getShadowStyles(),
                style,
            ])}
        >
            <View style={styles.content}>
                {loading ? (
                    <ActivityIndicator
                        color={getTextColor()}
                        style={styles.icon}
                        size="small"
                    />
                ) : (
                    icon && (
                        React.isValidElement(icon) ? (
                            <View style={styles.icon}>{icon}</View>
                        ) : (
                            React.createElement(icon as any, {
                                color: getTextColor(),
                                size: size === 'md' ? 18 : 20,
                                style: styles.icon as any
                            })
                        )
                    )
                )}
                <Typography
                    variant={size === 'md' ? "bodyMd" : "bodyLg"}
                    color={getTextColor()}
                    style={styles.label}
                >
                    {label}
                </Typography>
            </View>
        </Pressable>
    );
};

const styles = StyleSheet.create({
    container: {
        justifyContent: 'center',
        alignItems: 'center',
    },
    content: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
    },
    icon: {
        marginRight: theme.spacing[8],
    },
    label: {
        fontWeight: '600',
    }
});
