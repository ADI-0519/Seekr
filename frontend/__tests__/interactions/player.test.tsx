import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import LectureDetailScreen from '../../app/(app)/lectures/[id]';
import HomeScreen from '../../app/(app)/dashboard';
import { useLecture, useTranscript, useTopics, useGenerateNotes, useSlides, useVideoPlayer, useLectures, useAuth, useUploadStatusPolling, useLectureQuery, useEntryAnimation } from '../../src/hooks';
import { useRouter } from 'expo-router';

jest.mock('expo-router', () => ({
    useRouter: jest.fn(),
    useLocalSearchParams: () => ({ id: '123' }),
    usePathname: () => '/lectures/123'
}));

jest.mock('@react-navigation/native', () => ({
    useIsFocused: jest.fn().mockReturnValue(true)
}));

jest.mock('@react-native-async-storage/async-storage', () =>
    require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

jest.mock('../../src/hooks', () => ({
    useLecture: jest.fn(),
    useTranscript: jest.fn(),
    useTopics: jest.fn(),
    useGenerateNotes: jest.fn(),
    useSlides: jest.fn(),
    useVideoPlayer: jest.fn(),
    usePlayerShortcuts: jest.fn(),
    useLectures: jest.fn(),
    useAuth: jest.fn(),
    useUploadStatusPolling: jest.fn(),
    useCancelUpload: jest.fn().mockReturnValue({ mutateAsync: jest.fn() }),
    useDeleteLecture: jest.fn().mockReturnValue({ mutateAsync: jest.fn() }),
    useLectureQuery: jest.fn().mockReturnValue({ mutate: jest.fn(), isPending: false }),
    useEntryAnimation: jest.fn(),
}));

jest.mock('../../src/services', () => ({
    api: {
        exportNotesPDF: jest.fn(),
        getChatHistory: jest.fn().mockResolvedValue({ data: [] }),
        saveChatHistory: jest.fn().mockResolvedValue({}),
        getUserSettings: jest.fn().mockResolvedValue({ data: { pauseOnLeave: true } }),
    },
}));

jest.mock('expo-av', () => ({
    Video: () => <></>,
    ResizeMode: { CONTAIN: 'contain' }
}));

jest.mock('../../src/player/playerEngine', () => ({
    playerEngine: {
        getRef: () => ({ current: null }),
        onStatusUpdate: jest.fn()
    }
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#00FF00',
        textPrimary: '#FFFFFF',
        textSecondary: '#AAAAAA',
        borderSubtle: '#333333',
        chipBgReady: '#111111',
        surfaceElevated: '#222222',
        surfaceBase: '#000000',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid', toggleMode: jest.fn(), setMode: jest.fn(), toggleCardStyle: jest.fn(), setCardStyle: jest.fn() }),
}));

jest.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({ invalidateQueries: jest.fn() }),
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: jest.fn().mockReturnValue(true) // Assumes desktop layout width
}));

describe('Interactions Workflows', () => {

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('clicking a lecture card pushes the router to its detail screen', () => {
        const mockPush = jest.fn();
        (useRouter as jest.Mock).mockReturnValue({ push: mockPush });

        (useAuth as jest.Mock).mockReturnValue({ user: { displayName: 'Testing User' } });
        (useVideoPlayer as jest.Mock).mockReturnValue({ state: 'closed', activeVideo: null, claimEngine: jest.fn(), releaseEngine: jest.fn(), setVolume: jest.fn() });
        (useLectures as jest.Mock).mockReturnValue({
            data: {
                items: [
                    { id: '1', title: 'Calculus 101', status: 'ready', updatedAt: new Date().toISOString() },
                ]
            },
            isLoading: false
        });

        const { getByText } = render(<HomeScreen />);

        const cardElement = getByText('Calculus 101');
        fireEvent.press(cardElement);

        expect(mockPush).toHaveBeenCalledWith('/lectures/1');
    });

    it('clicking a transcript segment triggers playerEngine seekTo', () => {
        const mockSeekTo = jest.fn();
        (useVideoPlayer as jest.Mock).mockReturnValue({
            activeVideo: null,
            loadSession: jest.fn(),
            seekTo: mockSeekTo,
            claimEngine: jest.fn(),
            releaseEngine: jest.fn(),
            setVolume: jest.fn(),
        });

        (useLecture as jest.Mock).mockReturnValue({
            data: { data: { id: '123', title: 'React', status: 'ready', videoUrl: 'http://test.com', duration: 100 } },
            isLoading: false
        });

        (useTranscript as jest.Mock).mockReturnValue({
            data: {
                data: [
                    { id: 't1', startTime: 10.5, endTime: 15.0, text: 'Click me to jump.' }
                ]
            }
        });

        (useTopics as jest.Mock).mockReturnValue({ data: [] });
        (useGenerateNotes as jest.Mock).mockReturnValue({ data: null, isFetching: false });
        (useSlides as jest.Mock).mockReturnValue({ data: { data: [] }, isLoading: false });

        const { getByText } = render(<LectureDetailScreen />);

        const transcriptElement = getByText('Click me to jump.');
        fireEvent.press(transcriptElement);

        expect(mockSeekTo).toHaveBeenCalledWith(10.5); // Verify exact time boundary
    });
});
