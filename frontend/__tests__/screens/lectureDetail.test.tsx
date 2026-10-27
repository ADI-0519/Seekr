import React from 'react';
import { Alert } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import LectureDetailScreen from '../../app/(app)/lectures/[id]';
import { useDeleteLecture, useLecture, useTranscript, useTopics, useGenerateNotes, useSlides, useVideoPlayer, usePlayerShortcuts, useLectureQuery, useEntryAnimation } from '../../src/hooks';

const mockReplace = jest.fn();
const mockMutateAsync = jest.fn();

jest.mock('expo-router', () => ({
    useLocalSearchParams: () => ({ id: 'video-123' }),
    usePathname: () => '/lectures/video-123',
    useRouter: () => ({ replace: mockReplace, navigate: jest.fn(), push: jest.fn() })
}));

jest.mock('@react-navigation/native', () => ({
    useIsFocused: jest.fn().mockReturnValue(true)
}));

jest.mock('@react-native-async-storage/async-storage', () =>
    require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

jest.mock('../../src/hooks', () => ({
    useDeleteLecture: jest.fn(),
    useLecture: jest.fn(),
    useTranscript: jest.fn(),
    useTopics: jest.fn(),
    useGenerateNotes: jest.fn(),
    useSlides: jest.fn(),
    useVideoPlayer: jest.fn(),
    usePlayerShortcuts: jest.fn(),
    useLectureQuery: jest.fn().mockReturnValue({ mutate: jest.fn(), isPending: false }),
    useEntryAnimation: jest.fn().mockReturnValue({}),
}));

jest.mock('../../src/services', () => ({
    api: {
        exportNotesPDF: jest.fn(),
        getChatHistory: jest.fn().mockResolvedValue({ data: [] }),
        saveChatHistory: jest.fn().mockResolvedValue({}),
        getUserSettings: jest.fn().mockResolvedValue({ success: true, data: { pauseOnLeave: true } }),
        updateLecturePlaybackPosition: jest.fn().mockResolvedValue({ success: true, data: { videoId: 'video-123', positionSeconds: 0 } }),
    },
}));

jest.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({ invalidateQueries: jest.fn() }),
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
        primaryEmerald: '#10B981',
        textPrimary: '#1A2B2E',
        textSecondary: '#64748B',
        borderSubtle: '#E2E8F0',
        chipBgReady: '#F0FDF4',
        surfaceElevated: '#F8FAFC',
        surfaceBase: '#FFFFFF',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid', toggleMode: jest.fn(), setMode: jest.fn(), toggleCardStyle: jest.fn(), setCardStyle: jest.fn() }),
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: jest.fn().mockReturnValue(true)
}));

const mockLecture = {
    id: 'video-123',
    title: 'Intro to React Native',
    description: 'Learn to build cross-platform apps',
    overview: null,
    duration: 600,
    status: 'ready',
    videoUrl: 'http://test.com/vid.mp4',
    createdAt: '2023-01-01',
    updatedAt: '2023-01-01',
    thumbnailUrl: '',
    userId: 'user-1',
};

const mockVideoPlayer = {
    activeVideo: { lectureId: 'video-123', currentTime: 15, duration: 600, isPlaying: false, playbackRate: 1 },
    seekTo: jest.fn(),
    openMini: jest.fn(),
    updateTime: jest.fn(),
    updateDuration: jest.fn(),
    updatePlayState: jest.fn(),
    togglePlayPause: jest.fn(),
    setPlaybackRate: jest.fn(),
    claimEngine: jest.fn(),
    releaseEngine: jest.fn(),
    setVolume: jest.fn(),
};

describe('LectureDetailScreen', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockMutateAsync.mockResolvedValue(undefined);
        (useDeleteLecture as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
        (usePlayerShortcuts as jest.Mock).mockReturnValue(undefined);
        (useLectureQuery as jest.Mock).mockReturnValue({
            mutate: jest.fn(),
            isPending: false,
        });
        (useEntryAnimation as jest.Mock).mockReturnValue({});
        (useVideoPlayer as jest.Mock).mockReturnValue({
            ...mockVideoPlayer,
            loadSession: jest.fn(),
            activeVideo: { lectureId: 'video-123', currentTime: 15, duration: 600, isPlaying: false, playbackRate: 1 },
        });

        // Stubs for non-core data
        (useTranscript as jest.Mock).mockReturnValue({ data: { data: [] } });
        (useTopics as jest.Mock).mockReturnValue({ data: { data: [] } });
        (useSlides as jest.Mock).mockReturnValue({ data: { data: [] }, isLoading: false });
        (useGenerateNotes as jest.Mock).mockReturnValue({
            refetch: jest.fn(),
            isFetching: false,
            isError: false,
            data: null,
        });
    });

    it('renders loading state when lecture is not yet available', () => {
        (useLecture as jest.Mock).mockReturnValue({ data: null, isLoading: true });
        const { getByText } = render(<LectureDetailScreen />);
        expect(getByText(/Loading lecture.../i)).toBeTruthy();
    });

    it('renders the lecture content and delegates player binding', () => {
        const mockLecture = {
            id: 'video-123',
            title: 'Intro to React Native',
            description: 'Learn to build cross-platform apps',
            duration: 600,
            status: 'ready',
            videoUrl: 'http://test.com/vid.mp4',
            createdAt: '2023-01-01'
        };

        const mockOpenMini = jest.fn();
        const mockLoadSession = jest.fn();
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });
        (useVideoPlayer as jest.Mock).mockReturnValue({
            activeVideo: null,
            openMini: mockOpenMini,
            loadSession: mockLoadSession,
            seekTo: jest.fn(),
            claimEngine: jest.fn(),
            releaseEngine: jest.fn(),
            setVolume: jest.fn(),
        });

        const { getByText } = render(<LectureDetailScreen />);

        expect(getByText('Intro to React Native')).toBeTruthy();
        expect(getByText('Learn to build cross-platform apps')).toBeTruthy();
        expect(getByText('Transcript')).toBeTruthy();
        expect(getByText('Ask')).toBeTruthy();

        // Confirm loadSession was requested properly for lazy binding
        expect(mockLoadSession).toHaveBeenCalledWith(mockLecture, '/lectures/video-123', []);
    });

    it('shows Generate Notes button when lecture is ready and notes not yet generated', () => {
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });
        const { getByText } = render(<LectureDetailScreen />);
        expect(getByText('Generate Notes')).toBeTruthy();
    });

    it('calls generateNotes mutation when Generate Notes is pressed', () => {
        const mockRefetch = jest.fn();
        (useGenerateNotes as jest.Mock).mockReturnValue({
            refetch: mockRefetch,
            isFetching: false,
            isError: false,
            data: null,
        });
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });

        const { getByText } = render(<LectureDetailScreen />);
        fireEvent.press(getByText('Generate Notes'));
        expect(mockRefetch).toHaveBeenCalled();
    });

    it('shows spinner while notes are generating', () => {
        (useGenerateNotes as jest.Mock).mockReturnValue({
            refetch: jest.fn(),
            isFetching: true,
            isError: false,
            data: null,
        });
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });

        const { getByText } = render(<LectureDetailScreen />);
        expect(getByText('Generating notes...')).toBeTruthy();
    });

    it('renders generated notes with Export PDF button once notes are ready', () => {
        (useGenerateNotes as jest.Mock).mockReturnValue({
            refetch: jest.fn(),
            isFetching: false,
            isError: false,
            data: {
                data: {
                    videoId: 123,
                    notes: [
                        {
                            segmentId: 1,
                            title: 'Gradient Descent',
                            notesMarkdown: 'Overview of gradient descent.\n\n- **Learning rate**: Controls step size',
                            startTime: 0,
                            endTime: 120,
                        },
                    ],
                },
            },
        });
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });

        const { getByText } = render(<LectureDetailScreen />);
        expect(getByText('Gradient Descent')).toBeTruthy();
        expect(getByText('Export PDF')).toBeTruthy();
    });

    it('does not show Export PDF button before notes are generated', () => {
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });
        const { queryByText } = render(<LectureDetailScreen />);
        expect(queryByText('Export PDF')).toBeNull();
    });

    it('shows error message on generation failure', () => {
        (useGenerateNotes as jest.Mock).mockReturnValue({
            refetch: jest.fn(),
            isFetching: false,
            isError: true,
            data: null,
        });
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });

        const { getByText } = render(<LectureDetailScreen />);
        expect(getByText(/something went wrong/i)).toBeTruthy();
    });

    it('does not show Generate Notes for a lecture that is not ready', () => {
        const processingLecture = { ...mockLecture, status: 'processing' };
        (useLecture as jest.Mock).mockReturnValue({ data: { data: processingLecture }, isLoading: false });
        const { queryByText, getByText } = render(<LectureDetailScreen />);
        expect(getByText(/still processing/i)).toBeTruthy();
        expect(getByText(/Back to Dashboard/i)).toBeTruthy();
        expect(queryByText('Generate Notes')).toBeNull();
    });

    it('redirects to dashboard from processing guard CTA', () => {
        const processingLecture = { ...mockLecture, status: 'processing' };
        (useLecture as jest.Mock).mockReturnValue({ data: { data: processingLecture }, isLoading: false });
        const { getByText } = render(<LectureDetailScreen />);
        fireEvent.press(getByText('Back to Dashboard'));
        expect(mockReplace).toHaveBeenCalledWith('/(app)/dashboard');
    });

    it('does not expose delete controls in the detail view', () => {
        (useLecture as jest.Mock).mockReturnValue({ data: { data: mockLecture }, isLoading: false });

        const { queryByTestId } = render(<LectureDetailScreen />);

        expect(queryByTestId('delete-lecture-detail')).toBeNull();
        expect(mockMutateAsync).not.toHaveBeenCalled();
        expect(mockReplace).not.toHaveBeenCalled();
    });
});
