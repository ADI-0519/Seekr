import { act, renderHook } from '@testing-library/react-native';

import { api } from '../../src/services';
import { useLecturePlaybackPersistence } from '../../src/components/lecture-detail/hooks/useLecturePlaybackPersistence';

jest.mock('../../src/services', () => ({
    api: {
        getUserSettings: jest.fn(),
        updateLecturePlaybackPosition: jest.fn(),
    },
}));

describe('useLecturePlaybackPersistence', () => {
    type HookProps = {
        video: any;
        focused: boolean;
    };

    const updatePlayState = jest.fn();
    const pauseVideo = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();
        (api.getUserSettings as jest.Mock).mockResolvedValue({
            success: true,
            data: { pauseOnLeave: true },
        });
        (api.updateLecturePlaybackPosition as jest.Mock).mockResolvedValue({
            success: true,
            data: { videoId: 'v1', positionSeconds: 0 },
        });
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it('persists playback position on configured interval with delta threshold', async () => {
        let activeVideo: any = {
            lectureId: '1',
            currentTime: 10,
            lastKnownPosition: 10,
            isPlaying: true,
        };

        const { rerender } = renderHook<void, HookProps>(
            ({ video, focused }: HookProps) =>
                useLecturePlaybackPersistence({
                    lectureId: '1',
                    activeVideo: video,
                    isFocused: focused,
                    updatePlayState,
                    pauseVideo,
                    persistIntervalMs: 15000,
                    minPersistDeltaSeconds: 1.5,
                }),
            {
                initialProps: { video: activeVideo, focused: true },
            }
        );

        await act(async () => {
            jest.advanceTimersByTime(15000);
        });
        expect(api.updateLecturePlaybackPosition).toHaveBeenCalledWith('1', 10);

        activeVideo = { ...activeVideo, currentTime: 10.8 };
        rerender({ video: activeVideo, focused: true });
        await act(async () => {
            jest.advanceTimersByTime(15000);
        });
        expect(api.updateLecturePlaybackPosition).toHaveBeenCalledTimes(1);

        activeVideo = { ...activeVideo, currentTime: 12.5 };
        rerender({ video: activeVideo, focused: true });
        await act(async () => {
            jest.advanceTimersByTime(15000);
        });
        expect(api.updateLecturePlaybackPosition).toHaveBeenCalledTimes(2);
        expect(api.updateLecturePlaybackPosition).toHaveBeenLastCalledWith('1', 12.5);
    });
});
