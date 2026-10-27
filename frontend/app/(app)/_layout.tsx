import { View, StyleSheet } from 'react-native';
import { Slot, Redirect } from 'expo-router';
import { SidebarShell } from '../../src/components/navigation/SidebarShell';
import { AuthBootstrapFallback } from '../../src/components/ui/AuthBootstrapFallback';
import { GlobalProcessingDock } from '../../src/components/processing/GlobalProcessingDock';
import { PageFrame } from '../../src/design/primitives/PageFrame';
import { useBreakpointValue } from '../../src/hooks/useBreakpoint';
import { useSidebarStore } from '../../src/store';
import { useSidebarEntryAnimation } from '../../src/hooks/useSidebarEntryAnimation';
import { useAuth } from '@/hooks';

export default function AppLayout() {
    const { user, isInitializing } = useAuth();
    const { isManuallyCollapsed } = useSidebarStore();
    const sidebarEntryStyle = useSidebarEntryAnimation();

    const sidebarWrapperWidth = useBreakpointValue({
        sm: 0,
        md: 104,
        lg: (isManuallyCollapsed ? 72 : 240) + 40,
        xl: (isManuallyCollapsed ? 72 : 240) + 40
    });
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });

    if (isInitializing) return <AuthBootstrapFallback />;
    if (!user) return <Redirect href="/" />;

    return (
        <View style={styles.container}>
            <PageFrame>
                <Slot />
            </PageFrame>

            <View style={styles.processingDockLayer} pointerEvents="box-none">
                <GlobalProcessingDock />
            </View>

            <View
                style={[
                    styles.sidebarWrapper,
                    isMobile ? styles.sidebarWrapperMobile : { width: sidebarWrapperWidth },
                    sidebarEntryStyle,
                ]}
                pointerEvents="box-none"
            >
                <SidebarShell />
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        flexDirection: 'row',
    },
    sidebarWrapper: {
        position: 'absolute',
        top: 0,
        left: 0,
        bottom: 0,
        zIndex: 50,
    },
    processingDockLayer: {
        ...StyleSheet.absoluteFillObject,
        zIndex: 60,
    },
    sidebarWrapperMobile: {
        top: 'auto',
        bottom: 0,
        left: 0,
        right: 0,
        height: 100,
    }
});
