import React, { useState } from 'react';
import { Image, Linking, Platform, Pressable, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { Menu, X } from 'lucide-react-native';
import { Typography } from '../ui/Typography';
import { PrimaryButton } from '../ui/PrimaryButton';
import { theme } from '../../design';
import { useThemeColors } from '../../theme/ThemeProvider';
import { ROUTES } from '../../constants/routes';

type NavItem = {
    label: string;
    href?: string;
};

const NAV_ITEMS: NavItem[] = [
    { label: 'Product' },
    { label: 'How it Works' },
    { label: 'GitHub', href: ROUTES.GITHUB },
];

interface LandingNavbarProps {
    isMobile: boolean;
    onPressProduct?: () => void;
    onPressHowItWorks?: () => void;
}

export function LandingNavbar({ isMobile, onPressProduct, onPressHowItWorks }: LandingNavbarProps) {
    const colors = useThemeColors();
    const router = useRouter();
    const { width } = useWindowDimensions();
    const shouldStackMobile = width < 760;
    const isTinyMobile = shouldStackMobile && width < 390;
    const isCompactDesktop = !shouldStackMobile && width < 1260;
    const [menuOpen, setMenuOpen] = useState(false);

    return (
        <View
            style={[
                styles.navbar,
                shouldStackMobile && styles.navbarMobile,
                isTinyMobile && styles.navbarTinyMobile,
                isCompactDesktop && styles.navbarCompactDesktop,
                {
                    borderColor: colors.borderSubtle,
                    backgroundColor: Platform.OS === 'web' ? 'rgba(255, 255, 255, 0.62)' : colors.surfaceBase,
                },
            ]}
        >
            <View style={[styles.navLeft, shouldStackMobile && styles.navLeftMobile, isCompactDesktop && styles.navLeftCompactDesktop]}>
                <View style={styles.brandWrap}>
                    <Image
                        source={require('../../../assets/seekr-logo.png')}
                        style={styles.brandLogo}
                        resizeMode="contain"
                    />
                    <Typography variant="headingMd" color={colors.textPrimary} style={styles.brandText}>
                        Seekr
                    </Typography>
                </View>

                {!shouldStackMobile && (
                    <View style={[styles.navLinks, isCompactDesktop && styles.navLinksCompactDesktop]}>
                        {NAV_ITEMS.map((item) => (
                            <LandingNavLink
                                key={item.label}
                                item={item}
                                onPressProduct={onPressProduct}
                                onPressHowItWorks={onPressHowItWorks}
                                isTinyMobile={isTinyMobile}
                                isCompactDesktop={isCompactDesktop}
                            />
                        ))}
                    </View>
                )}
            </View>

            {!shouldStackMobile && (
                <View style={[styles.navRight, isCompactDesktop && styles.navRightCompactDesktop]}>
                    {!isCompactDesktop && (
                        <PrimaryButton
                            label="Log in"
                            variant="ghost"
                            size="lg"
                            onPress={() => router.push('/(auth)/login')}
                        />
                    )}
                    <PrimaryButton
                        label="Get started"
                        size={isCompactDesktop ? 'md' : 'lg'}
                        style={isCompactDesktop ? styles.compactDesktopDashboardButton : undefined}
                        onPress={() => router.push('/(auth)/register')}
                    />
                </View>
            )}

            {shouldStackMobile && (
                <Pressable
                    style={[styles.menuToggle, { borderColor: colors.borderSubtle, backgroundColor: colors.surfaceElevated }]}
                    onPress={() => setMenuOpen((v) => !v)}
                >
                    {menuOpen ? (
                        <X size={18} color={colors.textPrimary} />
                    ) : (
                        <Menu size={18} color={colors.textPrimary} />
                    )}
                </Pressable>
            )}

            {shouldStackMobile && menuOpen && (
                <View style={[styles.mobileMenuPanel, { borderColor: colors.borderSubtle }]}>
                    <View style={[styles.navLinks, styles.navLinksMobile]}>
                        {NAV_ITEMS.map((item) => (
                            <LandingNavLink
                                key={item.label}
                                item={item}
                                onPressProduct={() => {
                                    onPressProduct?.();
                                    setMenuOpen(false);
                                }}
                                onPressHowItWorks={() => {
                                    onPressHowItWorks?.();
                                    setMenuOpen(false);
                                }}
                                isTinyMobile={isTinyMobile}
                            />
                        ))}
                    </View>
                    <View style={[styles.navRight, styles.navRightMobile, isTinyMobile && styles.navRightTinyMobile]}>
                        <PrimaryButton
                            label="Log in"
                            variant="ghost"
                            size="md"
                            style={[styles.mobileActionButton, isTinyMobile && styles.mobileActionButtonTiny]}
                            onPress={() => {
                                setMenuOpen(false);
                                router.push('/(auth)/login');
                            }}
                        />
                        <PrimaryButton
                            label="Get started"
                            size="md"
                            style={[styles.mobileActionButton, isTinyMobile && styles.mobileActionButtonTiny]}
                            onPress={() => {
                                setMenuOpen(false);
                                router.push('/(auth)/register');
                            }}
                        />
                    </View>
                </View>
            )}
        </View>
    );
}

function LandingNavLink({
    item,
    onPressProduct,
    onPressHowItWorks,
    isTinyMobile,
    isCompactDesktop,
}: {
    item: NavItem;
    onPressProduct?: () => void;
    onPressHowItWorks?: () => void;
    isTinyMobile?: boolean;
    isCompactDesktop?: boolean;
}) {
    const [hovered, setHovered] = useState(false);
    const colors = useThemeColors();
    const router = useRouter();

    return (
        <Pressable
            style={[styles.navLinkButton, isTinyMobile && styles.navLinkButtonTiny, isCompactDesktop && styles.navLinkButtonCompactDesktop]}
            onPress={() => {
                if (item.label === 'Product') {
                    onPressProduct?.();
                    return;
                }
                if (item.label === 'How it Works') {
                    onPressHowItWorks?.();
                    return;
                }
                if (!item.href) return;
                if (item.href.startsWith('http')) {
                    void Linking.openURL(item.href);
                } else {
                    router.push(item.href as any);
                }
            }}
            {...(Platform.OS === 'web'
                ? ({
                    onMouseEnter: () => setHovered(true),
                    onMouseLeave: () => setHovered(false),
                } as any)
                : {})}
        >
            <Typography variant={isTinyMobile || isCompactDesktop ? 'bodySm' : 'bodyMd'} color={hovered ? colors.primaryEmerald : colors.textPrimary}>
                {item.label}
            </Typography>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    navbar: {
        position: 'relative',
        zIndex: 60,
        minHeight: 76,
        borderWidth: 1,
        borderRadius: 22,
        paddingHorizontal: theme.spacing[20],
        paddingVertical: theme.spacing[12],
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: theme.spacing[48],
        gap: theme.spacing[12],
        width: '100%',
        maxWidth: 1180,
        alignSelf: 'center',
        ...(Platform.OS === 'web'
            ? ({
                isolation: 'isolate',
                backdropFilter: 'blur(26px)',
                WebkitBackdropFilter: 'blur(26px)',
                boxShadow: '0 10px 32px rgba(16, 185, 129, 0.08)',
            } as any)
            : {}),
    },
    navbarMobile: {
        borderRadius: 18,
        paddingHorizontal: theme.spacing[16],
        paddingVertical: theme.spacing[16],
        marginBottom: theme.spacing[24],
        alignItems: 'center',
        justifyContent: 'space-between',
        flexDirection: 'row',
        gap: theme.spacing[12],
    },
    navbarTinyMobile: {
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[12],
        gap: theme.spacing[12],
    },
    navbarCompactDesktop: {
        paddingHorizontal: theme.spacing[16],
        gap: theme.spacing[8],
    },
    navLeft: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[20],
        flexShrink: 1,
    },
    navLeftMobile: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
        flex: 1,
    },
    navLeftCompactDesktop: {
        gap: theme.spacing[12],
        minWidth: 0,
    },
    brandWrap: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[4],
        marginTop: -4,
    },
    brandLogo: {
        width: 34,
        height: 34,
        borderRadius: 10,
    },
    brandText: {
        lineHeight: 28,
    },
    navLinks: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[16],
    },
    navLinksMobile: {
        width: '100%',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: theme.spacing[8],
    },
    navLinksCompactDesktop: {
        gap: theme.spacing[8],
        minWidth: 0,
    },
    navLinkButton: {
        paddingHorizontal: theme.spacing[8],
        paddingVertical: theme.spacing[8],
        borderRadius: theme.radii.button,
        ...(Platform.OS === 'web' ? ({ cursor: 'pointer' } as any) : {}),
    },
    navLinkButtonTiny: {
        paddingHorizontal: theme.spacing[4],
        paddingVertical: theme.spacing[4],
    },
    navLinkButtonCompactDesktop: {
        paddingHorizontal: theme.spacing[4],
        paddingVertical: theme.spacing[8],
    },
    navRight: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[12],
    },
    navRightMobile: {
        width: '100%',
        justifyContent: 'space-between',
        marginTop: theme.spacing[8],
    },
    navRightTinyMobile: {
        gap: theme.spacing[8],
    },
    navRightCompactDesktop: {
        gap: theme.spacing[4],
        flexShrink: 0,
    },
    mobileActionButton: {
        flex: 1,
    },
    mobileActionButtonTiny: {
        minHeight: 40,
    },
    compactDesktopDashboardButton: {
        minWidth: 124,
    },
    menuToggle: {
        width: 38,
        height: 38,
        borderRadius: 12,
        borderWidth: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    mobileMenuPanel: {
        position: 'absolute',
        top: 72,
        left: theme.spacing[12],
        right: theme.spacing[12],
        borderWidth: 1,
        borderRadius: 14,
        padding: theme.spacing[12],
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        zIndex: 999,
        elevation: 20,
        ...(Platform.OS === 'web'
            ? ({
                backdropFilter: 'blur(22px)',
                WebkitBackdropFilter: 'blur(22px)',
                boxShadow: '0 16px 36px rgba(15, 23, 42, 0.14)',
            } as any)
            : {}),
    },
});
