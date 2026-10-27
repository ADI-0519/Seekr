import React, { useState } from 'react';
import { AnimatedPage } from '../../../src/design/primitives/AnimatedPage';
import { View, StyleSheet, ScrollView, TextInput, Pressable, Platform, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { FloatingShell } from '../../../src/design/primitives/FloatingShell';
import { LectureCard } from '../../../src/components/cards/LectureCard';
import { Typography } from '../../../src/components/ui/Typography';
import { PrimaryButton } from '../../../src/components/ui/PrimaryButton';
import { theme } from '../../../src/design/index';
import { Search, BookOpen, UploadCloud, Trash2 } from 'lucide-react-native';
import { useDeleteLecture, useLectures } from '../../../src/hooks';
import { useBreakpointValue } from '../../../src/hooks/useBreakpoint';
import { useThemeColors } from '../../../src/theme/ThemeProvider';
import { Footer } from '../../../src/components/shell/Footer';
import { getResponsiveGridItemStyle, getWebStaggerStyle } from '@/utils/responsiveGrid';

export default function LecturesScreen() {
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const { data: lecturesData, isLoading } = useLectures();
    const deleteMutation = useDeleteLecture();

    const gridCols = useBreakpointValue({ sm: 1, md: 2, lg: 3, xl: 4 });
    const isMobile = useBreakpointValue({ sm: true, md: false, lg: false, xl: false });
    const themeColors = useThemeColors();
    const webNoFocusRing = Platform.OS === 'web'
        ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
        : null;

    const lectures = lecturesData?.items || [];

    const filteredLectures = lectures.filter(lecture =>
        lecture.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lecture.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const confirmDelete = (lectureId: string, lectureTitle: string) => {
        const runDelete = async () => {
            try {
                await deleteMutation.mutateAsync(lectureId);
            } catch (error: unknown) {
                const message = error instanceof Error ? error.message : 'Unable to delete this lecture.';
                if (Platform.OS === 'web' && typeof window !== 'undefined') {
                    window.alert(`Delete Failed\n\n${message}`);
                    return;
                }
                Alert.alert('Delete Failed', message);
            }
        };

        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            if (window.confirm(`Delete "${lectureTitle}"? This cannot be undone.`)) {
                void runDelete();
            }
            return;
        }

        Alert.alert(
            'Delete Lecture',
            `Delete "${lectureTitle}"? This cannot be undone.`,
            [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Delete', style: 'destructive', onPress: () => void runDelete() },
            ]
        );
    };

    return (
        <ScrollView
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.scrollContent}
        >
            <AnimatedPage style={styles.innerContent}>
                <View style={isMobile ? styles.headerRowMobile : styles.headerRowDesktop}>
                    <Typography variant="displayMd">
                        Library
                    </Typography>

                    <View style={styles.searchShellCenter}>
                        <FloatingShell
                            padding={8}
                            radius="pill"
                            style={isMobile ? styles.controlsShellMobile : styles.controlsShellDesktop}
                            elevation="soft"
                        >
                            <View style={styles.searchContainer}>
                                <Search color={themeColors.textSecondary} size={18} />
                                <TextInput
                                    style={[styles.searchInput, { color: themeColors.textPrimary }, webNoFocusRing]}
                                    placeholder="Search lectures..."
                                    placeholderTextColor={themeColors.textSecondary}
                                    value={searchQuery}
                                    onChangeText={setSearchQuery}
                                />
                            </View>
                        </FloatingShell>
                    </View>

                    <PrimaryButton
                        label="Upload"
                        icon={UploadCloud}
                        onPress={() => router.push('/upload')}
                    />
                </View>

                {filteredLectures.length > 0 ? (
                    <View style={[styles.gridContainer, { opacity: isLoading ? 0.5 : 1 }]}>
                        {filteredLectures.map((lecture, index) => (
                            <View
                                key={lecture.id}
                                style={StyleSheet.flatten([
                                    styles.gridItem,
                                    getResponsiveGridItemStyle({ gridCols }),
                                    getWebStaggerStyle({
                                        index,
                                        maxAnimatedItems: gridCols,
                                        includeInitialOpacity: true,
                                        fillMode: 'forwards',
                                    }),
                                ])}
                            >
                                <LectureCard
                                    lecture={lecture}
                                    onPress={() => router.push(`/lectures/${lecture.id}`)}
                                />
                                <Pressable
                                    testID={`delete-lecture-${lecture.id}`}
                                    style={[styles.deleteButton, { backgroundColor: themeColors.surfaceBase, borderColor: themeColors.borderSubtle }]}
                                    onPress={() => confirmDelete(lecture.id, lecture.title)}
                                >
                                    <Trash2 color={themeColors.textSecondary} size={16} />
                                </Pressable>
                            </View>
                        ))}
                    </View>
                ) : (
                    !isLoading && (
                        <FloatingShell padding={48} style={styles.emptyShell}>
                            <View style={[styles.emptyIconCircle, { backgroundColor: themeColors.chipBgReady }]}>
                                <BookOpen color={themeColors.primaryEmerald} size={32} />
                            </View>
                            <Typography variant="headingMd" style={styles.emptyTitle}>
                                {searchQuery ? `No results for "${searchQuery}"` : 'Your library is empty'}
                            </Typography>
                            <Typography variant="bodyMd" color={themeColors.textSecondary} style={styles.emptyBody}>
                                {searchQuery
                                    ? 'Try adjusting your search terms or browse all lectures.'
                                    : 'Upload your first lecture to build your personal knowledge library.'}
                            </Typography>
                            {!searchQuery && (
                                <PrimaryButton
                                    label="Upload Lecture"
                                    icon={UploadCloud}
                                    onPress={() => router.push('/upload')}
                                    style={{ marginTop: 24 }}
                                />
                            )}
                        </FloatingShell>
                    )
                )}

                <Footer />
            </AnimatedPage>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scrollContent: {
        paddingBottom: 100,
    },
    innerContent: {
        paddingTop: 34,
        paddingHorizontal: 16,
        overflow: 'visible',
    },
    headerRowDesktop: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 40,
    },
    headerRowMobile: {
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 16,
        marginBottom: 32,
    },
    controlsShellDesktop: {
        flexDirection: 'row',
        alignItems: 'center',
        width: '100%',
        maxWidth: 500,
    },
    controlsShellMobile: {
        flexDirection: 'row',
        alignItems: 'center',
        width: '100%',
        justifyContent: 'space-between',
        paddingHorizontal: 12,
        paddingVertical: 12,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
        paddingHorizontal: 16,
        gap: 10,
    },
    searchInput: {
        flex: 1,
        fontFamily: theme.typography.fontFamily.medium,
        fontSize: theme.typography.sizes.bodyMd.fontSize,
        height: 36,
    },
    searchShellCenter: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    gridContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 24,
        paddingBottom: 24,
    },
    gridItem: {
        position: 'relative',
    },
    deleteButton: {
        position: 'absolute',
        top: 12,
        right: 12,
        width: 34,
        height: 34,
        borderRadius: 17,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
    },
    emptyShell: {
        alignItems: 'center',
        marginTop: 64,
        marginBottom: theme.spacing[48]
    },
    emptyIconCircle: {
        width: 72,
        height: 72,
        borderRadius: 36,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 20,
    },
    emptyTitle: {
        marginBottom: 8,
        textAlign: 'center',
    },
    emptyBody: {
        textAlign: 'center',
        maxWidth: 360,
        lineHeight: 24,
    },
});
