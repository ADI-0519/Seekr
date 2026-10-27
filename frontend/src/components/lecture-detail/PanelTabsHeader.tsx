import React, { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';
import { FileText, Image as ImageIcon, MessageCircleQuestion, X } from 'lucide-react-native';

import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';
import type { LectureDetailStyles } from './lectureDetail.styles';

export type PanelTabKey = 'transcript' | 'ask' | 'slides';
export const PANEL_TAB_ORDER: PanelTabKey[] = ['transcript', 'ask', 'slides'];

const PANEL_TAB_META: Record<PanelTabKey, { label: string; Icon: typeof FileText }> = {
    transcript: { label: 'Transcript', Icon: FileText },
    ask: { label: 'Ask', Icon: MessageCircleQuestion },
    slides: { label: 'Slides', Icon: ImageIcon },
};

const PanelTabButton = ({
    tab,
    activeTab,
    onPress,
    styles,
}: {
    tab: PanelTabKey;
    activeTab: PanelTabKey;
    onPress: (tab: PanelTabKey) => void;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();
    const [hovered, setHovered] = useState(false);
    const isActive = activeTab === tab;
    const { label, Icon } = PANEL_TAB_META[tab];

    return (
        <Pressable
            style={({ pressed }) => [
                styles.tab,
                isActive && styles.tabActive,
                {
                    borderBottomColor: isActive ? themeColors.primaryEmerald : 'transparent',
                    backgroundColor: isActive
                        ? themeColors.surfaceBase
                        : hovered
                            ? 'rgba(16, 185, 129, 0.07)'
                            : 'transparent',
                },
                Platform.OS === 'web' && {
                    cursor: 'pointer',
                    transition: 'background-color 180ms ease, transform 180ms ease, border-color 180ms ease, color 180ms ease',
                } as any,
                hovered && !isActive && { transform: [{ translateY: -1 }] },
                pressed && { opacity: 0.82 },
            ]}
            onPress={() => onPress(tab)}
            {...(Platform.OS === 'web'
                ? {
                    onHoverIn: () => setHovered(true),
                    onHoverOut: () => setHovered(false),
                } as any
                : {})}
        >
            <View style={styles.tabContent}>
                <Icon color={isActive ? themeColors.primaryEmerald : themeColors.textSecondary} size={18} />
                <Typography variant="bodyMd" color={isActive ? themeColors.primaryEmerald : themeColors.textSecondary} style={styles.tabText}>
                    {label}
                </Typography>
            </View>
        </Pressable>
    );
};

export const PanelTabsHeader = ({
    activeTab,
    onChange,
    onClose,
    styles,
}: {
    activeTab: PanelTabKey;
    onChange: (tab: PanelTabKey) => void;
    onClose?: () => void;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();

    return (
        <View style={[styles.tabsHeader, onClose && styles.tabsHeaderFullscreen, { borderBottomColor: themeColors.borderSubtle, backgroundColor: themeColors.surfaceElevated }]}>
            <View style={styles.tabsHeaderTabs}>
                {PANEL_TAB_ORDER.map((tab) => (
                    <PanelTabButton key={tab} tab={tab} activeTab={activeTab} onPress={onChange} styles={styles} />
                ))}
            </View>

            {onClose ? (
                <Pressable
                    testID="panel-tabs-close"
                    style={[styles.tabsHeaderCloseButton, { borderColor: themeColors.borderSubtle, backgroundColor: themeColors.surfaceBase }]}
                    onPress={onClose}
                >
                    <X color={themeColors.textSecondary} size={16} />
                </Pressable>
            ) : null}
        </View>
    );
};
