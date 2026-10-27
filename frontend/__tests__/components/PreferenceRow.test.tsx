import React from 'react';
import { Text } from 'react-native';
import { fireEvent, render } from '@testing-library/react-native';

import { PreferenceRow } from '../../src/components/settings/PreferenceRow';

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        textPrimary: '#111111',
        textSecondary: '#6b7280',
        surfaceElevated: '#f5f5f5',
    }),
}));

function DummyIcon({ color, size }: { color?: string; size?: number }) {
    return <Text>{`icon:${color ?? 'none'}:${size ?? 'none'}`}</Text>;
}

describe('PreferenceRow', () => {
    it('renders title and subtitle', () => {
        const { getByText } = render(
            <PreferenceRow
                icon={DummyIcon}
                title="Pause when leaving lecture"
                subtitle="Pause playback when navigating away"
            />
        );

        expect(getByText('Pause when leaving lecture')).toBeTruthy();
        expect(getByText('Pause playback when navigating away')).toBeTruthy();
    });

    it('calls onPress when pressed', () => {
        const onPress = jest.fn();
        const { getByText } = render(
            <PreferenceRow
                icon={DummyIcon}
                title="Autoplay next"
                onPress={onPress}
            />
        );

        fireEvent.press(getByText('Autoplay next'));
        expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('renders trailing content when provided', () => {
        const { getByText } = render(
            <PreferenceRow
                icon={DummyIcon}
                title="Card style"
                trailing={<Text>TrailingControl</Text>}
            />
        );

        expect(getByText('TrailingControl')).toBeTruthy();
    });

    it('uses provided icon color and size', () => {
        const { getByText } = render(
            <PreferenceRow
                icon={DummyIcon}
                title="Theme"
                iconColor="#22c55e"
                iconSize={28}
            />
        );

        expect(getByText('icon:#22c55e:28')).toBeTruthy();
    });
});
