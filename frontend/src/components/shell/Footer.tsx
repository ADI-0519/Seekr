import React, { useState } from 'react';
import { View, StyleSheet, Pressable, Platform, Linking } from 'react-native';
import { Typography } from '../ui/Typography';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { theme } from '../../design/index';
import { useThemeColors } from '../../theme/ThemeProvider';
import { useBreakpointValue } from '../../hooks/useBreakpoint';
import {ROUTES} from "../../constants/routes"
import { useRouter } from 'expo-router';

const FOOTER_COLUMNS = [
    {
        title: 'Product',
        items: [
            { label: 'How it Works', href: ROUTES.HOW_IT_WORKS},
            { label: 'Changelog', href: ROUTES.CHANGELOG},
            { label: 'FAQ', href: ROUTES.FAQ},
        ],
    },
    {
        title: 'Company',
        items: [
            { label: 'About', href: ROUTES.ABOUT},
            { label: 'Contact', href: ROUTES.CONTACT},
        ],
    },
    {
        title: 'Legal',
        items: [
            { label: 'Privacy Policy', href: ROUTES.PRIVACY_POLICY},
            { label: 'Terms', href: ROUTES.TERMS },
            { label: 'Cookies', href: ROUTES.COOKIES},
        ],
    },
    {
        title: 'Resources',
        items: [
            { label: 'GitHub', href: 'https://github.kcl.ac.uk/k23149795/seekr' },
        ],
    },
] as const;

function FooterLink({ label, href }: { label: string; href: string }) {
    const themeColors = useThemeColors();
    const [hovered, setHovered] = useState(false);
    const isExternal = href.startsWith('http://') || href.startsWith('https://');
    const router = useRouter();

    return (
        <Pressable
            onPress={() => {
                if (isExternal) {
                    Linking.openURL(href);
                    return;
                }
                router.push(href as any);
            }}
            {...(Platform.OS === 'web'
                ? {
                    onMouseEnter: () => setHovered(true),
                    onMouseLeave: () => setHovered(false),
                } as any
                : {})}
            style={styles.linkButton}
        >
            <Typography
                variant="bodyMd"
                color={hovered ? themeColors.primaryEmerald : themeColors.textPrimary}
                style={styles.columnItem}
            >
                {label}
            </Typography>
        </Pressable>
    );
}

export const Footer: React.FC = () => {
    const themeColors = useThemeColors();
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });

    return (
        <FloatingShell padding={32} elevation="soft" style={styles.container}>
            <View style={[styles.headerRow, isMobile && styles.headerRowStack]}>
                <View style={styles.brandBlock}>
                    <Typography variant="headingMd" style={styles.brandTitle}>
                        Seekr
                    </Typography>
                </View>
            </View>

            <View style={[styles.columns, isMobile && styles.columnsStack]}>
                {FOOTER_COLUMNS.map((col) => (
                    <View key={col.title} style={styles.column}>
                        <Typography variant="bodySm" color={themeColors.textSecondary} style={styles.columnTitle}>
                            {col.title}
                        </Typography>
                        {col.items.map((item) => (
                            <FooterLink key={item.label} label={item.label} href={item.href} />
                        ))}
                    </View>
                ))}
            </View>

            <View style={[styles.divider, { backgroundColor: themeColors.borderSubtle }]} />

            <View style={[styles.bottomRow, isMobile && styles.bottomRowStack]}>
                <Typography variant="meta" color={themeColors.textSecondary}>
                    © 2026 Seekr
                </Typography>
            </View>
        </FloatingShell>
    );
};

const styles = StyleSheet.create({
    container: {
        marginTop: theme.spacing[48],
        marginBottom: 0,
    },
    headerRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: theme.spacing[24],
        marginBottom: theme.spacing[24],
    },
    headerRowStack: {
        flexDirection: 'column',
    },
    brandBlock: {
        flex: 1,
        maxWidth: 540,
    },
    brandTitle: {
        marginBottom: theme.spacing[16],
    },
    brandBody: {
        lineHeight: 25,
        maxWidth: 520,
    },
    badge: {
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[8],
        borderRadius: theme.radii.pill,
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.06)',
    },
    badgeText: {
        letterSpacing: 0.6,
    },
    columns: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        gap: theme.spacing[24],
    },
    columnsStack: {
        flexDirection: 'column',
    },
    column: {
        flex: 1,
        minWidth: 140,
    },
    columnTitle: {
        marginBottom: theme.spacing[12],
        letterSpacing: 0.5,
        textTransform: 'uppercase',
    },
    linkButton: {
        alignSelf: 'flex-start',
        borderRadius: theme.radii.button,
        paddingHorizontal: theme.spacing[8],
        marginLeft: -theme.spacing[8],
        marginBottom: theme.spacing[4],
        ...(Platform.OS === 'web'
            ? ({
                cursor: 'pointer',
                outlineStyle: 'none',
                outlineWidth: 0,
                outlineColor: 'transparent',
                borderWidth: 0,
                boxShadow: 'none',
                WebkitTapHighlightColor: 'transparent',
            } as any)
            : {}),
    },
    columnItem: {
        marginBottom: theme.spacing[8],
    },
    divider: {
        height: 1,
        marginTop: theme.spacing[24],
        marginBottom: theme.spacing[16],
        opacity: 0.6,
    },
    bottomRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: theme.spacing[16],
    },
    bottomRowStack: {
        flexDirection: 'column',
        alignItems: 'flex-start',
    },
    bottomMeta: {
        textAlign: 'right',
    },
});
