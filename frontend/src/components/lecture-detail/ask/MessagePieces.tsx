import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, Text, View } from 'react-native';

import { useEntryAnimation } from '@/hooks';
import { useThemeColors } from '@/theme/ThemeProvider';
import { QACitation, SearchResult } from '@/types';
import { Typography } from '@/components/ui/Typography';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from '../lectureDetail.styles';

import { dedupeByProximity, parseAnswerParts } from './utils';
import { InlineText } from './InlineText';

export const ChatBubbleAnimated = ({ children, index }: { children: React.ReactNode; index: number }) => {
    const animStyle = useEntryAnimation({ direction: 'up', delay: index * 50 });
    return <View style={animStyle}>{children}</View>;
};

export const LoadingDots = () => {
    if (Platform.OS !== 'web') return <ActivityIndicator size="small" color="#10B981" />;
    return (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3 }}>
            {[0, 1, 2].map((i) => (
                <View
                    key={i}
                    style={
                        {
                            width: 4,
                            height: 4,
                            borderRadius: 2,
                            backgroundColor: '#10B981',
                            animation: `askPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                        } as any
                    }
                />
            ))}
        </View>
    );
};

const InlineCitationBadge = ({
    n,
    citation,
    onSeek,
}: {
    n: number;
    citation: QACitation;
    onSeek: (t: number) => void;
}) => {
    const [hovered, setHovered] = useState(false);
    const [tipPos, setTipPos] = useState<{ x: number; y: number } | null>(null);
    const badgeRef = useRef<View>(null);
    const themeColors = useThemeColors();

    useEffect(() => {
        if (Platform.OS !== 'web') return;
        const id = `seekr-cite-tip-${n}-${citation.startTime}`;
        const existing = document.getElementById(id);
        if (existing) existing.remove();
        if (!hovered || !tipPos) return;

        const label = citation.segmentTitle || citation.text.slice(0, 60);
        const tip = document.createElement('div');
        tip.id = id;
        tip.style.cssText = [
            'position:fixed',
            `left:${tipPos.x}px`,
            `top:${tipPos.y - 58}px`,
            'transform:translateX(-50%)',
            'z-index:9999',
            'background:#FAFFFE',
            'border:1px solid #E2EDE8',
            'border-radius:8px',
            'padding:10px 12px',
            'max-width:180px',
            'pointer-events:none',
            'box-shadow:0 8px 32px rgba(0,0,0,0.09)',
            'animation:seekrTipIn 160ms cubic-bezier(0.45,0,0.55,1) both',
            'font-family:Plus Jakarta Sans, sans-serif',
        ].join(';');
        tip.innerHTML = [
            `<div style="color:#10B981;font-weight:600;font-size:13px;line-height:16px">${formatDuration(citation.startTime)}</div>`,
            `<div style="color:#6B7280;font-size:12px;line-height:15px;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${label}</div>`,
        ].join('');
        document.body.appendChild(tip);
        return () => {
            tip.remove();
        };
    }, [citation, hovered, n, tipPos]);

    const webHoverProps =
        Platform.OS === 'web'
            ? ({
                onMouseEnter: () => {
                    const rect = (badgeRef.current as any)?.getBoundingClientRect();
                    if (!rect) return;
                    setTipPos({ x: rect.left + rect.width / 2, y: rect.top });
                    setHovered(true);
                },
                onMouseLeave: () => {
                    setHovered(false);
                    setTipPos(null);
                },
            } as any)
            : {};

    return (
        <View
            ref={badgeRef}
            style={[
                Platform.OS === 'web' &&
                ({
                    display: 'inline-flex',
                    verticalAlign: 'baseline',
                    marginHorizontal: 1,
                } as any),
            ]}
            {...webHoverProps}
        >
            <Pressable
                onPress={() => onSeek(citation.startTime)}
                style={({ pressed }) => [
                    {
                        paddingHorizontal: 4,
                        paddingVertical: 1,
                        borderRadius: 4,
                        backgroundColor: hovered ? 'rgba(16, 185, 129, 0.18)' : themeColors.chipBgReady,
                    },
                    Platform.OS === 'web' &&
                    ({
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        transition: 'background-color 120ms cubic-bezier(0.45,0,0.55,1)',
                    } as any),
                    pressed && { opacity: 0.65 },
                ]}
            >
                <Typography
                    variant="meta"
                    color={themeColors.primaryEmerald}
                    style={{ fontWeight: '700', fontSize: 12 }}
                >
                    [{n}]
                </Typography>
            </Pressable>
        </View>
    );
};

export const InlineAnswerText = ({
    text,
    citations,
    onSeek,
}: {
    text: string;
    citations: QACitation[];
    onSeek: (t: number) => void;
}) => {
    const themeColors = useThemeColors();
    const parts = parseAnswerParts(text);

    if (Platform.OS !== 'web') {
        return (
            <Text style={{ color: themeColors.textPrimary, fontSize: 17, lineHeight: 27 }}>
                {parts.map((p, i) => {
                    if (p.kind === 'text') return <InlineText key={i} text={p.content} baseColor={themeColors.textPrimary} />;
                    const c = citations[p.n - 1];
                    if (!c) return <Text key={i}>[{p.n}]</Text>;
                    return (
                        <Text
                            key={i}
                            onPress={() => onSeek(c.startTime)}
                            style={{
                                color: themeColors.primaryEmerald,
                                fontWeight: '700',
                                fontSize: 12,
                            }}
                        >
                            [{p.n}]
                        </Text>
                    );
                })}
            </Text>
        );
    }

    return (
        <View style={{ display: 'block' } as any}>
            {parts.map((p, i) => {
                if (p.kind === 'text') {
                    return <InlineText key={i} text={p.content} baseColor={themeColors.textPrimary} />;
                }
                const c = citations[p.n - 1];
                if (!c) {
                    return (
                        <Text
                            key={i}
                            style={[
                                {
                                    color: themeColors.primaryEmerald,
                                    fontWeight: '700',
                                    fontSize: 12,
                                },
                                { display: 'inline' } as any,
                            ]}
                        >
                            [{p.n}]
                        </Text>
                    );
                }
                return <InlineCitationBadge key={i} n={p.n} citation={c} onSeek={onSeek} />;
            })}
        </View>
    );
};

export const RetrievalResults = ({
    results,
    onSeek,
    styles,
}: {
    results: SearchResult[];
    onSeek: (t: number) => void;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();
    const deduped = dedupeByProximity(results);
    if (deduped.length === 0) {
        return (
            <Typography variant="bodySm" color={themeColors.textSecondary} style={{ fontStyle: 'italic' }}>
                No matching moments found.
            </Typography>
        );
    }
    return (
        <View style={{ gap: 8 }}>
            {deduped.map((r) => (
                <Pressable
                    key={r.id}
                    onPress={() => onSeek(r.timestamp)}
                    style={({ pressed }) => [
                        styles.citationChip,
                        { backgroundColor: themeColors.chipBgReady },
                        Platform.OS === 'web' &&
                        ({ cursor: 'pointer', transition: 'all 160ms cubic-bezier(0.45,0,0.55,1)' } as any),
                        pressed && Platform.OS === 'web' && ({ transform: 'scale(0.98)' } as any),
                    ]}
                >
                    <View style={[styles.citationTimeBadge, { backgroundColor: themeColors.chipBgReady }]}>
                        <Typography
                            variant="bodySm"
                            color={themeColors.primaryEmerald}
                            style={{ fontWeight: '700', fontSize: 14, lineHeight: 20 }}
                        >
                            {formatDuration(r.timestamp)}
                        </Typography>
                    </View>
                    <Typography
                        variant="bodyMd"
                        color={themeColors.textSecondary}
                        numberOfLines={2}
                        style={{ marginLeft: 10, flex: 1, lineHeight: 24 }}
                    >
                        {r.context ? `${r.context} — ` : ''}
                        {r.text}
                    </Typography>
                </Pressable>
            ))}
        </View>
    );
};
