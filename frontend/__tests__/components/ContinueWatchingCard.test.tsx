import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { ContinueWatchingCard } from '../../src/components/cards/ContinueWatchingCard';
import type { Lecture } from '../../src/types';

let mockStoreState: any = null;

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        surfaceBase: '#ffffff',
        primaryEmerald: '#10b981',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid' }),
}));

jest.mock('../../src/store/videoStore', () => ({
    useVideoPlayerStore: (selector: any) => selector(mockStoreState),
}));

describe('ContinueWatchingCard', () => {
    const lecture: Lecture = {
        id: 'lecture-2',
        title: 'Linear Algebra',
        description: '',
        overview: null,
        duration: 600,
        thumbnailUrl: 'https://example.com/thumb.jpg',
        videoUrl: 'https://example.com/video.mp4',
        resumePosition: 120,
        status: 'ready',
        createdAt: '2026-04-01T10:00:00.000Z',
        updatedAt: '2026-04-01T10:00:00.000Z',
        userId: 'user-1',
    };

    beforeEach(() => {
        mockStoreState = { progressByLecture: {} };
    });

    it('shows fallback description when overview and description are missing', () => {
        const { getByText } = render(<ContinueWatchingCard lecture={lecture} onPress={jest.fn()} />);

        expect(getByText('Open lecture to generate notes and overview.')).toBeTruthy();
        expect(getByText('20% Completed')).toBeTruthy();
        expect(getByText('8 mins left')).toBeTruthy();
    });

    it('uses live store progress when present', () => {
        mockStoreState = {
            progressByLecture: {
                'lecture-2': { currentTime: 300, duration: 600 },
            },
        };

        const { getByText } = render(<ContinueWatchingCard lecture={lecture} onPress={jest.fn()} />);

        expect(getByText('50% Completed')).toBeTruthy();
        expect(getByText('5 mins left')).toBeTruthy();
    });

    it('calls onPress when pressed', () => {
        const onPress = jest.fn();
        const { getByText } = render(<ContinueWatchingCard lecture={lecture} onPress={onPress} />);

        fireEvent.press(getByText('Linear Algebra'));
        expect(onPress).toHaveBeenCalledTimes(1);
    });
});
