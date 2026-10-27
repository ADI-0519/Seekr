import React from 'react';
import { Alert } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';

import ProfileScreen from '../../app/(app)/profile';

const mockSignOut = jest.fn();
const mockReplace = jest.fn();

jest.mock('expo-router', () => ({
    router: {
        replace: (...args: unknown[]) => mockReplace(...args),
    },
}));

jest.mock('../../src/hooks', () => ({
    useAuth: () => ({
        user: {
            displayName: 'Test User',
            email: 'test@seekr.app',
            createdAt: '2026-01-01T00:00:00.000Z',
        },
        signOut: mockSignOut,
    }),
    useProfileSummary: () => ({
        isLoading: false,
        isError: false,
        data: {
            data: {
                lectureCount: 4,
                readyLectureCount: 3,
                totalDurationSeconds: 5400,
                recentUploads: [],
            },
        },
    }),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10b981',
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        chipBgReady: '#ecfdf5',
        chipBgFailed: '#fee2e2',
        surfaceBase: '#ffffff',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid' }),
}));

describe('ProfileScreen', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockSignOut.mockResolvedValue(undefined);
    });

    it('renders key profile information and stats', () => {
        const { getByText } = render(<ProfileScreen />);

        expect(getByText('Profile')).toBeTruthy();
        expect(getByText('Test User')).toBeTruthy();
        expect(getByText('test@seekr.app')).toBeTruthy();
        expect(getByText('Sign Out')).toBeTruthy();
        expect(getByText('Lectures')).toBeTruthy();
        expect(getByText('Ready')).toBeTruthy();
        expect(getByText('Content Time')).toBeTruthy();
    });

    it('confirms and signs out via native alert flow', async () => {
        const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
        const { getByText } = render(<ProfileScreen />);

        fireEvent.press(getByText('Sign Out'));
        expect(alertSpy).toHaveBeenCalled();

        const buttons = alertSpy.mock.calls[0][2] as Array<{ text: string; onPress?: () => void }>;
        const confirm = buttons.find((button) => button.text === 'Sign Out');
        expect(confirm).toBeTruthy();

        await act(async () => {
            confirm?.onPress?.();
        });

        await waitFor(() => {
            expect(mockSignOut).toHaveBeenCalledTimes(1);
            expect(mockReplace).toHaveBeenCalledWith('/');
        });
    });
});
