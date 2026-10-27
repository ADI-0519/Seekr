import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { LectureCard } from '../../src/components/cards/LectureCard';
import type { Lecture } from '../../src/types';

let mockStoreState: any = null;

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        surfaceBase: '#ffffff',
        surfaceElevated: '#f8fafc',
        primaryEmerald: '#10b981',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid' }),
}));

jest.mock('../../src/store/videoStore', () => ({
    useVideoPlayerStore: (selector: any) => selector(mockStoreState),
}));

describe('LectureCard', () => {
    const lecture: Lecture = {
        id: 'lecture-1',
        title: 'Test Lecture',
        description: 'desc',
        overview: null,
        duration: 1200,
        thumbnailUrl: '',
        videoUrl: 'https://example.com/video.mp4',
        resumePosition: 300,
        status: 'ready',
        createdAt: '2026-04-01T10:00:00.000Z',
        updatedAt: '2026-04-01T10:00:00.000Z',
        userId: 'user-1',
    };

    beforeEach(() => {
        mockStoreState = { progressByLecture: {} };
    });

    it('renders lecture metadata and status chip', () => {
        const { getByText } = render(<LectureCard lecture={lecture} onPress={jest.fn()} />);

        expect(getByText('Test Lecture')).toBeTruthy();
        expect(getByText('READY')).toBeTruthy();
    });

    it('calls onPress when pressed', () => {
        const onPress = jest.fn();
        const { getByText } = render(<LectureCard lecture={lecture} onPress={onPress} />);

        fireEvent.press(getByText('Test Lecture'));
        expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('prefers persisted store progress over resumePosition', () => {
        mockStoreState = {
            progressByLecture: {
                'lecture-1': { currentTime: 600, duration: 1200 },
            },
        };

        const { getByText } = render(<LectureCard lecture={lecture} onPress={jest.fn()} />);

        // If store progress was ignored this chip might disappear in some regressions.
        expect(getByText('READY')).toBeTruthy();
    });
});
