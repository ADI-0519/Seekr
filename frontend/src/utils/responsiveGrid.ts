import { Platform } from 'react-native';
import { motion } from '@/design/tokens/motion';

interface GridItemOptions {
    gridCols: number;
    gapPx?: number;
    minWidthPx?: number;
}

interface GridAnimationOptions {
    index: number;
    maxAnimatedItems: number;
    includeInitialOpacity?: boolean;
    fillMode?: 'forwards' | 'backwards' | 'both' | 'none';
}

export function getResponsiveGridItemStyle({
    gridCols,
    gapPx = 24,
    minWidthPx = 280,
}: GridItemOptions) {
    if (Platform.OS !== 'web') {
        return { flexBasis: '100%', minWidth: minWidthPx } as const;
    }
    return {
        width: `calc(${100 / gridCols}% - ${((gridCols - 1) * gapPx) / gridCols}px)`,
        minWidth: minWidthPx,
    } as const;
}

export function getWebStaggerStyle({
    index,
    maxAnimatedItems,
    includeInitialOpacity = false,
    fillMode = 'forwards',
}: GridAnimationOptions) {
    if (Platform.OS !== 'web' || index >= maxAnimatedItems) {
        return {};
    }

    return {
        ...(includeInitialOpacity
            ? {
                opacity: 0,
                transform: `translateY(${motion.shellOffsetY}px)`,
            }
            : {}),
        animation: `cardStaggerIn ${motion.durationPage}ms ${motion.easeOut} ${index * motion.staggerInterval}ms ${fillMode}`,
    } as const;
}
