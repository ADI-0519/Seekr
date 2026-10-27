import React from 'react';
import { render } from '@testing-library/react-native';

import { MiniPlayerShell } from '../../src/components/player/MiniPlayerShell';

const mockPush = jest.fn();
const mockExpandPlayer = jest.fn();
const mockClosePlayer = jest.fn();

let mockPathname = '/dashboard';
let mockStoreState: any = null;

jest.mock('expo-router', () => ({
    useRouter: () => ({ push: mockPush }),
    usePathname: () => mockPathname,
}));

jest.mock('../../src/store/videoStore', () => ({
    useVideoPlayerStore: () => mockStoreState,
    getRawCurrentTime: () => mockStoreState?.activeVideo?.currentTime ?? 0,
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: (values: any) => values.md ?? values.sm,
}));

jest.mock('../../src/hooks/useEntryAnimation', () => ({
    useEntryAnimation: () => ({}),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10b981',
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        surfaceBase: '#ffffff',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid' }),
}));

describe('MiniPlayerShell', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockPathname = '/dashboard';
        mockStoreState = {
            state: 'mini',
            activeVideo: {
                lectureId: '123',
                title: 'Mini Player Lecture',
                thumbnailUrl: '',
                duration: 100,
                currentTime: 25,
                sourceRoute: '/lectures/123',
                isPlaying: false,
            },
            togglePlayPause: jest.fn(),
            expandPlayer: mockExpandPlayer,
            closePlayer: mockClosePlayer,
        };
    });

    it('renders when there is an active mini-player session off-owner route', () => {
        const { getByText } = render(<MiniPlayerShell />);
        expect(getByText('Mini Player Lecture')).toBeTruthy();
    });

    it('hides when user is already on the owning lecture route', () => {
        mockPathname = '/lectures/123';
        const { queryByText } = render(<MiniPlayerShell />);
        expect(queryByText('Mini Player Lecture')).toBeNull();
    });

});
