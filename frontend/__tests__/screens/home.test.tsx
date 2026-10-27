import React from 'react';
import { render } from '@testing-library/react-native';
import HomeScreen from '../../app/(app)/dashboard';
import { useLectures, useAuth, useVideoPlayer, useUploadStatusPolling, useCancelUpload } from '../../src/hooks';

// Mock dependencies
jest.mock('expo-router', () => ({
    useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({ invalidateQueries: jest.fn() }),
}));

jest.mock('../../src/hooks', () => ({
    useLectures: jest.fn(),
    useAuth: jest.fn(),
    useVideoPlayer: jest.fn(),
    useUploadStatusPolling: jest.fn(),
    useCancelUpload: jest.fn(),
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

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: jest.fn().mockReturnValue(true) // Assume desktop
}));

describe('HomeScreen Integration', () => {

    beforeEach(() => {
        jest.clearAllMocks();
        (useAuth as jest.Mock).mockReturnValue({ user: { displayName: 'Testing User' } });
        (useCancelUpload as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
        (useVideoPlayer as jest.Mock).mockReturnValue({ state: 'closed', activeVideo: null });
        (useUploadStatusPolling as jest.Mock).mockReturnValue({});
    });

    it('renders the friendly empty state when no lectures exist', () => {
        (useLectures as jest.Mock).mockReturnValue({ data: { items: [] }, isLoading: false });

        const { getByText, queryByText } = render(<HomeScreen />);

        // Top Shell uses user's name
        expect(getByText(/Testing User/i)).toBeTruthy();

        // Expect the empty state title
        expect(getByText(/Your library is empty/i)).toBeTruthy();

        // Ensure real sections aren't there
        expect(queryByText(/Continue Watching/i)).toBeNull();
        expect(queryByText(/Recent Lectures/i)).toBeNull();
    });

    it('renders lecture grids and activity rail when data exists', () => {
        (useLectures as jest.Mock).mockReturnValue({
            data: {
                items: [
                    { id: '1', title: 'Calculus 101', status: 'ready', updatedAt: new Date().toISOString() },
                    { id: '2', title: 'Processing Vid', status: 'processing', updatedAt: new Date().toISOString() },
                    { id: '3', title: 'Physics 202', status: 'ready', updatedAt: new Date(Date.now() - 10000).toISOString() } // explicitly older to be "Recent" rather than "Continue"
                ]
            },
            isLoading: false
        });

        const { getByText, getAllByText } = render(<HomeScreen />);

        // Verify standard sections appeared
        expect(getByText(/Continue Watching/i)).toBeTruthy(); // The newest 'Calculus 101' goes here
        expect(getByText(/Recent Lectures/i)).toBeTruthy(); // 'Physics 202' goes here

        // Verify Activity Board
        expect(getByText(/Processing Activity/i)).toBeTruthy();
        expect(getByText('Processing Vid')).toBeTruthy();

        // Verify Quick Stats
        expect(getByText('Ready Lectures')).toBeTruthy();
        expect(getAllByText('2')).toBeTruthy(); // There are 2 ready
        expect(getByText('Processing')).toBeTruthy();
        expect(getAllByText('1')).toBeTruthy(); // There is 1 processing
    });
});
