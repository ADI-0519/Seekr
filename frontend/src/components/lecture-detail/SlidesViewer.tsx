import React, { useState } from 'react';
import { ActivityIndicator, Image, Platform, Pressable, ScrollView, View } from 'react-native';
import { Image as ImageIcon, ZoomIn, ZoomOut } from 'lucide-react-native';

import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import { SlideFrame } from '@/types';
import { formatDuration } from '@/utils/formatDuration';
import type { LectureDetailStyles } from './lectureDetail.styles';
export const SlidesViewer = ({ slides, onDownload, isDownloading, onSeek, styles }: {
    slides: SlideFrame[];
    onDownload: () => void;
    isDownloading: boolean;
    onSeek: (time: number) => void;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();
    const [zoomLevel, setZoomLevel] = useState(1);
    const hasSlides = slides.length > 0;

    const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.25, 3));
    const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.25, 0.5));
    const handleResetZoom = () => setZoomLevel(1);

    return (
        <View style={styles.slidesViewerContainer}>
            {/* Toolbar Area */}
            <View style={[styles.slidesToolbar, { borderBottomColor: themeColors.borderSubtle }]}>
                <View style={styles.zoomControls}>
                    <Pressable onPress={handleZoomOut} style={styles.iconButton} disabled={!hasSlides}>
                        <ZoomOut size={18} color={hasSlides ? themeColors.textPrimary : themeColors.textSecondary} />
                    </Pressable>
                    <Typography variant="bodyMd" style={{ width: 44, textAlign: 'center' }}>
                        {Math.round(zoomLevel * 100)}%
                    </Typography>
                    <Pressable onPress={handleZoomIn} style={styles.iconButton} disabled={!hasSlides}>
                        <ZoomIn size={18} color={hasSlides ? themeColors.textPrimary : themeColors.textSecondary} />
                    </Pressable>
                    {zoomLevel !== 1 && (
                        <Pressable onPress={handleResetZoom} style={{ marginLeft: 8 }}>
                            <Typography variant="bodySm" color={themeColors.textSecondary}>Reset</Typography>
                        </Pressable>
                    )}
                </View>

                <PrimaryButton
                    label={hasSlides ? 'Download' : 'Processing...'}
                    onPress={onDownload}
                    disabled={!hasSlides || isDownloading}
                    style={{ height: 36, paddingHorizontal: 16 }}
                />
            </View>

            {/* Main Area */}
            {hasSlides ? (
                <ScrollView
                    style={styles.slidesScrollArea}
                    contentContainerStyle={styles.slidesScrollContent}
                    showsVerticalScrollIndicator={true}
                    persistentScrollbar={true}
                    showsHorizontalScrollIndicator={false}
                >
                    <View style={Platform.OS === 'web'
                        ? { transform: `scale(${zoomLevel})`, transformOrigin: 'top center', paddingBottom: 40 } as any
                        : { transform: [{ scale: zoomLevel }], paddingBottom: 40 }
                    }>
                        {slides.map((slide, index) => (
                            <View key={slide.id} style={[styles.slideCard, { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle }]}>
                                <View style={styles.slideCardHeader}>
                                    <Typography variant="meta" color={themeColors.textSecondary} style={{ fontWeight: '500' }}>
                                        Slide {index + 1}
                                    </Typography>
                                    <Pressable onPress={() => onSeek(slide.startTime)} style={[styles.timestampPill, { backgroundColor: themeColors.surfaceBase }]}>
                                        <Typography variant="meta" color={themeColors.primaryEmerald}>
                                            {formatDuration(slide.startTime)}
                                        </Typography>
                                    </Pressable>
                                </View>

                                {slide.frameUrl ? (
                                    <Image
                                        source={{ uri: slide.frameUrl }}
                                        style={styles.slideImage}
                                        resizeMode="contain"
                                    />
                                ) : (
                                    <View style={[styles.slidePlaceholder, { backgroundColor: themeColors.surfaceBase }]}>
                                        <ImageIcon size={32} color={themeColors.textSecondary} style={{ marginBottom: 12, opacity: 0.5 }} />
                                        <Typography variant="bodySm" color={themeColors.textSecondary}>Image missing</Typography>
                                    </View>
                                )}
                            </View>
                        ))}
                    </View>
                </ScrollView>
            ) : (
                <View style={styles.askEmptyState}>
                    <ActivityIndicator color={themeColors.primaryEmerald} style={{ marginBottom: 16 }} />
                    <Typography variant="bodyLg" color={themeColors.textSecondary} style={{ textAlign: 'center' }}>
                        Processing slides...
                    </Typography>
                    <Typography variant="bodySm" color={themeColors.textSecondary} style={{ textAlign: 'center', marginTop: 8, opacity: 0.7 }}>
                        Visuals are being extracted from the video
                    </Typography>
                </View>
            )}
        </View>
    );
};
