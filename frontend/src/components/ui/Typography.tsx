import React from 'react';
import { Text, TextProps, StyleSheet } from 'react-native';
import { theme } from '../../design/index';
import { TypographyVariant } from '../../design/tokens/typography';
import { useThemeColors } from '../../theme/ThemeProvider';

interface TypographyProps extends TextProps {
    variant?: TypographyVariant;
    color?: string;
    align?: 'auto' | 'left' | 'right' | 'center' | 'justify';
    numberOfLines?: number;
}

export const Typography = React.forwardRef<Text, TypographyProps>(({
    variant = 'bodyMd',
    color,
    align = 'auto',
    style,
    children,
    ...rest
}, ref) => {
    const themeColors = useThemeColors();
    const resolvedColor = color || themeColors.textPrimary;
    const typographyTokens = theme.typography.sizes[variant];
    const weightTokens = theme.typography.weights[variant];

    const getFontFamily = (weight: string) => {
        switch (weight) {
            case '700': return theme.typography.fontFamily.bold;
            case '600': return theme.typography.fontFamily.semibold;
            case '500': return theme.typography.fontFamily.medium;
            default: return theme.typography.fontFamily.regular;
        }
    };

    return (
        <Text
            ref={ref}
            style={StyleSheet.flatten([
                typographyTokens,
                {
                    fontFamily: getFontFamily(weightTokens),
                    color: resolvedColor,
                    textAlign: align,
                },
                style,
            ])}
            {...rest}
        >
            {children}
        </Text>
    );
});

Typography.displayName = 'Typography';
