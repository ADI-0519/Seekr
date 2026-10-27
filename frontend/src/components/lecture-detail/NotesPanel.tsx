import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useQueryClient } from '@tanstack/react-query';
import { Download } from 'lucide-react-native';

import { theme } from '@/design';
import { useThemeColors } from '@/theme/ThemeProvider';
import { GeneratedNote } from '@/types';
import { Typography } from '@/components/ui/Typography';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { api } from '@/services';
import { formatDuration } from '@/utils/formatDuration';
import { InlineText } from './ask/InlineText';

const NOTES_CACHE_PREFIX = 'seekr_notes_';

const NotesMarkdown = ({
    markdown,
    secondaryColor,
}: {
    markdown: string;
    secondaryColor: string;
}) => {
    const lines = markdown.split('\n');
    const elements: React.ReactNode[] = [];

    const normaliseBullet = (s: string): string => {
        const glyphs = ['\u25a0', '\u25cf', '\u2022', '\u25e6', '\u2013', '\u2014'];
        for (const g of glyphs) {
            if (s.startsWith(`${g} `)) return `- ${s.slice(g.length + 1)}`;
            if (s.startsWith(g)) return `- ${s.slice(g.length).trimStart()}`;
        }
        return s;
    };

    lines.forEach((line, i) => {
        const stripped = line.trimStart();
        const indentChars = line.length - stripped.length;
        const level = Math.floor(indentChars / 2);
        const normalised = normaliseBullet(stripped);
        const isBullet = normalised.startsWith('- ') || normalised.startsWith('* ');
        const content = isBullet ? normalised.slice(2) : normalised;

        if (!stripped) {
            elements.push(<View key={i} style={{ height: 6 }} />);
            return;
        }

        if (isBullet) {
            const bullet = level === 0 ? '\u2022' : '\u25e6';
            elements.push(
                <View key={i} style={{ flexDirection: 'row', marginBottom: 5, paddingLeft: level * 16 }}>
                    <Text style={{ color: secondaryColor, fontSize: 15, marginRight: 8, lineHeight: 24 }}>
                        {bullet}
                    </Text>
                    <View style={{ flex: 1 }}>
                        <InlineText text={content} baseColor={secondaryColor} />
                    </View>
                </View>
            );
        } else {
            elements.push(
                <View key={i} style={{ marginBottom: 5 }}>
                    <InlineText text={content} baseColor={secondaryColor} />
                </View>
            );
        }
    });

    return <View>{elements}</View>;
};

const NoteCard = ({ note, index }: { note: GeneratedNote; index: number }) => {
    const [collapsed, setCollapsed] = useState(true);
    const themeColors = useThemeColors();

    return (
        <View
            style={{
                marginBottom: 16,
                borderRadius: theme.radii.controlSm,
                backgroundColor: themeColors.surfaceElevated,
                borderWidth: 1,
                borderColor: themeColors.borderSubtle,
                borderLeftWidth: 3,
                borderLeftColor: themeColors.primaryEmerald,
            }}
        >
            <Pressable
                onPress={() => setCollapsed((prev) => !prev)}
                style={({ pressed }) => [
                    {
                        flexDirection: 'row',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        paddingHorizontal: 16,
                        paddingTop: 14,
                        paddingBottom: 14,
                        borderBottomWidth: collapsed ? 0 : 1,
                        borderBottomColor: themeColors.borderSubtle,
                    },
                    Platform.OS === 'web' ? ({ cursor: 'pointer' } as any) : null,
                    pressed && { opacity: 0.75 },
                ]}
            >
                <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1, gap: 8 }}>
                    <Typography variant="meta" color={themeColors.primaryEmerald} style={{ fontWeight: '700' }}>
                        {String(index + 1).padStart(2, '0')}
                    </Typography>
                    <Typography variant="bodyLg" style={{ fontWeight: '600', flex: 1 }}>
                        {note.title}
                    </Typography>
                </View>
                <View
                    style={{
                        paddingHorizontal: 8,
                        paddingVertical: 3,
                        borderRadius: 6,
                        backgroundColor: themeColors.chipBgReady,
                    }}
                >
                    <Typography variant="meta" color={themeColors.primaryEmerald} style={{ fontWeight: '500' }}>
                        {formatDuration(note.startTime)}
                    </Typography>
                </View>
            </Pressable>
            <View
                style={
                    Platform.OS === 'web'
                        ? ({
                            display: 'grid',
                            gridTemplateRows: collapsed ? '0fr' : '1fr',
                            transition: `grid-template-rows 300ms ${theme.motion.easeOut}`,
                        } as any)
                        : { display: collapsed ? 'none' : 'flex' }
                }
            >
                <View style={Platform.OS === 'web' ? ({ overflow: 'hidden', minHeight: 0 } as any) : undefined}>
                    <View style={{ padding: 16 }}>
                        <NotesMarkdown markdown={note.notesMarkdown} secondaryColor={themeColors.textSecondary} />
                    </View>
                </View>
            </View>
        </View>
    );
};

export const NotesPanel = ({
    lectureId,
    lectureTitle,
    lectureCacheToken,
    isReady,
    notesQuery,
}: {
    lectureId: string;
    lectureTitle: string;
    lectureCacheToken?: string;
    isReady: boolean;
    notesQuery: {
        data?: any;
        isFetching: boolean;
        isError: boolean;
        refetch: () => Promise<any>;
    };
}) => {
    const themeColors = useThemeColors();
    const queryClient = useQueryClient();
    const notes = notesQuery.data?.data?.notes ?? null;
    const isGenerating = notesQuery.isFetching;
    const hasFailed = notesQuery.isError;
    const cacheKey = `${NOTES_CACHE_PREFIX}${lectureCacheToken || lectureId}`;

    useEffect(() => {
        if (notesQuery.data) return;
        AsyncStorage.getItem(cacheKey)
            .then((raw) => {
                if (!raw) return;
                try {
                    queryClient.setQueryData(['notes', lectureId], JSON.parse(raw));
                } catch {
                    // ignore bad cache
                }
            })
            .catch(() => { });
    }, [cacheKey, lectureId, notesQuery.data, queryClient]);

    useEffect(() => {
        if (!notesQuery.data) return;
        AsyncStorage.setItem(cacheKey, JSON.stringify(notesQuery.data)).catch(() => { });
    }, [cacheKey, notesQuery.data]);

    const handleGenerate = () => {
        notesQuery.refetch();
    };

    const handleExport = async () => {
        if (!notes) return;
        try {
            const blob = await api.exportNotesPDF(lectureId, notes);
            if (Platform.OS === 'web' && typeof window !== 'undefined') {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `notes_${lectureTitle.replace(/\s+/g, '_').slice(0, 50)}.pdf`;
                a.click();
                URL.revokeObjectURL(url);
            }
        } catch {
            // allow retry
        }
    };

    return (
        <View>
            <View
                style={{
                    flexDirection: 'row',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 24,
                }}
            >
                <Typography variant="headingMd">Notes</Typography>
                {notes && (
                    <PrimaryButton
                        label="Export PDF"
                        icon={Download}
                        variant="primary"
                        size="md"
                        onPress={handleExport}
                    />
                )}
            </View>

            {!notes && !isGenerating && (
                <View style={{ alignItems: 'center', paddingVertical: 32 }}>
                    <Typography
                        variant="bodyLg"
                        color={themeColors.textSecondary}
                        style={{ marginBottom: 20, textAlign: 'center' }}
                    >
                        {isReady
                            ? 'Generate AI study notes for this lecture.'
                            : 'Notes will be available once processing completes.'}
                    </Typography>
                    {isReady && (
                        <PrimaryButton
                            label="Generate Notes"
                            variant="primary"
                            size="md"
                            onPress={handleGenerate}
                        />
                    )}
                    {hasFailed && (
                        <Typography
                            variant="bodySm"
                            color={themeColors.textSecondary}
                            style={{ marginTop: 12 }}
                        >
                            Something went wrong. Try again.
                        </Typography>
                    )}
                </View>
            )}

            {isGenerating && (
                <View style={{ alignItems: 'center', paddingVertical: 40 }}>
                    <ActivityIndicator color={themeColors.primaryEmerald} style={{ marginBottom: 16 }} />
                    <Typography variant="bodyLg" color={themeColors.textSecondary}>
                        Generating notes...
                    </Typography>
                </View>
            )}

            {notes &&
                notes.map((note: GeneratedNote, index: number) => (
                    <NoteCard key={note.segmentId} note={note} index={index} />
                ))}
        </View>
    );
};
