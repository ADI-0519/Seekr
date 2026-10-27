import { useState, useEffect } from 'react';
import { Platform } from 'react-native';
import { motion } from '../design/tokens/motion';
import { useReducedMotion } from './useReducedMotion';

const SESSION_KEY = 'seekr_sidebar_animated';

export function useSidebarEntryAnimation() {
    const reducedMotion = useReducedMotion();

    const [entered, setEntered] = useState(() => {
        if (Platform.OS !== 'web') return true;
        if (typeof window === 'undefined') return true;
        try {
            return sessionStorage.getItem(SESSION_KEY) === 'true';
        } catch {
            return false;
        }
    });

    useEffect(() => {
        if (Platform.OS !== 'web' || reducedMotion || entered) return;

        const raf = requestAnimationFrame(() => {
            setEntered(true);
            try {
                sessionStorage.setItem(SESSION_KEY, 'true');
            } catch { /* ignore */ }
        });
        return () => cancelAnimationFrame(raf);
    }, [reducedMotion, entered]);

    if (Platform.OS !== 'web' || reducedMotion) {
        return {} as any;
    }

    if (entered) {
        return {} as any;
    }

    return {
        opacity: 0,
        transform: `translateX(${motion.sidebarOffsetX}px)`,
        transition: `opacity ${motion.durationShell}ms ${motion.easeOut}, transform ${motion.durationShell}ms ${motion.easeOut}`,
        willChange: 'opacity, transform',
    } as any;
}
