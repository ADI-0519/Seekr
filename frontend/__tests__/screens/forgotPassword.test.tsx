import React from 'react';
import { Alert } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import ForgotPasswordScreen from '../../app/(auth)/forgot-password';
import { useAuth } from '../../src/hooks/useAuth';

const mockBack = jest.fn();
const mockResetPassword = jest.fn();

jest.mock('expo-router', () => ({
    router: {
        back: mockBack,
    },
}));

jest.mock('../../src/hooks/useAuth', () => ({
    useAuth: jest.fn(),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10B981',
        textPrimary: '#FFFFFF',
        textSecondary: '#94A3B8',
        borderSubtle: '#334155',
        error: '#EF4444',
        surfaceBase: '#020617',
        surfaceElevated: '#0F172A',
        chipBgReady: '#0B1220',
    }),
    useTheme: () => ({
        mode: 'dark',
        isDark: true,
        cardStyle: 'solid',
        toggleMode: jest.fn(),
        setMode: jest.fn(),
        toggleCardStyle: jest.fn(),
        setCardStyle: jest.fn(),
    }),
}));

jest.mock('../../src/components/ui/Typography', () => {
    const React = require('react');
    const { Text } = require('react-native');
    return {
        Typography: ({ children }: { children: React.ReactNode }) => React.createElement(Text, null, children),
    };
});

describe('ForgotPasswordScreen', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        jest.spyOn(Alert, 'alert').mockImplementation(() => {});
        (useAuth as jest.Mock).mockReturnValue({
            resetPassword: mockResetPassword,
            isLoading: false,
        });
    });

    afterEach(() => {
        (Alert.alert as jest.Mock).mockRestore?.();
    });

    it('validates empty email and invalid email format', async () => {
        const { getByText, getByPlaceholderText } = render(<ForgotPasswordScreen />);

        fireEvent.press(getByText('Send Reset Link'));
        await waitFor(() => {
            expect(getByText('Email is required')).toBeTruthy();
        });

        fireEvent.changeText(getByPlaceholderText('Enter your email'), 'bad-email');
        fireEvent.press(getByText('Send Reset Link'));
        await waitFor(() => {
            expect(getByText('Please enter a valid email')).toBeTruthy();
        });
    });

    it('shows success state when reset email is sent', async () => {
        mockResetPassword.mockResolvedValueOnce(undefined);
        const { getByPlaceholderText, getByText } = render(<ForgotPasswordScreen />);

        fireEvent.changeText(getByPlaceholderText('Enter your email'), 'reset@example.com');
        fireEvent.press(getByText('Send Reset Link'));

        await waitFor(() => {
            expect(mockResetPassword).toHaveBeenCalledWith('reset@example.com');
            expect(getByText('Check your email')).toBeTruthy();
        });
    });

    it('shows alert when reset fails', async () => {
        mockResetPassword.mockRejectedValueOnce(new Error('Reset failed'));
        const { getByPlaceholderText, getByText } = render(<ForgotPasswordScreen />);

        fireEvent.changeText(getByPlaceholderText('Enter your email'), 'reset@example.com');
        fireEvent.press(getByText('Send Reset Link'));

        await waitFor(() => {
            expect(Alert.alert).toHaveBeenCalledWith('Error', 'Reset failed');
        });
    });
});
