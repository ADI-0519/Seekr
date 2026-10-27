import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import LoginScreen from '../../app/(auth)/login';
import { useAuth } from '../../src/hooks/useAuth';

const mockReplace = jest.fn();
const mockSignIn = jest.fn();
const mockSignInWithGoogle = jest.fn();

jest.mock('expo-router', () => ({
    Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    router: {
        replace: mockReplace,
    },
}));

jest.mock('../../src/hooks/useAuth', () => ({
    useAuth: jest.fn(),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10B981',
        primaryHover: '#059669',
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

jest.mock('../../src/constants', () => ({
    FEATURES: {
        enableMockAuth: false,
    },
    APP_CONFIG: {
        name: 'Seekr',
        tagline: 'Study smarter',
    },
}));

jest.mock('../../src/components/ui/Typography', () => {
    const React = require('react');
    const { Text } = require('react-native');

    return {
        Typography: ({ children }: { children: React.ReactNode }) => React.createElement(Text, null, children),
    };
});

describe('LoginScreen', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (useAuth as jest.Mock).mockReturnValue({
            signIn: mockSignIn,
            signInWithGoogle: mockSignInWithGoogle,
            isLoading: false,
        });
    });

    it('shows an inline credential mismatch error when sign in fails', async () => {
        mockSignIn.mockRejectedValueOnce(new Error('Firebase: Error (auth/invalid-credential).'));

        const { getByPlaceholderText, getByText } = render(<LoginScreen />);

        fireEvent.changeText(getByPlaceholderText('Enter your email'), 'user@example.com');
        fireEvent.changeText(getByPlaceholderText('Enter your password'), 'wrongpass');
        fireEvent.press(getByText('Sign In'));

        await waitFor(() => {
            expect(getByText('Email or password is incorrect.')).toBeTruthy();
        });

        expect(mockReplace).not.toHaveBeenCalled();
        expect(mockSignIn).toHaveBeenCalledWith('user@example.com', 'wrongpass');
    });
});
