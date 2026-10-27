import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useBreakpointValue } from '../../hooks/useBreakpoint';
import { useSidebarStore } from '../../store';

interface PageFrameProps {
    children: React.ReactNode;
    style?: StyleProp<ViewStyle>;
    contentContainerStyle?: StyleProp<ViewStyle>;
    withSidebar?: boolean;
}

export const PageFrame: React.FC<PageFrameProps> = ({
    children,
    style,
    contentContainerStyle,
    withSidebar = true,
}) => {
    const { isManuallyCollapsed } = useSidebarStore();
    const insets = useSafeAreaInsets();
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });

    const sidebarWidth = useBreakpointValue({
        sm: 0,
        md: 72,
        lg: isManuallyCollapsed ? 72 : 240,
        xl: isManuallyCollapsed ? 72 : 240
    });

    const sidebarInset = useBreakpointValue({
        sm: 0,
        md: 16,
        lg: 24,
        xl: 24
    });

    const columnGap = useBreakpointValue({
        sm: 0,
        md: 24,
        lg: 32,
        xl: 32
    });

    const pageInset = useBreakpointValue({
        sm: 16,
        md: 24,
        lg: 24,
        xl: 24
    });

    const shadowPadding = 16;

    const effectivePaddingLeft = withSidebar
        ? sidebarInset + sidebarWidth + Math.max(0, columnGap - shadowPadding)
        : Math.max(0, pageInset - shadowPadding);

    const effectivePaddingRight = Math.max(0, pageInset - shadowPadding);

    const topPadding = isMobile ? Math.max(insets.top, 20) : 0;

    return (
        <View style={StyleSheet.flatten([styles.container, { paddingTop: topPadding }, style])}>
            <View
                style={StyleSheet.flatten([
                    styles.content,
                    {
                        paddingLeft: effectivePaddingLeft,
                        paddingRight: effectivePaddingRight,
                    },
                    contentContainerStyle
                ])}
            >
                <View style={styles.contentWrapper}>
                    {children}
                </View>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        width: '100%',
        overflow: 'visible',
    },
    content: {
        flex: 1,
        width: '100%',
        alignSelf: 'stretch',
        overflow: 'visible',
    },
    contentWrapper: {
        flex: 1,
    },
});
