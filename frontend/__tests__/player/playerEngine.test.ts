import { AVPlaybackStatusSuccess } from 'expo-av';
import { playerEngine } from '../../src/player/playerEngine';

describe('PlayerEngine', () => {
    let mockVideoRef: any;

    beforeEach(() => {
        mockVideoRef = {
            playAsync: jest.fn(),
            pauseAsync: jest.fn(),
            setPositionAsync: jest.fn(),
            setRateAsync: jest.fn(),
            setVolumeAsync: jest.fn(),
            loadAsync: jest.fn(),
            unloadAsync: jest.fn(),
            getStatusAsync: jest.fn(),
        };

        // Attach mock ref privately to the engine
        Object.defineProperty(playerEngine, 'videoRef', {
            value: { current: mockVideoRef },
            writable: true
        });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('plays video if ref exists', async () => {
        await playerEngine.play();
        expect(mockVideoRef.playAsync).toHaveBeenCalled();
    });

    it('pauses video if ref exists', async () => {
        await playerEngine.pause();
        expect(mockVideoRef.pauseAsync).toHaveBeenCalled();
    });

    it('seeks to correct millisecond position', async () => {
        await playerEngine.seekTo(15.5); // 15.5 seconds
        expect(mockVideoRef.setPositionAsync).toHaveBeenCalledWith(15500);
    });

    it('safely ignores invalid seek requests', async () => {
        await playerEngine.seekTo(-10);
        await playerEngine.seekTo(NaN);
        expect(mockVideoRef.setPositionAsync).not.toHaveBeenCalled();
    });

    it('sets playback rate', async () => {
        await playerEngine.setPlaybackRate(1.5);
        expect(mockVideoRef.setRateAsync).toHaveBeenCalledWith(1.5, true);
    });

    it('sets volume', async () => {
        await playerEngine.setVolume(0.8);
        expect(mockVideoRef.setVolumeAsync).toHaveBeenCalledWith(0.8);
    });

    it('loads and unloads URI safely', async () => {
        await playerEngine.load('http://example.com/video.mp4');
        expect(mockVideoRef.loadAsync).toHaveBeenCalledWith({ uri: 'http://example.com/video.mp4' });

        await playerEngine.unload();
        expect(mockVideoRef.unloadAsync).toHaveBeenCalled();
    });

    describe('togglePlayPause', () => {
        it('pauses when currently playing', async () => {
            mockVideoRef.getStatusAsync.mockResolvedValueOnce({
                isLoaded: true,
                isPlaying: true,
            } as AVPlaybackStatusSuccess);

            await playerEngine.togglePlayPause();
            expect(mockVideoRef.pauseAsync).toHaveBeenCalled();
        });

        it('plays when currently paused', async () => {
            mockVideoRef.getStatusAsync.mockResolvedValueOnce({
                isLoaded: true,
                isPlaying: false,
            } as AVPlaybackStatusSuccess);

            await playerEngine.togglePlayPause();
            expect(mockVideoRef.playAsync).toHaveBeenCalled();
        });

        it('ignores toggle if video is not loaded natively', async () => {
            mockVideoRef.getStatusAsync.mockResolvedValueOnce({
                isLoaded: false,
            });

            await playerEngine.togglePlayPause();
            expect(mockVideoRef.playAsync).not.toHaveBeenCalled();
            expect(mockVideoRef.pauseAsync).not.toHaveBeenCalled();
        });
    });

    describe('listeners', () => {
        it('adds, emits, and removes status update listeners', () => {
            const mockListener = jest.fn();
            playerEngine.addListener(mockListener);

            const status = { isLoaded: true, positionMillis: 1000 } as any;
            playerEngine.onStatusUpdate(status);
            expect(mockListener).toHaveBeenCalledWith(status);

            playerEngine.removeListener(mockListener);
            playerEngine.onStatusUpdate({} as any);
            expect(mockListener).toHaveBeenCalledTimes(1);
        });
    });
});
