import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { theme } from '../index';
import { Typography } from '../../components/ui/Typography';
import { useThemeColors } from '../../theme/ThemeProvider';

interface SectionHeaderProps {
    title: string;
    rightElement?: React.ReactNode;
    style?: StyleProp<ViewStyle>;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
    title,
    rightElement,
    style,
}) => {
    const themeColors = useThemeColors();
    return (
        <View style={StyleSheet.flatten([styles.container, style])}>
            <Typography variant="headingLg" color={themeColors.textPrimary}>
                {title}
            </Typography>
            {rightElement && (
                <View style={styles.rightContainer}>
                    {rightElement}
                </View>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
        width: '100%',
    },
    rightContainer: {
        flexDirection: 'row',
        alignItems: 'center',
    },
});
