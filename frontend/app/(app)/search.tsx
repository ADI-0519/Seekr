import React, { useState, useCallback, useRef, useEffect } from 'react';
import { AnimatedPage } from '../../src/design/primitives/AnimatedPage';
import { View, StyleSheet, ScrollView, TextInput, Pressable, Platform } from 'react-native';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { Typography } from '../../src/components/ui/Typography';
import { theme } from '../../src/design/index';
import { Search as SearchIcon, Clock, Sparkles, BookOpen } from 'lucide-react-native';
import { useLectures } from '../../src/hooks';
import { api } from '../../src/services';
import { SearchResult } from '../../src/types';
import { formatDuration } from '../../src/utils/formatDuration';
import { useRouter } from 'expo-router';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { Footer } from '../../src/components/shell/Footer';

function escapeRegex(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export default function SearchScreen() {
    const [query, setQuery] = useState('');
    const [hoverIndex, setHoverIndex] = useState<number | null>(null);
    const [results, setResults] = useState<(SearchResult & { lectureName?: string })[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const { data: lecturesData } = useLectures();
    const router = useRouter();
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const themeColors = useThemeColors();
    const webNoFocusRing = Platform.OS === 'web'
        ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
        : null;

    const toMatchPercent = (score: number) => {
        if (!Number.isFinite(score)) return 0;

        // Calibrate raw reranker scores to a stable, probability-like percentage.
        // This avoids misleading per-query normalization where many relevant
        // results can appear as 0% if the top result has a much higher score.
        const center = -1.0;
        const scale = 1.0;
        const z = (score - center) / scale;
        const prob = 1 / (1 + Math.exp(-z));
        const bounded = Math.max(0.01, Math.min(0.99, prob));
        return Math.round(bounded * 100);
    };

    const performSearch = useCallback(async (text: string) => {
        if (text.length <= 2) {
            setResults([]);
            setIsSearching(false);
            return;
        }

        setIsSearching(true);
        try {
            const lectures = lecturesData?.items?.filter(l => l.status === 'ready') || [];
            const allResults: (SearchResult & { lectureName?: string })[] = [];

            await Promise.all(lectures.map(async (lecture) => {
                try {
                    const response = await api.search(lecture.id, text);
                    if (response.success && response.data.length > 0) {
                        response.data.forEach(r => allResults.push({ ...r, lectureName: lecture.title }));
                    }
                } catch {
                    // Skip lecture on error
                }
            }));

            allResults.sort((a, b) => b.relevanceScore - a.relevanceScore);
            setResults(allResults);
        } catch (e) {
            console.error('Search error:', e);
        } finally {
            setIsSearching(false);
        }
    }, [lecturesData]);

    const handleSearch = (text: string) => {
        setQuery(text);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => performSearch(text), 400);
    };

    useEffect(() => {
        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
                debounceRef.current = null;
            }
        };
    }, []);

    const handleResultPress = (result: SearchResult) => {
        router.push(`/lectures/${result.lectureId}?t=${result.timestamp}`);
    };

    const normalizedQuery = query.trim().toLowerCase();
    const escapedQuery = escapeRegex(query.trim());
    const queryRegex = escapedQuery ? new RegExp(`(${escapedQuery})`, 'gi') : null;

    return (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
            <AnimatedPage style={styles.innerContent}>
                <View style={styles.header}>
                    <Typography variant="displayMd">
                        Search
                    </Typography>
                </View>

                <FloatingShell style={styles.searchShell} padding={16} radius="pill" elevation="soft">
                    <SearchIcon color={themeColors.textSecondary} size={20} />
                    <TextInput
                        style={[styles.searchInput, { color: themeColors.textPrimary }, webNoFocusRing]}
                        placeholder="Search transcripts, lectures, and notes..."
                        placeholderTextColor={themeColors.textSecondary}
                        value={query}
                        onChangeText={handleSearch}
                        autoFocus
                    />
                </FloatingShell>

                <View style={styles.resultsContainer}>
                    {isSearching ? (
                        <View style={styles.loadingState}>
                            <Typography variant="bodyLg" color={themeColors.textSecondary}>
                                Searching for "{query}"...
                            </Typography>
                        </View>
                    ) : results.length > 0 ? (
                        <View style={styles.resultsList}>
                            {results.map((result, index) => (
                                <Pressable
                                    key={`${result.lectureId}-${result.id}-${index}`}
                                    onPress={() => handleResultPress(result)}
                                    onHoverIn={Platform.OS === 'web' ? () => setHoverIndex(index) : undefined}
                                    onHoverOut={Platform.OS === 'web' ? () => setHoverIndex(null) : undefined}
                                >
                                    <FloatingShell
                                        padding={20}
                                        radius="card"
                                        elevation={hoverIndex === index ? 'hover' : 'soft'}
                                        style={StyleSheet.flatten([
                                            styles.resultItem,
                                            hoverIndex === index && styles.resultItemHover,
                                        ])}
                                    >
                                        <View style={[styles.resultIcon, { backgroundColor: themeColors.chipBgReady }]}>
                                            <SearchIcon color={themeColors.primaryEmerald} size={20} />
                                        </View>
                                        <View style={styles.resultInfo}>
                                            {result.lectureName && (
                                                <Typography variant="bodySm" color={themeColors.primaryEmerald} style={{ marginBottom: 4, fontWeight: '600' }}>
                                                    {result.lectureName}
                                                </Typography>
                                            )}
                                            <Typography variant="headingSm" numberOfLines={1}>
                                                "{result.text}"
                                            </Typography>
                                            <Typography variant="bodyMd" color={themeColors.textSecondary} style={{ marginTop: 6 }} numberOfLines={2}>
                                                ...{(queryRegex ? result.context.split(queryRegex) : [result.context]).map((part, i) => {
                                                    const isMatch = normalizedQuery.length > 0 && part.toLowerCase() === normalizedQuery;
                                                    return isMatch ? (
                                                        <Typography key={i} variant="bodyMd" style={{ fontWeight: '700', backgroundColor: 'rgba(16, 185, 129, 0.15)' }}>{part}</Typography>
                                                    ) : (
                                                        <React.Fragment key={i}>{part}</React.Fragment>
                                                    );
                                                })}...
                                            </Typography>
                                            <View style={styles.resultMeta}>
                                                <Clock size={12} color={themeColors.textSecondary} style={{ marginRight: 4 }} />
                                                <Typography variant="meta" color={themeColors.textSecondary}>
                                                    At {formatDuration(result.timestamp)}
                                                </Typography>
                                                <View style={[styles.relevanceBadge, { backgroundColor: themeColors.chipBgReady }]}>
                                                    <Typography variant="meta" color={themeColors.primaryEmerald}>
                                                        {toMatchPercent(result.relevanceScore)}% match
                                                    </Typography>
                                                </View>
                                            </View>
                                        </View>
                                    </FloatingShell>
                                </Pressable>
                            ))}
                        </View>
                    ) : query.length > 2 ? (
                        <FloatingShell padding={48} style={styles.emptyShell}>
                            <View style={styles.emptyIconCircle}>
                                <SearchIcon color={themeColors.textSecondary} size={28} />
                            </View>
                            <Typography variant="headingMd" style={{ marginTop: 16 }}>
                                No results found
                            </Typography>
                            <Typography variant="bodyMd" color={themeColors.textSecondary} style={{ marginTop: 8, textAlign: 'center' }}>
                                Try different keywords or check your spelling.
                            </Typography>
                        </FloatingShell>
                    ) : (
                        <FloatingShell padding={48} style={styles.emptyShell}>
                            <View style={styles.emptyIconCircle}>
                                <Sparkles color={themeColors.primaryEmerald} size={28} />
                            </View>
                            <Typography variant="headingMd" style={{ marginTop: 16 }}>
                                Find anything in your library
                            </Typography>
                            <Typography variant="bodyMd" color={themeColors.textSecondary} style={{ marginTop: 8, textAlign: 'center', maxWidth: 400, lineHeight: 24 }}>
                                Search across {lecturesData?.items?.length || 0} indexed lectures and all their transcripts. Results show exact timestamps so you can jump right in.
                            </Typography>

                            <View style={styles.examplesContainer}>
                                <Typography variant="meta" color={themeColors.textSecondary} style={styles.examplesTitle}>TRY SEARCHING FOR</Typography>
                                <View style={styles.examplesGrid}>
                                    <Pressable
                                        style={[
                                            styles.examplePill,
                                            { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle },
                                        ]}
                                        onPress={() => handleSearch('machine learning')}
                                    >
                                        <SearchIcon size={12} color={themeColors.textSecondary} style={{ marginRight: 6 }} />
                                        <Typography variant="bodySm" color={themeColors.textPrimary}>"machine learning"</Typography>
                                    </Pressable>
                                    <Pressable
                                        style={[
                                            styles.examplePill,
                                            { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle },
                                        ]}
                                        onPress={() => handleSearch('design patterns')}
                                    >
                                        <SearchIcon size={12} color={themeColors.textSecondary} style={{ marginRight: 6 }} />
                                        <Typography variant="bodySm" color={themeColors.textPrimary}>"design patterns"</Typography>
                                    </Pressable>
                                    <Pressable
                                        style={[
                                            styles.examplePill,
                                            { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle },
                                        ]}
                                        onPress={() => handleSearch('linear algebra')}
                                    >
                                        <SearchIcon size={12} color={themeColors.textSecondary} style={{ marginRight: 6 }} />
                                        <Typography variant="bodySm" color={themeColors.textPrimary}>"linear algebra"</Typography>
                                    </Pressable>
                                </View>
                            </View>
                        </FloatingShell>
                    )}

                    <Footer />
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
        marginBottom: theme.spacing[24],
    },
    searchShell: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing[12],
        marginBottom: theme.spacing[32],
    },
    searchInput: {
        flex: 1,
        fontFamily: theme.typography.fontFamily.medium,
        fontSize: theme.typography.sizes.bodyLg.fontSize,
        height: 36,
    },
    resultsContainer: {
        minHeight: 300,
    },
    loadingState: {
        alignItems: 'center',
        paddingVertical: 60,
    },
    resultsList: {
        gap: theme.spacing[16],
        paddingTop: 12,
        paddingBottom: 24,
    },
    resultItem: {
        flexDirection: 'row',
        alignItems: 'flex-start',
    },
    resultItemHover: {
        transform: [{ translateY: -1 }],
    },
    resultIcon: {
        width: 40,
        height: 40,
        borderRadius: 20,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: theme.spacing[16],
    },
    resultInfo: {
        flex: 1,
    },
    resultMeta: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: theme.spacing[8],
    },
    relevanceBadge: {
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: theme.radii.pill,
        marginLeft: 12,
    },
    emptyShell: {
        alignItems: 'center',
    },
    emptyIconCircle: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: theme.colors.chipBgReady,
        alignItems: 'center',
        justifyContent: 'center',
    },
    examplesContainer: {
        marginTop: 40,
        alignItems: 'center',
    },
    examplesTitle: {
        marginBottom: 16,
        letterSpacing: 0.5,
    },
    examplesGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        justifyContent: 'center',
        gap: 12,
        maxWidth: 500,
    },
    examplePill: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 10,
        backgroundColor: theme.colors.surfaceElevated,
        borderRadius: theme.radii.pill,
        borderWidth: 1,
        borderColor: theme.colors.borderSubtle,
    }
});
