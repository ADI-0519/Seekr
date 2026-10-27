import { useEffect } from 'react';
import { Platform } from 'react-native';
import { useVideoPlayerStore } from '../store/videoStore';

export function usePlayerShortcuts() {
    useEffect(() => {
        if (Platform.OS !== 'web') return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if (
                ['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName) ||
                (e.target as HTMLElement).isContentEditable
            ) {
                return;
            }

            const store = useVideoPlayerStore.getState();
            const { activeVideo, togglePlayPause, seekTo, setPlaybackRate } = store;

            if (!activeVideo) return;

            switch (e.key) {
                case ' ':
                    e.preventDefault();
                    togglePlayPause();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    seekTo(Math.max(0, activeVideo.currentTime - 5));
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    seekTo(Math.min(activeVideo.duration, activeVideo.currentTime + 5));
                    break;
                case 'ArrowUp':
                    break;
                case 'ArrowDown':
                    break;
                case '1':
                    e.preventDefault();
                    setPlaybackRate(1.0);
                    break;
                case '2':
                    e.preventDefault();
                    setPlaybackRate(1.25);
                    break;
                case '3':
                    e.preventDefault();
                    setPlaybackRate(1.5);
                    break;
                case '4':
                    e.preventDefault();
                    setPlaybackRate(2.0);
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);
}
