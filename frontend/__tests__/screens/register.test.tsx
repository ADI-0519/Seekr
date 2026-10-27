import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import RegisterScreen from '../../app/(auth)/register';
import { useAuth } from '../../src/hooks/useAuth';

const mockReplace = jest.fn();
const mockBack = jest.fn();
const mockSignUp = jest.fn();
const mockSignUpWithGoogle = jest.fn();

jest.mock('expo-router', () => ({
    Link: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    router: {
        replace: mockReplace,
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

jest.mock('../../src/components/ui/PrimaryButton', () => {
    const React = require('react');
    const { Pressable, Text } = require('react-native');
    return {
        PrimaryButton: ({ label, onPress, disabled }: { label: string; onPress: () => void; disabled?: boolean }) => (
            <Pressable onPress={onPress} disabled={disabled}>
                <Text>{label}</Text>
            </Pressable>
        ),
    };
});

describe('RegisterScreen', () => {
    const pressForLabel = (label: string, getAllByText: (text: string) => any[]) => {
        const nodes = getAllByText(label);
        let current = nodes[nodes.length - 1];
        while (current && typeof current.props?.onPress !== 'function') {
            current = current.parent;
        }
        if (!current) {
            throw new Error(`Could not find pressable for "${label}"`);
        }
        fireEvent.press(current);
    };

    beforeEach(() => {
        jest.clearAllMocks();
        (useAuth as jest.Mock).mockReturnValue({
            signUp: mockSignUp,
            signUpWithGoogle: mockSignUpWithGoogle,
            isLoading: false,
        });
    });

    it('shows validation errors when required fields are missing', async () => {
        const { getByText, getAllByText } = render(<RegisterScreen />);
        pressForLabel('Create Account', getAllByText);

        await waitFor(() => {
            expect(getByText('Name is required')).toBeTruthy();
            expect(getByText('Email is required')).toBeTruthy();
            expect(getByText('Password is required')).toBeTruthy();
        });
        expect(mockSignUp).not.toHaveBeenCalled();
    });

    it('submits sign up and redirects on success', async () => {
        mockSignUp.mockResolvedValueOnce(undefined);
        const { getByPlaceholderText, getAllByText } = render(<RegisterScreen />);

        fireEvent.changeText(getByPlaceholderText('Enter your name'), 'Adi');
        fireEvent.changeText(getByPlaceholderText('Enter your email'), 'adi@example.com');
        fireEvent.changeText(getByPlaceholderText('Create a password'), 'password123');
        fireEvent.changeText(getByPlaceholderText('Confirm your password'), 'password123');
        pressForLabel('Create Account', getAllByText);

        await waitFor(() => {
            expect(mockSignUp).toHaveBeenCalledWith('adi@example.com', 'password123', 'Adi');
        });
    });

    it('runs Google sign-up flow', async () => {
        mockSignUpWithGoogle.mockResolvedValueOnce(undefined);
        const { getAllByText } = render(<RegisterScreen />);
        pressForLabel('Continue with Google', getAllByText);

        await waitFor(() => {
            expect(mockSignUpWithGoogle).toHaveBeenCalled();
        });
    });
});
