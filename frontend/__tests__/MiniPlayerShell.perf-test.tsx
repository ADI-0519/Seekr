import React from 'react';
import { measureRenders } from 'reassure';
import { MiniPlayerShell } from '../src/components/player/MiniPlayerShell';
import { ThemeProvider } from '../src/theme/ThemeProvider';

jest.mock('expo-router', () => ({
    useRouter: () => ({
        push: jest.fn(),
    }),
    usePathname: () => '/',
}));

const mockStore = {
    selectedLectureId: '1',
    isMiniPlayerReady: true,
    isExpanded: false,
    isFullscreen: false,
    engine: {
        pause: jest.fn(),
        play: jest.fn(),
        seek: jest.fn(),
        destroy: jest.fn(),
    },
    isPlaying: true,
    durationMs: 120000,
    currentPositionMs: 50000,
    setExpanded: jest.fn(),
    setFullscreen: jest.fn(),
    clearLecture: jest.fn(),
};

jest.mock('../src/store/videoStore', () => ({
    useVideoStore: (selector: any) => selector(mockStore),
    useVideoPlayerStore: () => mockStore,
}));

jest.mock('../src/hooks', () => ({
    useLectures: () => ({
        data: {
            items: [
                { id: '1', title: 'Test Lecture', status: 'ready', updatedAt: new Date().toISOString() },
            ],
        },
    }),
    useVideoPlayer: () => ({}),
}));

const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>
        {children}
    </ThemeProvider>
);

describe('MiniPlayerShell Performance', () => {
    it('renders smoothly', async () => {
        await measureRenders(<MiniPlayerShell />, { wrapper: Wrapper });
    });
});
