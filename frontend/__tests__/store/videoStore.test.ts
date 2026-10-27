import { useVideoPlayerStore } from '../../src/store/videoStore';
import { playerEngine } from '../../src/player/playerEngine';
import { Lecture } from '@/types';

// Mock the playerEngine
jest.mock('../../src/player/playerEngine', () => ({
    playerEngine: {
        load: jest.fn(),
        unload: jest.fn(),
        togglePlayPause: jest.fn(),
        seekTo: jest.fn(),
        setVolume: jest.fn(),
        setPlaybackRate: jest.fn(),
    }
}));

const mockLecture: Lecture = {
    id: '123',
    title: 'Test Lecture',
    videoUrl: 'http://example.com/video.mp4',
    thumbnailUrl: 'http://example.com/thumb.jpg',
    duration: 100,
    overview: null,
    status: 'ready',
    createdAt: '2023-01-01',
    updatedAt: '2023-01-01',
    description: 'Test Description',
    userId: 'user1',
};

describe('useVideoPlayerStore', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Reset state
        useVideoPlayerStore.setState({ state: 'closed', activeVideo: null });
    });

    it('should open mini player and load engine when a new lecture is opened', () => {
        const store = useVideoPlayerStore.getState();
        store.loadSession(mockLecture, '/lectures/123');

        const newState = useVideoPlayerStore.getState();
        expect(newState.state).toBe('mini');
        expect(newState.activeVideo?.lectureId).toBe('123');
        expect(newState.activeVideo?.videoUrl).toBe('http://example.com/video.mp4');
        expect(playerEngine.load).toHaveBeenCalledWith('http://example.com/video.mp4');
    });

    it('should expand and minimize player', () => {
        const store = useVideoPlayerStore.getState();
        store.loadSession(mockLecture, '/lectures/123');

        useVideoPlayerStore.getState().expandPlayer();
        expect(useVideoPlayerStore.getState().state).toBe('expanded');

        useVideoPlayerStore.getState().minimizePlayer();
        expect(useVideoPlayerStore.getState().state).toBe('mini');
    });

    it('should close player and unload engine', () => {
        const store = useVideoPlayerStore.getState();
        store.loadSession(mockLecture, '/lectures/123');

        useVideoPlayerStore.getState().closePlayer();
        expect(useVideoPlayerStore.getState().state).toBe('closed');
        expect(useVideoPlayerStore.getState().activeVideo).toBeNull();
        expect(playerEngine.unload).toHaveBeenCalled();
    });

    it('should update sync states (time, duration, play, rate)', () => {
        useVideoPlayerStore.getState().loadSession(mockLecture, '/lectures/123');

        useVideoPlayerStore.getState().updateTime(50);
        expect(useVideoPlayerStore.getState().activeVideo?.currentTime).toBe(50);

        useVideoPlayerStore.getState().updateDuration(200);
        expect(useVideoPlayerStore.getState().activeVideo?.duration).toBe(200);

        useVideoPlayerStore.getState().updatePlayState(true);
        expect(useVideoPlayerStore.getState().activeVideo?.isPlaying).toBe(true);

        useVideoPlayerStore.getState().updatePlaybackRate(1.5);
        expect(useVideoPlayerStore.getState().activeVideo?.playbackRate).toBe(1.5);
    });

    describe('Engine Delegation', () => {
        beforeEach(() => {
            useVideoPlayerStore.getState().loadSession(mockLecture, '/lectures/123');
            jest.clearAllMocks(); // Clear the initial load() call
        });

        it('delegates togglePlayPause correctly', async () => {
            await useVideoPlayerStore.getState().togglePlayPause();
            expect(playerEngine.togglePlayPause).toHaveBeenCalled();
        });

        it('delegates setVolume correctly', async () => {
            await useVideoPlayerStore.getState().setVolume(0.5);
            expect(playerEngine.setVolume).toHaveBeenCalledWith(0.5);
        });

        it('delegates seekTo correctly', async () => {
            await useVideoPlayerStore.getState().seekTo(150);
            expect(playerEngine.seekTo).toHaveBeenCalledWith(150);
        });

        it('delegates setPlaybackRate correctly and updates state', async () => {
            await useVideoPlayerStore.getState().setPlaybackRate(2.0);
            expect(playerEngine.setPlaybackRate).toHaveBeenCalledWith(2.0);
            expect(useVideoPlayerStore.getState().activeVideo?.playbackRate).toBe(2.0);
        });
    });
});
