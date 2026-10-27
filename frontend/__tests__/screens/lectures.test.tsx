import React from 'react';
import { Alert } from 'react-native';
import { act, fireEvent, render } from '@testing-library/react-native';
import LecturesScreen from '../../app/(app)/lectures/index';
import { useDeleteLecture, useLectures } from '../../src/hooks';

const mockPush = jest.fn();
const mockMutateAsync = jest.fn();

jest.mock('expo-router', () => ({
    useRouter: () => ({ push: mockPush }),
}));

jest.mock('../../src/hooks', () => ({
    useLectures: jest.fn(),
    useDeleteLecture: jest.fn(),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#00FF00',
        textPrimary: '#FFFFFF',
        textSecondary: '#AAAAAA',
        borderSubtle: '#333333',
        chipBgReady: '#111111',
        surfaceBase: '#000000',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid', toggleMode: jest.fn(), setMode: jest.fn(), toggleCardStyle: jest.fn(), setCardStyle: jest.fn() }),
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: jest.fn().mockReturnValue(true)
}));

describe('LecturesScreen Integration', () => {
    const lectureItems = [
        {
            id: '1',
            title: 'Calculus 101',
            description: 'Advanced Math',
            duration: 600,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            status: 'ready',
            thumbnailUrl: '',
            videoUrl: '',
            userId: 'user-1',
        },
        {
            id: '2',
            title: 'Physics 202',
            description: 'Intro to Quantum',
            duration: 420,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            status: 'ready',
            thumbnailUrl: '',
            videoUrl: '',
            userId: 'user-1',
        },
    ];

    beforeEach(() => {
        jest.clearAllMocks();
        mockMutateAsync.mockResolvedValue(undefined);
        (useDeleteLecture as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });
    });

    it('renders empty state when no lectures exist', () => {
        (useLectures as jest.Mock).mockReturnValue({ data: { items: [] }, isLoading: false });

        const { getByText, queryByText } = render(<LecturesScreen />);

        expect(getByText(/Your library is empty/i)).toBeTruthy();
        expect(queryByText(/Upload your first lecture/i)).toBeTruthy();
    });

    it('renders lecture grid when data exists', () => {
        (useLectures as jest.Mock).mockReturnValue({
            data: { items: lectureItems },
            isLoading: false,
        });

        const { getByText, queryByText } = render(<LecturesScreen />);

        expect(getByText('Calculus 101')).toBeTruthy();
        expect(getByText('Physics 202')).toBeTruthy();
        expect(queryByText(/Your library is empty/i)).toBeNull();
    });

    it('filters lectures based on search query', () => {
        (useLectures as jest.Mock).mockReturnValue({
            data: { items: lectureItems },
            isLoading: false,
        });

        const { getByText, queryByText, getByPlaceholderText } = render(<LecturesScreen />);

        expect(getByText('Calculus 101')).toBeTruthy();
        expect(getByText('Physics 202')).toBeTruthy();

        const searchInput = getByPlaceholderText(/Search lectures/i);
        fireEvent.changeText(searchInput, 'Quantum');

        expect(getByText('Physics 202')).toBeTruthy();
        expect(queryByText('Calculus 101')).toBeNull();
    });

    it('shows no results found message when filter misses all', () => {
        (useLectures as jest.Mock).mockReturnValue({
            data: { items: [lectureItems[0]] },
            isLoading: false,
        });

        const { getByText, getByPlaceholderText, queryByText } = render(<LecturesScreen />);

        const searchInput = getByPlaceholderText(/Search lectures/i);
        fireEvent.changeText(searchInput, 'AlienTech');

        expect(queryByText('Calculus 101')).toBeNull();
        expect(getByText(/No results for "AlienTech"/i)).toBeTruthy();
        expect(getByText(/Try adjusting your search terms/i)).toBeTruthy();
    });

    it('confirms and deletes a lecture from the library grid', async () => {
        const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
        (useLectures as jest.Mock).mockReturnValue({
            data: { items: [lectureItems[0]] },
            isLoading: false,
        });

        const { getByTestId } = render(<LecturesScreen />);

        fireEvent.press(getByTestId('delete-lecture-1'));

        expect(alertSpy).toHaveBeenCalled();
        const buttons = alertSpy.mock.calls[0][2] as Array<{ text: string; onPress?: () => void }>;
        const deleteButton = buttons.find(button => button.text === 'Delete');
        expect(deleteButton).toBeTruthy();

        await act(async () => {
            deleteButton?.onPress?.();
        });

        expect(mockMutateAsync).toHaveBeenCalledWith('1');
    });
});
