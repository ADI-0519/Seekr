import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, Image, Pressable, Platform, Animated } from 'react-native';
import { useRouter, usePathname } from 'expo-router';
import { Home, Search, Library, Settings, User, PanelLeftClose, PanelLeftOpen } from 'lucide-react-native';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design/index';
import { useBreakpointValue } from '../../hooks/useBreakpoint';
import { useThemeColors } from '../../theme/ThemeProvider';
import { useSidebarStore } from '../../store';

interface SidebarItemProps {
    icon: React.ComponentType<any>;
    label: string;
    route: string;
    active: boolean;
    isCollapsed: boolean;
    isMobile: boolean;
    labelOpacity?: Animated.Value;
    pathname: string;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ icon: Icon, label, route, active, isCollapsed, isMobile, labelOpacity, pathname }) => {
    const router = useRouter();
    const [hovered, setHovered] = useState(false);
    const themeColors = useThemeColors();
    const scaleAnim = useRef(new Animated.Value(1)).current;

    const onPressIn = () => {
        if (!isMobile) return;
        Animated.spring(scaleAnim, {
            toValue: 0.85,
            useNativeDriver: true,
            speed: 50,
            bounciness: 4,
        }).start();
    };

    const onPressOut = () => {
        if (!isMobile) return;
        Animated.spring(scaleAnim, {
            toValue: 1,
            useNativeDriver: true,
            speed: 14,
            bounciness: 6,
        }).start();
    };

    return (
        <Pressable
            onPressIn={onPressIn}
            onPressOut={onPressOut}
            style={StyleSheet.flatten([
                styles.navItem,
                isCollapsed && styles.navItemCollapsed,
                isMobile && styles.navItemMobile,
                active && styles.navItemActive,
                hovered && !active && styles.navItemHover,
            ])}
            onPress={() => {
                if (pathname !== route) {
                    router.push(route as any);
                }
            }}
            {...(Platform.OS === 'web' ? {
                onMouseEnter: () => setHovered(true),
                onMouseLeave: () => setHovered(false),
            } as any : {})}
        >
            <Animated.View style={isMobile ? { transform: [{ scale: scaleAnim }], alignItems: 'center' } : undefined}>
                <Icon
                    color={active ? themeColors.primaryEmerald : hovered ? themeColors.textPrimary : themeColors.textSecondary}
                    size={20}
                />
            </Animated.View>
            {!isCollapsed && !isMobile && (
                <Animated.View style={{ opacity: labelOpacity ?? 1 }}>
                    <Typography
                        variant="bodyMd"
                        color={active ? themeColors.primaryEmerald : hovered ? themeColors.textPrimary : themeColors.textSecondary}
                        style={StyleSheet.flatten([
                            styles.navItemText,
                            active && styles.navItemTextActive,
                        ])}
                    >
                        {label}
                    </Typography>
                </Animated.View>
            )}
        </Pressable>
    );
};

export const SidebarShell: React.FC = () => {
    const pathname = usePathname();
    const themeColors = useThemeColors();

    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });
    const isMd = useBreakpointValue({ sm: false, md: true, lg: false, xl: false });

    const { isManuallyCollapsed, toggleSidebar } = useSidebarStore();
    const isCollapsed = isMd || isManuallyCollapsed;

    const labelOpacity = useRef(new Animated.Value(isCollapsed ? 0 : 1)).current;

    useEffect(() => {
        if (isCollapsed) {
            Animated.timing(labelOpacity, { toValue: 0, duration: 80, useNativeDriver: false }).start();
        } else {
            setTimeout(() => {
                Animated.timing(labelOpacity, { toValue: 1, duration: 120, useNativeDriver: false }).start();
            }, 150);
        }
    }, [isCollapsed]);

    if (isMobile) {
        return (
            <FloatingShell style={[styles.mobileContainer, { backgroundColor: themeColors.surfaceBase }]} padding={12} radius="modal" elevation="elevated">
                <SidebarItem icon={Home} label="Home" route="/dashboard" active={pathname === '/dashboard'} isCollapsed={isCollapsed} isMobile={isMobile} pathname={pathname} />
                <SidebarItem icon={Search} label="Search" route="/search" active={pathname === '/search'} isCollapsed={isCollapsed} isMobile={isMobile} pathname={pathname} />
                <SidebarItem icon={Library} label="Library" route="/lectures" active={pathname === '/lectures' || pathname.startsWith('/lectures/')} isCollapsed={isCollapsed} isMobile={isMobile} pathname={pathname} />
                <SidebarItem icon={Settings} label="Settings" route="/settings" active={pathname.startsWith('/settings')} isCollapsed={isCollapsed} isMobile={isMobile} pathname={pathname} />
                <SidebarItem icon={User} label="Profile" route="/profile" active={pathname.startsWith('/profile')} isCollapsed={isCollapsed} isMobile={isMobile} pathname={pathname} />
            </FloatingShell>
        );
    }

    const containerStyle: any = StyleSheet.flatten([
        styles.container,
        isCollapsed && styles.containerCollapsed,
    ]);

    if (Platform.OS === 'web') {
        containerStyle.transition = 'width 250ms cubic-bezier(0.4, 0, 0.2, 1), padding 250ms cubic-bezier(0.4, 0, 0.2, 1)';
    }

    return (
        <FloatingShell
            style={containerStyle}
            padding={isCollapsed ? 12 : 20}
        >
            <View style={StyleSheet.flatten([styles.brandArea, isCollapsed && styles.brandAreaCollapsed])}>
                <View style={styles.brandLogoAndText}>
                    <Image
                        source={require('../../../assets/seekr-logo.png')}
                        style={StyleSheet.flatten([styles.logoImage, isCollapsed && styles.logoImageCollapsed])}
                        resizeMode="contain"
                    />
                    {!isCollapsed && (
                        <Animated.View style={{ opacity: labelOpacity }}>
                            <Typography variant="headingMd" color={themeColors.textPrimary} style={styles.brandTitle}>
                                Seekr
                            </Typography>
                        </Animated.View>
                    )}
                </View>

                {!isCollapsed ? (
                    <Animated.View style={{ opacity: labelOpacity }}>
                        <Pressable
                            onPress={toggleSidebar}
                            style={styles.toggleButton}
                            {...(Platform.OS === 'web' ? {
                                onMouseEnter: (e: any) => { if (e.target.style) e.target.style.opacity = 0.7; },
                                onMouseLeave: (e: any) => { if (e.target.style) e.target.style.opacity = 1; }
                            } as any : {})}
                        >
                            <PanelLeftClose size={20} color={themeColors.textSecondary} />
                        </Pressable>
                    </Animated.View>
                ) : (
                    <Pressable
                        onPress={toggleSidebar}
                        style={styles.toggleButtonCollapsed}
                        {...(Platform.OS === 'web' ? {
                            onMouseEnter: (e: any) => { if (e.target.style) e.target.style.opacity = 0.7; },
                            onMouseLeave: (e: any) => { if (e.target.style) e.target.style.opacity = 1; }
                        } as any : {})}
                    >
                        <PanelLeftOpen size={20} color={themeColors.textSecondary} />
                    </Pressable>
                )}
            </View>

            <View style={StyleSheet.flatten([styles.navContainer, isCollapsed && styles.navContainerCollapsed])}>
                <SidebarItem icon={Home} label="Home" route="/dashboard" active={pathname === '/dashboard'} isCollapsed={isCollapsed} isMobile={isMobile} labelOpacity={labelOpacity} pathname={pathname} />
                <SidebarItem icon={Search} label="Search" route="/search" active={pathname === '/search'} isCollapsed={isCollapsed} isMobile={isMobile} labelOpacity={labelOpacity} pathname={pathname} />
                <SidebarItem icon={Library} label="Library" route="/lectures" active={pathname === '/lectures' || pathname.startsWith('/lectures/')} isCollapsed={isCollapsed} isMobile={isMobile} labelOpacity={labelOpacity} pathname={pathname} />
            </View>

            <View style={StyleSheet.flatten([styles.bottomArea, isCollapsed && styles.bottomAreaCollapsed, { borderTopColor: themeColors.borderSubtle }])}>
                <SidebarItem icon={Settings} label="Settings" route="/settings" active={pathname.startsWith('/settings')} isCollapsed={isCollapsed} isMobile={isMobile} labelOpacity={labelOpacity} pathname={pathname} />
                <SidebarItem icon={User} label="Profile" route="/profile" active={pathname.startsWith('/profile')} isCollapsed={isCollapsed} isMobile={isMobile} labelOpacity={labelOpacity} pathname={pathname} />
            </View>
        </FloatingShell>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        left: 24,
        top: 24,
        bottom: 24,
        width: 240,
        justifyContent: 'flex-start',
    },
    containerCollapsed: {
        left: theme.spacing[16],
        width: 72,
        alignItems: 'center',
    },
    mobileContainer: {
        position: 'absolute',
        bottom: theme.spacing[16],
        left: theme.spacing[16],
        right: theme.spacing[16],
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
    },
    brandArea: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[40],
        paddingHorizontal: theme.spacing[4],
        width: '100%',
    },
    brandAreaCollapsed: {
        flexDirection: 'column',
        justifyContent: 'center',
        paddingHorizontal: 0,
        marginBottom: theme.spacing[24],
    },
    brandLogoAndText: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    logoImage: {
        width: 40,
        height: 40,
        borderRadius: 12,
        marginRight: theme.spacing[12],
        marginBottom: -theme.spacing[4],
    },
    logoImageCollapsed: {
        marginRight: 0,
        marginBottom: 0,
    },
    toggleButton: {
        padding: theme.spacing[4],
        borderRadius: theme.radii.button,
    },
    toggleButtonCollapsed: {
        padding: theme.spacing[8],
        marginTop: theme.spacing[16],
        borderRadius: theme.radii.button,
        alignItems: 'center',
        justifyContent: 'center',
    },
    brandTitle: {
        fontSize: 28,
        lineHeight: 32,
    },
    navContainer: {
        flex: 1,
        gap: 4,
        width: '100%',
    },
    navContainerCollapsed: {
        alignItems: 'center',
    },
    navItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: theme.spacing[12],
        paddingHorizontal: theme.spacing[16],
        borderRadius: theme.radii.button,
        marginLeft: theme.spacing[4],
        marginRight: theme.spacing[4],
    },
    navItemCollapsed: {
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 0,
        marginHorizontal: 0,
        width: 48,
        height: 48,
    },
    navItemMobile: {
        flex: 1,
        justifyContent: 'center',
        paddingVertical: theme.spacing[12],
        paddingHorizontal: 0,
        marginHorizontal: 0,
        alignItems: 'center',
    },
    navItemActive: {
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
    },
    navItemHover: {
        backgroundColor: 'rgba(16, 185, 129, 0.04)',
    },
    navItemText: {
        marginLeft: theme.spacing[16],
        fontWeight: '500',
    },
    navItemTextActive: {
        fontWeight: '600',
    },
    bottomArea: {
        borderTopWidth: 1,
        paddingTop: theme.spacing[20],
        marginTop: theme.spacing[20],
        gap: 4,
        width: '100%',
    },
    bottomAreaCollapsed: {
        alignItems: 'center',
    }
});
