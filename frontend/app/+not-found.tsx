import { View, StyleSheet } from 'react-native';
import { Link } from 'expo-router';
import { Typography } from '../src/components/ui/Typography';
import { theme } from '../src/design/index';
import { useThemeColors } from '../src/theme/ThemeProvider';

export default function NotFoundScreen() {
    const themeColors = useThemeColors();

    return (
        <View style={styles.container}>
            <Typography variant="displayMd" color={themeColors.textPrimary}>
                Page Not Found
            </Typography>
            <Typography variant="bodyLg" color={themeColors.textSecondary} style={{ marginTop: 16 }}>
                This page doesn't exist.
            </Typography>
            <Link href="/" style={styles.link}>
                <Typography variant="bodyLg" color={themeColors.primaryEmerald}>
                    Go to Home
                </Typography>
            </Link>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
    },
    link: {
        marginTop: 24,
    }
});
