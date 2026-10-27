import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '@/services';

type ActiveVideoLike = {
    lectureId?: string;
    isPlaying?: boolean;
    currentTime?: number;
    lastKnownPosition?: number;
} | null | undefined;

type PlaybackPersistenceOptions = {
    lectureId: string;
    activeVideo: ActiveVideoLike;
    isFocused: boolean;
    updatePlayState: (isPlaying: boolean) => void;
    pauseVideo: () => Promise<void> | void;
    persistIntervalMs?: number;
    minPersistDeltaSeconds?: number;
};

export const shouldPersistPlaybackPosition = (
    lastPersistedPosition: number,
    nextPosition: number,
    minDeltaSeconds = 1.5
): boolean => {
    if (!Number.isFinite(nextPosition)) return false;
    return Math.abs(nextPosition - lastPersistedPosition) >= minDeltaSeconds;
};

export const useLecturePlaybackPersistence = ({
    lectureId,
    activeVideo,
    isFocused,
    updatePlayState,
    pauseVideo,
    persistIntervalMs = 15000,
    minPersistDeltaSeconds = 1.5,
}: PlaybackPersistenceOptions) => {
    const [pauseOnLeave, setPauseOnLeave] = useState(true);
    const pauseOnLeaveRef = useRef(true);
    const activeVideoRef = useRef(activeVideo);
    const lastPersistedPositionRef = useRef<number>(-1);
    const wasFocusedRef = useRef(isFocused);

    useEffect(() => {
        let cancelled = false;
        const loadPausePreference = async () => {
            try {
                const response = await api.getUserSettings();
                if (!response.success || cancelled) return;
                setPauseOnLeave(response.data.pauseOnLeave);
            } catch (error) {
                console.warn('[Lecture] Failed to load pause-on-leave preference:', error);
            }
        };

        void loadPausePreference();
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        pauseOnLeaveRef.current = pauseOnLeave;
    }, [pauseOnLeave]);

    useEffect(() => {
        activeVideoRef.current = activeVideo;
    }, [activeVideo]);

    const persistPlaybackPosition = useCallback((video: ActiveVideoLike) => {
        if (!video || video.lectureId !== lectureId) return;

        const position = Math.max(0, Number(video.currentTime ?? video.lastKnownPosition ?? 0));
        if (!shouldPersistPlaybackPosition(lastPersistedPositionRef.current, position, minPersistDeltaSeconds)) {
            return;
        }
        lastPersistedPositionRef.current = position;

        void api.updateLecturePlaybackPosition(lectureId, position).catch((error) => {
            console.warn('[Lecture] Failed to persist playback position:', error);
        });
    }, [lectureId, minPersistDeltaSeconds]);

    const pauseCurrentLectureIfNeeded = useCallback((video: ActiveVideoLike) => {
        if (!pauseOnLeaveRef.current) return;
        if (video?.lectureId !== lectureId || !video?.isPlaying) return;

        updatePlayState(false);
        void pauseVideo();
    }, [lectureId, pauseVideo, updatePlayState]);

    useEffect(() => {
        const wasFocused = wasFocusedRef.current;
        wasFocusedRef.current = isFocused;

        // Only react when the lecture screen actually loses focus.
        if (isFocused || !wasFocused) return;
        persistPlaybackPosition(activeVideo);
        pauseCurrentLectureIfNeeded(activeVideo);
    }, [isFocused, activeVideo, pauseCurrentLectureIfNeeded, persistPlaybackPosition]);

    useEffect(() => {
        if (!isFocused || activeVideo?.lectureId !== lectureId) return;

        const interval = setInterval(() => {
            persistPlaybackPosition(activeVideoRef.current);
        }, persistIntervalMs);

        return () => clearInterval(interval);
    }, [isFocused, activeVideo?.lectureId, lectureId, persistIntervalMs, persistPlaybackPosition]);

    useEffect(() => {
        return () => {
            const currentVideo = activeVideoRef.current;
            persistPlaybackPosition(currentVideo);
            pauseCurrentLectureIfNeeded(currentVideo);
        };
    }, [pauseCurrentLectureIfNeeded, persistPlaybackPosition]);
};
