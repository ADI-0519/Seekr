import React from 'react';
import { AnimatedPage } from '../../src/design/primitives/AnimatedPage';
import { View, StyleSheet, ScrollView, Platform, Alert } from 'react-native';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { SectionHeader } from '../../src/design/primitives/SectionHeader';
import { Typography } from '../../src/components/ui/Typography';
import { theme } from '../../src/design/index';
import { useAuth, useProfileSummary } from '../../src/hooks';
import { Mail, BookOpen, Clock3, CircleCheckBig, AlertTriangle, LogOut } from 'lucide-react-native';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { router } from 'expo-router';
import { Lecture } from '../../src/types';
import { PreferenceRow } from '@/components/settings/PreferenceRow';

function formatMemberSince(createdAt?: string | null) {
    if (!createdAt) {
        return 'Member since recently';
    }

    const date = new Date(createdAt);
    if (Number.isNaN(date.getTime())) {
        return 'Member since recently';
    }

    return `Member since ${new Intl.DateTimeFormat('en-GB', {
        month: 'long',
        year: 'numeric',
    }).format(date)}`;
}

function formatHours(totalSeconds: number) {
    if (totalSeconds <= 0) {
        return '0h';
    }

    const hours = totalSeconds / 3600;
    if (hours >= 10) {
        return `${Math.round(hours)}h`;
    }

    return `${hours.toFixed(1)}h`;
}

function formatRelativeDate(isoDate: string) {
    const date = new Date(isoDate);
    if (Number.isNaN(date.getTime())) {
        return 'Recently';
    }

    const diffMs = Date.now() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) {
        return 'Just now';
    }
    if (diffHours < 24) {
        return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
    }

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) {
        return 'Yesterday';
    }
    if (diffDays < 7) {
        return `${diffDays} days ago`;
    }

    return new Intl.DateTimeFormat('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    }).format(date);
}

function statusLabel(status: Lecture['status']) {
    switch (status) {
        case 'ready':
            return 'Ready';
        case 'failed':
            return 'Failed';
        case 'processing':
            return 'Processing';
        case 'transcribing':
            return 'Transcribing';
        case 'segmenting':
            return 'Segmenting';
        default:
            return status;
    }
}

export default function ProfileScreen() {
    const { user, signOut } = useAuth();
    const themeColors = useThemeColors();
    const { data, isLoading, isError } = useProfileSummary();

    const displayName = user?.displayName || 'Demo User';
    const email = user?.email || 'demo@seekr.app';
    const initials = displayName.split(' ').map((n: string) => n[0]).join('').toUpperCase();
    const memberSince = formatMemberSince(user?.createdAt);
    const summary = data?.data;
    const recentUploads = summary?.recentUploads || [];

    const stats = [
        { icon: BookOpen, value: isLoading ? '...' : String(summary?.lectureCount ?? 0), label: 'Lectures' },
        { icon: CircleCheckBig, value: isLoading ? '...' : String(summary?.readyLectureCount ?? 0), label: 'Ready' },
        { icon: Clock3, value: isLoading ? '...' : formatHours(summary?.totalDurationSeconds ?? 0), label: 'Content Time' },
    ];

    const confirmSignOut = () => {
        const runSignOut = async () => {
            try {
                await signOut();
                router.replace('/');
            } catch (error: unknown) {
                const message = error instanceof Error ? error.message : 'Failed to sign out';
                Alert.alert('Error', message);
            }
        };

        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            if (window.confirm('Sign out of your account?')) {
                void runSignOut();
            }
            return;
        }

        Alert.alert(
            'Sign Out',
            'Sign out of your account?',
            [
                { text: 'Stay Signed In', style: 'cancel' },
                { text: 'Sign Out', style: 'destructive', onPress: () => void runSignOut() },
            ]
        );
    };

    return (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
            <AnimatedPage style={styles.innerContent}>
                <View style={styles.header}>
                    <Typography variant="displayMd">
                        Profile
                    </Typography>
                </View>

                <View style={styles.content}>
                    <FloatingShell padding={40} style={styles.profileCard} elevation="elevated">
                        <View style={styles.avatarRow}>
                            <View style={[styles.avatar, { backgroundColor: themeColors.primaryEmerald }]}>
                                <Typography variant="headingXl" color={themeColors.surfaceBase}>
                                    {initials}
                                </Typography>
                            </View>
                            <View style={styles.profileInfo}>
                                <Typography variant="headingLg">
                                    {displayName}
                                </Typography>
                                <View style={styles.emailRow}>
                                    <Mail color={themeColors.textSecondary} size={14} style={{ marginRight: 6 }} />
                                    <Typography variant="bodyMd" color={themeColors.textSecondary}>
                                        {email}
                                    </Typography>
                                </View>
                                <View style={[styles.memberBadge, { backgroundColor: themeColors.chipBgReady }]}>
                                    <Typography variant="meta" color={themeColors.primaryEmerald} style={{ fontWeight: '600' }}>
                                        {memberSince}
                                    </Typography>
                                </View>
                            </View>
                        </View>
                    </FloatingShell>

                    <View style={styles.statsRow}>
                        {stats.map((stat) => (
                            <FloatingShell key={stat.label} padding={24} style={styles.statCard}>
                                <View style={[styles.statIconCircle, { backgroundColor: themeColors.chipBgReady }]}>
                                    <stat.icon color={themeColors.primaryEmerald} size={20} />
                                </View>
                                <Typography variant="headingXl" style={{ marginBottom: 4 }}>
                                    {stat.value}
                                </Typography>
                                <Typography variant="bodySm" color={themeColors.textSecondary}>
                                    {stat.label}
                                </Typography>
                            </FloatingShell>
                        ))}
                    </View>

                    <FloatingShell padding={32} style={styles.recentActivityShell}>
                        <SectionHeader title="Recent Uploads" />
                        <View style={styles.activityList}>
                            {isLoading ? (
                                <Typography variant="bodyMd" color={themeColors.textSecondary}>
                                    Loading profile activity...
                                </Typography>
                            ) : isError ? (
                                <Typography variant="bodyMd" color={theme.colors.error}>
                                    Failed to load profile summary.
                                </Typography>
                            ) : recentUploads.length ? (
                                recentUploads.map((upload, index) => {
                                    const isLast = index === recentUploads.length - 1;
                                    const isReady = upload.status === 'ready';
                                    const isFailed = upload.status === 'failed';
                                    const statusColor = isFailed
                                        ? theme.colors.error
                                        : isReady
                                            ? themeColors.primaryEmerald
                                            : themeColors.textSecondary;
                                    const iconColor = isFailed
                                        ? theme.colors.error
                                        : isReady
                                            ? themeColors.primaryEmerald
                                            : themeColors.textSecondary;
                                    const Icon = isFailed ? AlertTriangle : isReady ? CircleCheckBig : Clock3;

                                    return (
                                        <View
                                            key={upload.id}
                                            style={[
                                                styles.activityHistoryRow,
                                                { borderLeftColor: isLast ? 'transparent' : themeColors.borderSubtle },
                                            ]}
                                        >
                                            <View style={[styles.activityTimelineDot, { backgroundColor: themeColors.borderSubtle }]} />
                                            <Icon color={iconColor} size={16} />
                                            <View style={styles.activityHistoryContent}>
                                                <Typography variant="bodyLg">
                                                    Uploaded{' '}
                                                    <Typography
                                                        variant="bodyLg"
                                                        color={themeColors.primaryEmerald}
                                                        style={{ fontWeight: '600' }}
                                                    >
                                                        '{upload.title}'
                                                    </Typography>
                                                </Typography>
                                                <Typography variant="meta" color={themeColors.textSecondary}>
                                                    {formatRelativeDate(upload.createdAt)}
                                                </Typography>
                                                <Typography
                                                    variant="meta"
                                                    color={statusColor}
                                                    style={styles.activityStatus}
                                                >
                                                    {statusLabel(upload.status)}
                                                </Typography>
                                            </View>
                                        </View>
                                    );
                                })
                            ) : (
                                <Typography variant="bodyMd" color={themeColors.textSecondary}>
                                    No uploads yet.
                                </Typography>
                            )}
                        </View>
                    </FloatingShell>

                    <FloatingShell padding={32} style={styles.actionsShell}>
                        <SectionHeader title="Account Settings" />
                        <View style={styles.actionList}>
                            <PreferenceRow
                                icon={LogOut}
                                iconColor={theme.colors.error}
                                titleColor={theme.colors.error}
                                iconBackgroundColor={themeColors.chipBgFailed}
                                iconSize={18}
                                title="Sign Out"
                                onPress={confirmSignOut}
                            />
                        </View>
                    </FloatingShell>
                </View>
            </AnimatedPage>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scroll: {
        paddingBottom: 100,
    },
    innerContent: {
        paddingTop: 34,
        paddingHorizontal: 16,
        overflow: 'visible',
    },
    header: {
        marginBottom: 40,
    },
    content: {
        maxWidth: 720,
        gap: 24,
        overflow: 'visible',
    },
    profileCard: {},
    avatarRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatar: {
        width: 88,
        height: 88,
        borderRadius: 44,
        backgroundColor: theme.colors.primaryEmerald,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 28,
    },
    profileInfo: {
        flex: 1,
    },
    emailRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 6,
    },
    memberBadge: {
        marginTop: 10,
        backgroundColor: theme.colors.chipBgReady,
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: theme.radii.pill,
        alignSelf: 'flex-start',
    },
    statsRow: {
        flexDirection: 'row',
        gap: 20,
        paddingTop: 12,
        paddingBottom: 24,
    },
    statCard: {
        flex: 1,
        alignItems: 'center',
    },
    statIconCircle: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: theme.colors.chipBgReady,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 14,
    },
    actionsShell: {},
    actionList: {
        marginTop: 16,
    },
    recentActivityShell: {},
    activityList: {
        marginTop: 16,
    },
    activityHistoryRow: {
        flexDirection: 'row',
        paddingBottom: 24,
        borderLeftWidth: 2,
        borderLeftColor: theme.colors.borderSubtle,
        paddingLeft: 24,
        position: 'relative',
        marginLeft: 6,
    },
    activityTimelineDot: {
        position: 'absolute',
        left: -5,
        top: 0,
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: theme.colors.borderSubtle,
    },
    activityHistoryContent: {
        flex: 1,
        marginLeft: 16,
        marginTop: -2,
    },
    activityStatus: {
        marginTop: 6,
    },
});
