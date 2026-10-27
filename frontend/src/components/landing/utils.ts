import { Platform } from 'react-native';

export function buildGlassStyle(fallbackColor: string, alpha: number) {
    if (Platform.OS !== 'web') return { backgroundColor: fallbackColor };
    return {
        backgroundColor: `rgba(255,255,255,${alpha})`,
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
    } as any;
}
