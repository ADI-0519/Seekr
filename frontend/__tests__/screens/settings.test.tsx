import React from 'react';
import { Switch } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';

import SettingsScreen from '../../app/(app)/settings';

const mockPush = jest.fn();
const mockGetUserSettings = jest.fn();
const mockUpdateUserSettings = jest.fn();
const mockSetMode = jest.fn();
const mockSetCardStyle = jest.fn();
const mockSetBackgroundStyle = jest.fn();
const mockSetVideoAnimation = jest.fn();
const mockCycleVideoAnimation = jest.fn();

jest.mock('expo-router', () => ({
    useRouter: () => ({ push: mockPush }),
}));

jest.mock('../../src/services', () => ({
    api: {
        getUserSettings: (...args: unknown[]) => mockGetUserSettings(...args),
        updateUserSettings: (...args: unknown[]) => mockUpdateUserSettings(...args),
    },
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10b981',
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        surfaceElevated: '#f8fafc',
    }),
    useTheme: () => ({
        mode: 'light',
        isDark: false,
        cardStyle: 'solid',
        backgroundStyle: 'animated',
        videoAnimation: 3,
        setMode: mockSetMode,
        setCardStyle: mockSetCardStyle,
        setBackgroundStyle: mockSetBackgroundStyle,
        setVideoAnimation: mockSetVideoAnimation,
        cycleVideoAnimation: mockCycleVideoAnimation,
        toggleMode: jest.fn(),
        toggleCardStyle: jest.fn(),
    }),
}));

describe('SettingsScreen', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockGetUserSettings.mockResolvedValue({
            success: true,
            data: {
                themeMode: 'light',
                backgroundMode: 'animated',
                cardStyle: 'solid',
                videoAnimation: 3,
                autoplayNext: true,
                pauseOnLeave: true,
                volumeDefault: 1,
                mutedDefault: false,
                preferredLanguage: 'en',
                timezone: null,
            },
        });
        mockUpdateUserSettings.mockResolvedValue({ success: true });
    });

    it('loads settings on mount and applies them to theme', async () => {
        render(<SettingsScreen />);

        await waitFor(() => {
            expect(mockGetUserSettings).toHaveBeenCalledTimes(1);
            expect(mockSetMode).toHaveBeenCalledWith('light');
            expect(mockSetBackgroundStyle).toHaveBeenCalledWith('animated');
            expect(mockSetCardStyle).toHaveBeenCalledWith('solid');
            expect(mockSetVideoAnimation).toHaveBeenCalledWith(3);
        });
    });

    it('persists pause-on-leave toggle updates', async () => {
        const { UNSAFE_getAllByType } = render(<SettingsScreen />);

        await waitFor(() => {
            expect(mockGetUserSettings).toHaveBeenCalled();
        });

        const switches = UNSAFE_getAllByType(Switch);
        const pauseOnLeaveSwitch = switches[switches.length - 1];
        fireEvent(pauseOnLeaveSwitch, 'valueChange', false);

        await waitFor(() => {
            expect(mockUpdateUserSettings).toHaveBeenCalledWith(
                expect.objectContaining({ pauseOnLeave: false })
            );
        });
    });

    it('opens privacy policy route from account section', async () => {
        const { getByText } = render(<SettingsScreen />);

        await waitFor(() => {
            expect(mockGetUserSettings).toHaveBeenCalled();
        });

        fireEvent.press(getByText('Privacy Policy'));
        expect(mockPush).toHaveBeenCalledWith('/info/privacy-policy');
    });
});
