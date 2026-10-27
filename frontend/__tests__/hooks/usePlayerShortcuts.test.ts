import { renderHook, act } from '@testing-library/react-native';
import { Platform } from 'react-native';
import { usePlayerShortcuts } from '../../src/hooks/usePlayerShortcuts';
import { useVideoPlayerStore } from '../../src/store/videoStore';

// Mock the store
jest.mock('../../src/store/videoStore', () => ({
    useVideoPlayerStore: {
        getState: jest.fn(),
    },
}));

describe('usePlayerShortcuts', () => {
    let mockTogglePlayPause: jest.Mock;
    let mockSeekTo: jest.Mock;
    let mockSetPlaybackRate: jest.Mock;

    beforeEach(() => {
        jest.clearAllMocks();

        mockTogglePlayPause = jest.fn();
        mockSeekTo = jest.fn();
        mockSetPlaybackRate = jest.fn();

        (useVideoPlayerStore.getState as jest.Mock).mockReturnValue({
            activeVideo: { currentTime: 10, duration: 100 },
            togglePlayPause: mockTogglePlayPause,
            seekTo: mockSeekTo,
            setPlaybackRate: mockSetPlaybackRate,
        });

        // Mock window events
        Platform.OS = 'web';
        (global as any).window = {
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            dispatchEvent: jest.fn(),
        };
    });

    it('adds and removes keydown event listener on mount and unmount', () => {
        const addSpy = jest.spyOn(window, 'addEventListener');
        const removeSpy = jest.spyOn(window, 'removeEventListener');

        const { unmount } = renderHook(() => usePlayerShortcuts());

        expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

        unmount();

        expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    });

    it('toggles play/pause on spacebar', () => {
        renderHook(() => usePlayerShortcuts());

        act(() => {
            const event = { key: ' ', preventDefault: jest.fn(), target: { tagName: 'BODY' } };
            const dispatchEvent = window.addEventListener as jest.Mock;
            // simulate the callback invocation that would happen on addEventListener
            if (dispatchEvent.mock.calls.length > 0) {
                const handler = dispatchEvent.mock.calls[0][1];
                handler(event);
            }
        });

        expect(mockTogglePlayPause).toHaveBeenCalled();
    });

    it('seeks forward on ArrowRight and backward on ArrowLeft', () => {
        renderHook(() => usePlayerShortcuts());

        act(() => {
            const getHandler = () => (window.addEventListener as jest.Mock).mock.calls[0][1];
            getHandler()({ key: 'ArrowRight', preventDefault: jest.fn(), target: { tagName: 'BODY' } });
            getHandler()({ key: 'ArrowLeft', preventDefault: jest.fn(), target: { tagName: 'BODY' } });
        });

        expect(mockSeekTo).toHaveBeenCalledWith(15);
        expect(mockSeekTo).toHaveBeenCalledWith(5);
    });

    it('ignores input if typing in a text field', () => {
        renderHook(() => usePlayerShortcuts());

        act(() => {
            const getHandler = () => (window.addEventListener as jest.Mock).mock.calls[0][1];
            getHandler()({ key: ' ', preventDefault: jest.fn(), target: { tagName: 'INPUT' } });
        });

        expect(mockTogglePlayPause).not.toHaveBeenCalled();
    });
});
