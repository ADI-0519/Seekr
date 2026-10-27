import React from 'react';
import { View } from 'react-native';
import { fireEvent, render } from '@testing-library/react-native';

import { AuthField } from '../../src/components/auth/AuthField';

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        textPrimary: '#101010',
        textSecondary: '#808080',
        borderSubtle: '#d9d9d9',
        error: '#ef4444',
    }),
}));

jest.mock('lucide-react-native', () => {
    const React = require('react');
    const { Text } = require('react-native');
    return {
        Eye: (props: any) => React.createElement(Text, props, 'Eye'),
        EyeOff: (props: any) => React.createElement(Text, props, 'EyeOff'),
    };
});

describe('AuthField', () => {
    it('renders label and placeholder and forwards input changes', () => {
        const onChangeText = jest.fn();
        const { getByText, getByPlaceholderText } = render(
            <AuthField
                label="Email"
                value=""
                onChangeText={onChangeText}
                placeholder="Enter email"
                icon={<View testID="email-icon" />}
                autoComplete="email"
                keyboardType="email-address"
            />
        );

        expect(getByText('Email')).toBeTruthy();
        const input = getByPlaceholderText('Enter email');
        fireEvent.changeText(input, 'user@example.com');

        expect(onChangeText).toHaveBeenCalledWith('user@example.com');
    });

    it('shows error text when error is provided', () => {
        const { getByText } = render(
            <AuthField
                label="Password"
                value=""
                onChangeText={jest.fn()}
                placeholder="Enter password"
                icon={<View />}
                error="Password is required"
            />
        );

        expect(getByText('Password is required')).toBeTruthy();
    });

    it('uses secure text mode when password visibility is off', () => {
        const { getByPlaceholderText } = render(
            <AuthField
                label="Password"
                value="secret"
                onChangeText={jest.fn()}
                placeholder="Enter password"
                icon={<View />}
                secureTextEntry
                showPassword={false}
                onTogglePassword={jest.fn()}
            />
        );

        const input = getByPlaceholderText('Enter password') as any;
        expect(input.props.secureTextEntry).toBe(true);
    });

    it('disables secure text mode when password visibility is on and toggles via press', () => {
        const onTogglePassword = jest.fn();
        const { getByPlaceholderText, getByText } = render(
            <AuthField
                label="Password"
                value="secret"
                onChangeText={jest.fn()}
                placeholder="Enter password"
                icon={<View />}
                secureTextEntry
                showPassword
                onTogglePassword={onTogglePassword}
            />
        );

        const input = getByPlaceholderText('Enter password') as any;
        expect(input.props.secureTextEntry).toBe(false);

        fireEvent.press(getByText('EyeOff'));
        expect(onTogglePassword).toHaveBeenCalledTimes(1);
    });

    it('does not render toggle control when onTogglePassword is not provided', () => {
        const { queryByText } = render(
            <AuthField
                label="Password"
                value="secret"
                onChangeText={jest.fn()}
                placeholder="Enter password"
                icon={<View />}
                secureTextEntry
                showPassword={false}
            />
        );

        expect(queryByText('Eye')).toBeNull();
        expect(queryByText('EyeOff')).toBeNull();
    });
});
