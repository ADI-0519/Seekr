import { useState, useEffect } from 'react';
import { Platform } from 'react-native';
import { motion } from '../design/tokens/motion';
import { useReducedMotion } from './useReducedMotion';

export interface EntryAnimationConfig {
    direction?: 'left' | 'up' | 'down';
    duration?: number;
    delay?: number;
    offset?: number;
}

export function useEntryAnimation(config: EntryAnimationConfig = {}) {
    const {
        direction = 'up',
        duration = motion.durationPage,
        delay = 0,
        offset,
    } = config;

    const reducedMotion = useReducedMotion();
    const [entered, setEntered] = useState(false);

    useEffect(() => {
        if (Platform.OS !== 'web' || reducedMotion) {
            setEntered(true);
            return;
        }
        // Wait one frame so the initial state is painted first
        const raf = requestAnimationFrame(() => {
            setEntered(true);
        });
        return () => cancelAnimationFrame(raf);
    }, [reducedMotion]);

    if (Platform.OS !== 'web' || reducedMotion) {
        return {} as any;
    }

    const resolvedOffset = offset ?? getDefaultOffset(direction);
    const transform = entered ? 'none' : getTransform(direction, resolvedOffset);

    return {
        opacity: entered ? 1 : 0,
        transform,
        transition: `opacity ${duration}ms ${motion.easeOut} ${delay}ms, transform ${duration}ms ${motion.easeOut} ${delay}ms`,
        willChange: entered ? 'auto' : 'opacity, transform',
    } as any;
}

function getDefaultOffset(direction: string): number {
    switch (direction) {
        case 'left': return motion.sidebarOffsetX;
        case 'up': return motion.shellOffsetY;
        case 'down': return -motion.miniPlayerOffsetY;
        default: return motion.shellOffsetY;
    }
}

function getTransform(direction: string, offset: number): string {
    switch (direction) {
        case 'left': return `translateX(${offset}px)`;
        case 'up': return `translateY(${offset}px)`;
        case 'down': return `translateY(${offset}px)`;
        default: return `translateY(${offset}px)`;
    }
}
