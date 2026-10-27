import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import SearchScreen from '../../app/(app)/search';
import { useLectures } from '../../src/hooks';
import { api } from '../../src/services';

// Mock dependencies
jest.mock('expo-router', () => ({
    useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('../../src/hooks', () => ({
    useLectures: jest.fn(),
}));

jest.mock('../../src/services', () => ({
    api: {
        search: jest.fn(),
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

describe('SearchScreen Integration', () => {

    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();

        // Setup base lectures
        (useLectures as jest.Mock).mockReturnValue({
            data: {
                items: [
                    { id: '1', title: 'Calculus 101', status: 'ready' },
                    { id: '2', title: 'Processing', status: 'processing' } // Should be skipped in search
                ]
            }
        });
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it('renders initial state prompting discovery', () => {
        const { getByText } = render(<SearchScreen />);
        expect(getByText(/Find anything in your library/i)).toBeTruthy();
    });

    it('waits for debounce, fires API, and renders results', async () => {
        // Mock the search api to return matching data for Calculus 101
        (api.search as jest.Mock).mockResolvedValueOnce({
            success: true,
            data: [
                { id: 's1', lectureId: '1', text: 'Quantum tunneling is fun', timestamp: 120.5, relevanceScore: 0.99, context: 'Intro' }
            ]
        });

        const { getByPlaceholderText, getByText, queryByText } = render(<SearchScreen />);

        // Type a valid query
        const input = getByPlaceholderText(/Search transcripts/i);
        fireEvent.changeText(input, 'Quantum');

        // Immediately after typing, should NOT have results or even "Searching" yet (debounce active)
        expect(queryByText(/Quantum tunneling is fun/i)).toBeNull();

        // Fast forward the 400ms debounce
        act(() => {
            jest.advanceTimersByTime(400);
        });

        // The component uses an async performSearch.
        // We wait for the DOM to update with the results.
        await waitFor(() => {
            expect(getByText(/"Quantum tunneling is fun"/i)).toBeTruthy();
        });

        // Validate that it injected the lecture name dynamically
        expect(getByText(/Calculus 101/i)).toBeTruthy();

        // Validate formatted percentage label
        expect(getByText(/% match/i)).toBeTruthy();
    });

    it('renders no results backend state gracefully', async () => {
        (api.search as jest.Mock).mockResolvedValueOnce({
            success: true,
            data: [] // Empty results
        });

        const { getByPlaceholderText, getByText } = render(<SearchScreen />);

        fireEvent.changeText(getByPlaceholderText(/Search transcripts/i), 'AlienTech');

        act(() => {
            jest.advanceTimersByTime(400);
        });

        await waitFor(() => {
            expect(getByText(/No results found/i)).toBeTruthy();
            expect(getByText(/Try different keywords/i)).toBeTruthy();
        });
    });

    it('gracefully handles backend errors', async () => {
        (api.search as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

        const { getByPlaceholderText, getByText } = render(<SearchScreen />);

        fireEvent.changeText(getByPlaceholderText(/Search transcripts/i), 'FailMe');

        act(() => {
            jest.advanceTimersByTime(400);
        });

        // Should fallback to empty state rather than crashing,
        // since the error is caught inside the map loop.
        await waitFor(() => {
            expect(getByText(/No results found/i)).toBeTruthy();
        });
    });
});
