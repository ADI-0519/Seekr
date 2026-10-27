import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { PrimaryButton } from '../ui/PrimaryButton';
import { theme } from '../../design/index';
import { Plus } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useThemeColors } from '../../theme/ThemeProvider';
import { useBreakpointValue } from '../../hooks/useBreakpoint';

interface TopHeroShellProps {
    userName: string;
}

export const TopHeroShell: React.FC<TopHeroShellProps> = ({
    userName,
}) => {
    const router = useRouter();
    const themeColors = useThemeColors();
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });

    const currentHour = new Date().getHours();
    const greeting = currentHour < 12 ? 'Good Morning' : currentHour < 18 ? 'Good Afternoon' : 'Good Evening';

    return (
        <FloatingShell
            style={[styles.container, isMobile && styles.containerMobile]}
            padding={isMobile ? 24 : 32}
        >
            <View style={[styles.textContainer, isMobile && styles.textContainerMobile]}>
                <Typography variant="displayMd" color={themeColors.textPrimary} style={styles.title}>
                    {greeting}, {userName}
                </Typography>
                <Typography variant="headingSm" color={themeColors.textSecondary} style={styles.secondarytitle}>
                    Ready to continue learning?
                </Typography>
            </View>
            <View style={[styles.actionContainer, isMobile && styles.actionContainerMobile]}>
                <PrimaryButton
                    label="Upload"
                    icon={Plus}
                    onPress={() => router.push('/upload')}
                    size="lg"
                    style={[styles.uploadButton, isMobile && styles.uploadButtonMobile]}
                />
            </View>
        </FloatingShell>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[40],
    },
    containerMobile: {
        flexDirection: 'column',
        alignItems: 'flex-start',
    },
    textContainer: {
        flex: 1,
        paddingRight: theme.spacing[24],
    },
    textContainerMobile: {
        paddingRight: 0,
        marginBottom: theme.spacing[20],
    },
    title: {
        marginBottom: theme.spacing[8],
        marginLeft: theme.spacing[4],
    },
    secondarytitle: {
        marginLeft: theme.spacing[8]
    },
    actionContainer: {
        justifyContent: 'center',
    },
    actionContainerMobile: {
        width: '100%',
        alignItems: 'flex-start',
        marginLeft: theme.spacing[4],
    },
    uploadButton: {
        minWidth: 140,
    },
    uploadButtonMobile: {
        minWidth: 160,
    }
});
