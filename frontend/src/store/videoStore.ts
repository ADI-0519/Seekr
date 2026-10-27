import { create } from 'zustand';
import { TopicSegment, Lecture } from '@/types';
import { playerEngine } from '../player/playerEngine';

export type PlayerState = 'closed' | 'mini' | 'expanded';

export type SessionStatus = 'idle' | 'ready' | 'playing' | 'paused' | 'buffering' | 'ended' | 'error';

export interface ActivePlayerState {
    lectureId: string;
    videoUrl: string;
    title: string;
    thumbnailUrl?: string;
    currentTime: number;
    duration: number;
    isPlaying: boolean;
    playbackRate: number;
    topics: TopicSegment[];
    sessionStatus: SessionStatus;
    sourceRoute: string;
    lastKnownPosition: number;
}

interface VideoPlayerStore {
    state: PlayerState;
    activeVideo: ActivePlayerState | null;
    progressByLecture: Record<string, { currentTime: number; duration: number }>;
    isEngineClaimedByLocal: boolean;

    loadSession: (lecture: Lecture, route: string, topics?: TopicSegment[]) => void;
    unloadSession: () => void;
    expandPlayer: () => void;
    closePlayer: () => void;
    minimizePlayer: () => void;
    removeLecture: (lectureId: string) => void;
    clearProgress: () => void;

    claimEngine: () => void;
    releaseEngine: () => void;

    updateTime: (time: number) => void;
    updateDuration: (duration: number) => void;
    updatePlayState: (isPlaying: boolean) => void;
    updatePlaybackRate: (rate: number) => void;
    updateSessionStatus: (status: SessionStatus) => void;

    togglePlayPause: () => Promise<void>;
    seekTo: (time: number) => Promise<void>;
    setVolume: (volume: number) => Promise<void>;
    setPlaybackRate: (rate: number) => Promise<void>;
}

let _rawCurrentTime = 0;
let _lastCommittedTime = -1;

/** Returns the unthrottled playback time for direct progress syncing. */
export function getRawCurrentTime(): number {
    return _rawCurrentTime;
}

export const useVideoPlayerStore = create<VideoPlayerStore>((set, get) => ({
    state: 'closed',
    activeVideo: null,
    progressByLecture: {},
    isEngineClaimedByLocal: false,

    loadSession: (lecture, route, topics) => {
        const { activeVideo } = get();
        const startPosition = Math.max(0, lecture.resumePosition ?? 0);

        if (activeVideo?.lectureId === lecture.id) {
            set({ state: 'mini' });
            return;
        }

        _rawCurrentTime = 0;
        _lastCommittedTime = -1;

        set({
            state: 'mini',
            activeVideo: {
                lectureId: lecture.id,
                videoUrl: lecture.videoUrl,
                title: lecture.title,
                thumbnailUrl: lecture.thumbnailUrl,
                currentTime: startPosition,
                duration: lecture.duration || 0,
                isPlaying: false,
                playbackRate: 1.0,
                topics: topics || [],
                sessionStatus: 'idle',
                sourceRoute: route,
                lastKnownPosition: startPosition,
            },
            progressByLecture: {
                ...get().progressByLecture,
                [lecture.id]: {
                    currentTime: startPosition,
                    duration: lecture.duration || 0,
                },
            },
        });

        if (lecture.videoUrl) {
            playerEngine.load(lecture.videoUrl);
        }
    },

    unloadSession: () => {
        playerEngine.unload();
        _rawCurrentTime = 0;
        _lastCommittedTime = -1;
        set({ state: 'closed', activeVideo: null, isEngineClaimedByLocal: false });
    },

    expandPlayer: () => {
        if (!get().activeVideo) return;
        set({ state: 'expanded' });
    },

    minimizePlayer: () => {
        if (!get().activeVideo) return;
        set({ state: 'mini' });
    },

    closePlayer: () => {
        get().unloadSession();
    },

    removeLecture: (lectureId) => {
        const { activeVideo, progressByLecture } = get();
        const { [lectureId]: _removed, ...remainingProgress } = progressByLecture;

        if (activeVideo?.lectureId === lectureId) {
            get().unloadSession();
            set({ progressByLecture: remainingProgress });
            return;
        }

        set({ progressByLecture: remainingProgress });
    },

    clearProgress: () => {
        set({ progressByLecture: {} });
    },

    claimEngine: () => set({ isEngineClaimedByLocal: true }),

    releaseEngine: () => set({ isEngineClaimedByLocal: false }),

    updateTime: (time) => {
        _rawCurrentTime = time;

        // Quantise updates so React state changes stay cheap during playback.
        const quantised = Math.round(time * 4) / 4; // round to nearest 0.25s
        if (quantised === _lastCommittedTime) return;
        _lastCommittedTime = quantised;

        set((state) => ({
            activeVideo: state.activeVideo
                ? { ...state.activeVideo, currentTime: time, lastKnownPosition: time }
                : null,
            progressByLecture: state.activeVideo
                ? {
                    ...state.progressByLecture,
                    [state.activeVideo.lectureId]: {
                        currentTime: time,
                        duration: state.activeVideo.duration,
                    },
                }
                : state.progressByLecture,
        }));
    },

    updateDuration: (duration) => {
        set((state) => ({
            activeVideo: state.activeVideo
                ? { ...state.activeVideo, duration }
                : null,
            progressByLecture: state.activeVideo
                ? {
                    ...state.progressByLecture,
                    [state.activeVideo.lectureId]: {
                        currentTime: state.activeVideo.currentTime,
                        duration,
                    },
                }
                : state.progressByLecture,
        }));
    },

    updatePlayState: (isPlaying) => {
        set((state) => ({
            activeVideo: state.activeVideo
                ? { ...state.activeVideo, isPlaying }
                : null,
        }));
    },

    updatePlaybackRate: (rate) => {
        set((state) => ({
            activeVideo: state.activeVideo
                ? { ...state.activeVideo, playbackRate: rate }
                : null,
        }));
    },

    updateSessionStatus: (status) => {
        set((state) => ({
            activeVideo: state.activeVideo ? { ...state.activeVideo, sessionStatus: status } : null,
        }));
    },

    togglePlayPause: async () => {
        await playerEngine.togglePlayPause();
    },

    seekTo: async (time) => {
        _rawCurrentTime = time;
        // Invalidate the quantised cache so the seek commits immediately.
        _lastCommittedTime = -1;
        get().updateTime(time);
        await playerEngine.seekTo(time);
    },

    setVolume: async (volume) => {
        await playerEngine.setVolume(volume);
    },

    setPlaybackRate: async (rate) => {
        await playerEngine.setPlaybackRate(rate);
        set((state) => ({
            activeVideo: state.activeVideo
                ? { ...state.activeVideo, playbackRate: rate }
                : null,
        }));
    },
}));

export const useVideoPlayer = () => useVideoPlayerStore();
