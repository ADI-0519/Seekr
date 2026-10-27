import React, { useState } from 'react';
import { ScrollView, StyleSheet, View, Pressable, Linking, Platform, TextInput } from 'react-native';
import { Redirect, router } from 'expo-router';
import { ArrowUpRight, Clock3, Mail, MessageSquareText, Send, X } from 'lucide-react-native';
import { AnimatedPage } from '../../design/primitives/AnimatedPage';
import { FloatingShell } from '../../design/primitives/FloatingShell';
import { Typography } from '../ui/Typography';
import { theme } from '../../design/index';
import { useTheme, useThemeColors } from '../../theme/ThemeProvider';
import { FooterPageContent } from '../../content/footerPages';

interface InfoPageScreenProps {
    page?: FooterPageContent;
    externalHref?: string;
}

const LONGFORM_SLUGS = new Set(['privacy-policy', 'faq', 'terms', 'cookies']);

function HoverShell({
    children,
    padding,
    style,
    wrapperStyle,
    elevation,
    interactive = false,
}: {
    children: React.ReactNode;
    padding: keyof typeof theme.spacing | 'none';
    style?: any;
    wrapperStyle?: any;
    elevation?: 'soft' | 'elevated';
    interactive?: boolean;
}) {
    const [hovered, setHovered] = useState(false);

    return (
        <View
            {...(Platform.OS === 'web'
                ? {
                    onMouseEnter: () => !interactive && setHovered(true),
                    onMouseLeave: () => !interactive && setHovered(false),
                }
                : {})}
            style={[styles.hoverShellWrap, wrapperStyle]}
        >
            <FloatingShell
                padding={padding}
                elevation={elevation}
                style={[style, hovered && !interactive && styles.hoverShellActive]}
            >
                {children}
            </FloatingShell>
        </View>
    );
}

export const InfoPageScreen: React.FC<InfoPageScreenProps> = ({ page, externalHref }) => {
    const themeColors = useThemeColors();
    const { isDark } = useTheme();
    const [closeHovered, setCloseHovered] = useState(false);
    const [form, setForm] = useState({
        fullName: '',
        email: '',
        subject: '',
        message: '',
    });
    const [formErrors, setFormErrors] = useState<Record<string, string>>({});
    const [submitState, setSubmitState] = useState<'idle' | 'success'>('idle');
    const externalLabel = 'Open resource';
    const isContactPage = page?.slug === 'contact';
    const isLongformPage = page ? LONGFORM_SLUGS.has(page.slug) : false;
    const webInputReset = Platform.OS === 'web'
        ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
        : null;

    const setField = (field: keyof typeof form, value: string) => {
        setForm((prev) => ({ ...prev, [field]: value }));
        setFormErrors((prev) => {
            if (!prev[field]) return prev;
            const next = { ...prev };
            delete next[field];
            return next;
        });
        setSubmitState('idle');
    };

    const validateContactForm = () => {
        const nextErrors: Record<string, string> = {};
        if (!form.fullName.trim()) nextErrors.fullName = 'Please enter your full name.';
        if (!form.email.trim()) {
            nextErrors.email = 'Please enter your email address.';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
            nextErrors.email = 'Please enter a valid email address.';
        }
        if (!form.subject.trim()) nextErrors.subject = 'Please enter a subject.';
        if (!form.message.trim()) {
            nextErrors.message = 'Please enter a message.';
        } else if (form.message.trim().length < 12) {
            nextErrors.message = 'Please provide a little more detail in your message.';
        }
        setFormErrors(nextErrors);
        return Object.keys(nextErrors).length === 0;
    };

    const handleSubmit = () => {
        if (!validateContactForm()) return;
        setSubmitState('success');
        setForm({
            fullName: '',
            email: '',
            subject: '',
            message: '',
        });
        setFormErrors({});
    };

    if (!page) {
        return <Redirect href="/+not-found" />;
    }

    return (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
            <AnimatedPage style={styles.page}>
                <View style={styles.topBar}>
                    <Pressable
                        style={[styles.closeButton, closeHovered && styles.closeButtonHovered]}
                        onPress={() => router.back()}
                        {...(Platform.OS === 'web'
                            ? {
                                onMouseEnter: () => setCloseHovered(true),
                                onMouseLeave: () => setCloseHovered(false),
                            }
                            : {})}
                    >
                        <Typography variant="bodyMd" color={closeHovered ? themeColors.textPrimary : themeColors.textSecondary}>
                            Close
                        </Typography>
                        <X size={18} color={closeHovered ? themeColors.textPrimary : themeColors.textSecondary} />
                    </Pressable>
                </View>

                {isLongformPage ? (
                    <HoverShell
                        padding={32}
                        elevation="elevated"
                        wrapperStyle={styles.fullWidthWrap}
                        style={[styles.longformShell, styles.wideShell]}
                    >
                        <View style={styles.heroTopRow}>
                            <View style={styles.eyebrowChip}>
                                <Typography variant="meta" color={themeColors.primaryEmerald} style={styles.eyebrowText}>
                                    {page.eyebrow}
                                </Typography>
                            </View>
                        </View>

                        <Typography variant="displayMd" style={styles.longformPageTitle}>
                            {page.title}
                        </Typography>
                        <Typography variant="bodySm" color={themeColors.textSecondary} style={styles.longformMeta}>
                            Last updated: 18 March 2026
                        </Typography>
                        <Typography variant="bodyLg" color={themeColors.textSecondary} style={styles.longformIntro}>
                            {page.intro}
                        </Typography>

                        {page.sections.map((section) => (
                            <View key={section.title} style={styles.longformBlock}>
                                <Typography variant="headingLg" style={styles.longformTitle}>
                                    {section.title}
                                </Typography>
                                {section.body.map((paragraph) => (
                                    <Typography
                                        key={paragraph}
                                        variant="bodyLg"
                                        color={themeColors.textSecondary}
                                        style={styles.longformBody}
                                    >
                                        {paragraph}
                                    </Typography>
                                ))}
                            </View>
                        ))}
                    </HoverShell>
                ) : (
                    <HoverShell
                        padding={40}
                        elevation="elevated"
                        wrapperStyle={isContactPage ? styles.fullWidthWrap : undefined}
                        style={[styles.heroShell, isContactPage && styles.contactHeroShell, isContactPage && styles.wideShell]}
                    >
                        <View style={styles.heroTopRow}>
                            <View style={styles.eyebrowChip}>
                                <Typography variant="meta" color={themeColors.primaryEmerald} style={styles.eyebrowText}>
                                    {page.eyebrow}
                                </Typography>
                            </View>
                            {externalHref ? (
                                <Pressable
                                    style={styles.externalButton}
                                    onPress={() => Linking.openURL(externalHref)}
                                >
                                    <Typography variant="bodySm" color={themeColors.textPrimary}>
                                        {externalLabel}
                                    </Typography>
                                    <ArrowUpRight size={16} color={themeColors.textPrimary} />
                                </Pressable>
                            ) : null}
                        </View>

                        <Typography variant="displayMd" style={styles.heroTitle}>
                            {page.title}
                        </Typography>
                        <Typography variant="bodyLg" color={themeColors.textSecondary} style={styles.heroIntro}>
                            {page.intro}
                        </Typography>
                    </HoverShell>
                )}

                {isContactPage ? (
                    <View style={styles.contactGrid}>
                        <View style={styles.contactFormWrap}>
                            <FloatingShell padding={32} style={[styles.contactFormShell, styles.contactLeftColumn]}>
                            <Typography
                                variant="headingLg"
                                style={[styles.contactCardTitle, { color: themeColors.primaryEmerald }]}
                            >
                                Send us a message
                            </Typography>

                            <View style={styles.fieldGroup}>
                                <Typography variant="bodyMd" style={styles.fieldLabel}>
                                    Full Name *
                                </Typography>
                                <TextInput
                                    value={form.fullName}
                                    onChangeText={(value) => setField('fullName', value)}
                                    placeholder="Your full name"
                                    placeholderTextColor={themeColors.textSecondary}
                                    style={[
                                        styles.inputControl,
                                        {
                                            backgroundColor: themeColors.surfaceElevated,
                                            borderColor: formErrors.fullName ? '#EF4444' : themeColors.borderSubtle,
                                            color: themeColors.textPrimary,
                                        },
                                        webInputReset,
                                    ]}
                                />
                                {formErrors.fullName ? (
                                    <Typography variant="bodySm" color="#EF4444" style={styles.errorText}>
                                        {formErrors.fullName}
                                    </Typography>
                                ) : null}
                            </View>

                            <View style={styles.fieldGroup}>
                                <Typography variant="bodyMd" style={styles.fieldLabel}>
                                    Email Address *
                                </Typography>
                                <TextInput
                                    value={form.email}
                                    onChangeText={(value) => setField('email', value)}
                                    placeholder="you@example.com"
                                    placeholderTextColor={themeColors.textSecondary}
                                    keyboardType="email-address"
                                    autoCapitalize="none"
                                    style={[
                                        styles.inputControl,
                                        {
                                            backgroundColor: themeColors.surfaceElevated,
                                            borderColor: formErrors.email ? '#EF4444' : themeColors.borderSubtle,
                                            color: themeColors.textPrimary,
                                        },
                                        webInputReset,
                                    ]}
                                />
                                {formErrors.email ? (
                                    <Typography variant="bodySm" color="#EF4444" style={styles.errorText}>
                                        {formErrors.email}
                                    </Typography>
                                ) : null}
                            </View>

                            <View style={styles.fieldGroup}>
                                <Typography variant="bodyMd" style={styles.fieldLabel}>
                                    Subject *
                                </Typography>
                                <TextInput
                                    value={form.subject}
                                    onChangeText={(value) => setField('subject', value)}
                                    placeholder="What would you like to discuss?"
                                    placeholderTextColor={themeColors.textSecondary}
                                    style={[
                                        styles.inputControl,
                                        {
                                            backgroundColor: themeColors.surfaceElevated,
                                            borderColor: formErrors.subject ? '#EF4444' : themeColors.borderSubtle,
                                            color: themeColors.textPrimary,
                                        },
                                        webInputReset,
                                    ]}
                                />
                                {formErrors.subject ? (
                                    <Typography variant="bodySm" color="#EF4444" style={styles.errorText}>
                                        {formErrors.subject}
                                    </Typography>
                                ) : null}
                            </View>

                            <View style={styles.fieldGroup}>
                                <Typography variant="bodyMd" style={styles.fieldLabel}>
                                    Message *
                                </Typography>
                                <TextInput
                                    value={form.message}
                                    onChangeText={(value) => setField('message', value)}
                                    placeholder="Tell us how we can help."
                                    placeholderTextColor={themeColors.textSecondary}
                                    multiline
                                    textAlignVertical="top"
                                    style={[
                                        styles.textareaControl,
                                        {
                                            backgroundColor: themeColors.surfaceElevated,
                                            borderColor: formErrors.message ? '#EF4444' : themeColors.borderSubtle,
                                            color: themeColors.textPrimary,
                                        },
                                        webInputReset,
                                    ]}
                                />
                                {formErrors.message ? (
                                    <Typography variant="bodySm" color="#EF4444" style={styles.errorText}>
                                        {formErrors.message}
                                    </Typography>
                                ) : null}
                            </View>

                            <Pressable
                                onPress={handleSubmit}
                                style={[
                                    styles.sendButton,
                                    {
                                        backgroundColor: themeColors.primaryEmerald,
                                        shadowColor: themeColors.primaryEmerald,
                                    },
                                ]}
                            >
                                <Send size={16} color={themeColors.surfaceBase} />
                                <Typography variant="bodyMd" color={themeColors.surfaceBase}>
                                    Send Message
                                </Typography>
                            </Pressable>

                            {submitState === 'success' ? (
                                <Typography
                                    variant="bodySm"
                                    color={themeColors.primaryEmerald}
                                    style={styles.successText}
                                >
                                    Your message has been sent successfully. We will be in touch soon.
                                </Typography>
                            ) : null}
                            </FloatingShell>
                        </View>

                        <View style={styles.contactRightColumn}>
                            <HoverShell padding={24} style={styles.contactInfoShell}>
                                <Typography
                                    variant="headingLg"
                                    style={[styles.contactCardTitle, { color: themeColors.primaryEmerald }]}
                                >
                                    Get in touch
                                </Typography>
                                <View style={styles.contactInfoRow}>
                                    <View
                                        style={[
                                            styles.infoIconBadge,
                                            { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.14)' : 'rgba(16, 185, 129, 0.08)' } as any,
                                        ]}
                                    >
                                        <Mail size={18} color={themeColors.primaryEmerald} />
                                    </View>
                                    <View style={styles.infoBody}>
                                        <Typography variant="bodyMd" style={styles.infoLabel}>
                                            Email
                                        </Typography>
                                        <Typography variant="bodyLg" color={themeColors.textSecondary}>
                                            hello@seekr.app
                                        </Typography>
                                    </View>
                                </View>
                                <View style={styles.contactInfoRow}>
                                    <View
                                        style={[
                                            styles.infoIconBadge,
                                            { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.14)' : 'rgba(16, 185, 129, 0.08)' } as any,
                                        ]}
                                    >
                                        <MessageSquareText size={18} color={themeColors.primaryEmerald} />
                                    </View>
                                    <View style={styles.infoBody}>
                                        <Typography variant="bodyMd" style={styles.infoLabel}>
                                            Best for
                                        </Typography>
                                        <Typography variant="bodyLg" color={themeColors.textSecondary}>
                                            Product questions, demos, and support requests
                                        </Typography>
                                    </View>
                                </View>
                            </HoverShell>

                            <HoverShell padding={24} style={styles.contactInfoShell}>
                                <Typography
                                    variant="headingLg"
                                    style={[styles.contactCardTitle, { color: themeColors.primaryEmerald }]}
                                >
                                    Support hours
                                </Typography>
                                <View style={styles.contactInfoRow}>
                                    <View
                                        style={[
                                            styles.infoIconBadge,
                                            { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.14)' : 'rgba(16, 185, 129, 0.08)' } as any,
                                        ]}
                                    >
                                        <Clock3 size={18} color={themeColors.primaryEmerald} />
                                    </View>
                                    <View style={styles.infoBody}>
                                        <Typography variant="bodyLg" color={themeColors.textSecondary} style={styles.infoParagraph}>
                                            Monday - Friday: 9:00 AM - 6:00 PM GMT
                                        </Typography>
                                        <Typography variant="bodyLg" color={themeColors.textSecondary} style={styles.infoParagraph}>
                                            Saturday: 10:00 AM - 4:00 PM GMT
                                        </Typography>
                                        <Typography variant="bodyLg" color={themeColors.textSecondary}>
                                            Sunday: Closed
                                        </Typography>
                                    </View>
                                </View>
                            </HoverShell>
                        </View>
                    </View>
                ) : !isLongformPage ? (
                    <View style={styles.sectionStack}>
                        {page.sections.map((section) => (
                            <HoverShell key={section.title} padding={24} style={styles.sectionShell}>
                                <Typography variant="headingMd" style={styles.sectionTitle}>
                                    {section.title}
                                </Typography>
                                {section.body.map((paragraph) => (
                                    <Typography
                                        key={paragraph}
                                        variant="bodyMd"
                                        color={themeColors.textSecondary}
                                        style={styles.sectionBody}
                                    >
                                        {paragraph}
                                    </Typography>
                                ))}
                            </HoverShell>
                        ))}
                    </View>
                ) : null}
            </AnimatedPage>
        </ScrollView>
    );
};

const styles = StyleSheet.create({
    scrollContent: {
        paddingBottom: 120,
    },
    page: {
        paddingTop: 40,
        paddingLeft: 16,
        paddingRight: 24,
        width: '100%',
        maxWidth: 1160,
        alignSelf: 'center',
    },
    topBar: {
        width: '100%',
        flexDirection: 'row',
        justifyContent: 'flex-end',
        marginBottom: theme.spacing[20],
        paddingRight: 2,
    },
    hoverShellWrap: {
        ...(Platform.OS === 'web'
            ? ({
                transitionDuration: '220ms',
                transitionProperty: 'transform',
                transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
            } as any)
            : {}),
    },
    fullWidthWrap: {
        width: '100%',
    },
    hoverShellActive: {
        ...(Platform.OS === 'web'
            ? ({
                transform: [{ translateY: -4 }, { scale: 1.014 }],
                boxShadow: '0 24px 60px rgba(15, 23, 42, 0.16), 0 10px 28px rgba(16, 185, 129, 0.10)',
                borderColor: 'rgba(255, 255, 255, 0.12)',
                transitionDuration: '220ms',
                transitionProperty: 'transform, box-shadow, border-color',
                transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
            } as any)
            : {}),
    },
    closeButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
        paddingHorizontal: theme.spacing[8],
        paddingVertical: theme.spacing[8],
        borderRadius: theme.radii.button,
        ...(Platform.OS === 'web'
            ? ({ cursor: 'pointer', outlineStyle: 'none', outlineWidth: 0, transitionDuration: '180ms', transitionProperty: 'border-color, background-color, color' } as any)
            : {}),
    },
    closeButtonHovered: {
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.12)',
        backgroundColor: 'rgba(255, 255, 255, 0.04)',
    },
    notFoundShell: {
        maxWidth: 720,
    },
    notFoundTitle: {
        marginBottom: theme.spacing[8],
    },
    heroShell: {
        marginBottom: theme.spacing[24],
        width: '100%',
        maxWidth: 860,
        alignSelf: 'center',
        minHeight: 280,
        justifyContent: 'center',
    },
    contactHeroShell: {
        width: '100%',
        maxWidth: '100%',
    },
    wideShell: {
        width: '100%',
    },
    heroTopRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: theme.spacing[12],
        marginBottom: theme.spacing[16],
        flexWrap: 'wrap',
    },
    eyebrowChip: {
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[8],
        borderRadius: theme.radii.pill,
        backgroundColor: 'rgba(16, 185, 129, 0.08)',
    },
    eyebrowText: {
        letterSpacing: 0.6,
    },
    externalButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
        paddingHorizontal: theme.spacing[12],
        paddingVertical: theme.spacing[8],
        borderRadius: theme.radii.button,
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        ...(Platform.OS === 'web'
            ? ({ cursor: 'pointer', outlineStyle: 'none', outlineWidth: 0 } as any)
            : {}),
    },
    heroTitle: {
        marginBottom: theme.spacing[12],
        maxWidth: 760,
    },
    heroIntro: {
        maxWidth: 760,
        lineHeight: 30,
    },
    sectionStack: {
        gap: theme.spacing[20],
        alignItems: 'center',
    },
    sectionShell: {
        width: '100%',
        maxWidth: 860,
        alignSelf: 'center',
    },
    sectionTitle: {
        marginBottom: theme.spacing[12],
    },
    sectionBody: {
        lineHeight: 26,
        marginBottom: theme.spacing[12],
    },
    contactGrid: {
        width: '100%',
        flexDirection: 'row',
        gap: theme.spacing[16],
        alignItems: 'stretch',
        justifyContent: 'flex-start',
        flexWrap: 'wrap',
    },
    contactLeftColumn: {
        flex: 1.25,
        minWidth: 520,
        maxWidth: 720,
    },
    contactFormWrap: {
        flex: 1.25,
        minWidth: 520,
        maxWidth: 720,
    },
    contactRightColumn: {
        flex: 0.8,
        minWidth: 340,
        maxWidth: 390,
        gap: theme.spacing[24],
        marginHorizontal: theme.spacing[16],
    },
    contactFormShell: {
        width: '100%',
        alignSelf: 'stretch',
    },
    contactInfoShell: {
        width: '100%',
        alignSelf: 'stretch',
    },
    contactCardTitle: {
        marginBottom: theme.spacing[24],
    },
    fieldGroup: {
        marginBottom: theme.spacing[20],
    },
    fieldLabel: {
        marginBottom: theme.spacing[8],
    },
    inputControl: {
        height: 60,
        borderRadius: 18,
        borderWidth: 1,
        paddingHorizontal: theme.spacing[20],
        fontSize: 16,
    },
    textareaControl: {
        height: 180,
        borderRadius: 22,
        borderWidth: 1,
        paddingHorizontal: theme.spacing[20],
        paddingVertical: theme.spacing[16],
        fontSize: 16,
    },
    sendButton: {
        marginTop: theme.spacing[8],
        alignSelf: 'flex-start',
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[8],
        paddingHorizontal: theme.spacing[20],
        paddingVertical: theme.spacing[12],
        borderRadius: theme.radii.button,
        shadowOpacity: 0.18,
        shadowRadius: 18,
        shadowOffset: { width: 0, height: 10 },
        elevation: 4,
    },
    contactInfoRow: {
        flexDirection: 'row',
        alignItems: 'flex-start',
        gap: theme.spacing[12],
        marginBottom: theme.spacing[20],
    },
    infoIconBadge: {
        width: 42,
        height: 42,
        borderRadius: 14,
        alignItems: 'center',
        justifyContent: 'center',
    },
    infoBody: {
        flex: 1,
    },
    infoLabel: {
        marginBottom: theme.spacing[8],
    },
    infoParagraph: {
        marginBottom: theme.spacing[8],
    },
    errorText: {
        marginTop: theme.spacing[8],
    },
    successText: {
        marginTop: theme.spacing[12],
        lineHeight: 22,
    },
    longformShell: {
        width: '100%',
    },
    longformPageTitle: {
        marginBottom: theme.spacing[12],
        maxWidth: 920,
    },
    longformMeta: {
        marginBottom: theme.spacing[20],
        fontStyle: 'italic',
    },
    longformIntro: {
        lineHeight: 31,
        marginBottom: theme.spacing[32],
        maxWidth: 1000,
    },
    longformBlock: {
        marginBottom: theme.spacing[24],
    },
    longformTitle: {
        marginBottom: theme.spacing[12],
    },
    longformBody: {
        lineHeight: 32,
        marginBottom: theme.spacing[12],
        maxWidth: 1000,
    },
});
