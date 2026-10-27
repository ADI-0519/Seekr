import { useState, useEffect } from 'react';
import { Platform } from 'react-native';

export function useReducedMotion(): boolean {
    const [prefersReduced, setPrefersReduced] = useState(() => {
        if (Platform.OS !== 'web') return false;
        if (typeof window === 'undefined') return false;
        return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    });

    useEffect(() => {
        if (Platform.OS !== 'web' || typeof window === 'undefined') return;

        const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
        const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    }, []);

    return prefersReduced;
}
