import React from 'react';
import { render } from '@testing-library/react-native';

import { GlobalProcessingDock } from '../../src/components/processing/GlobalProcessingDock';

let mockPathname = '/search';
let mockMobileMode = true;

const mockHydrate = jest.fn().mockResolvedValue(undefined);
const mockPrune = jest.fn();
const mockSetOverride = jest.fn();
const mockInvalidateQueries = jest.fn();

jest.mock('expo-router', () => ({
    usePathname: () => mockPathname,
    useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mockInvalidateQueries }),
}));

jest.mock('../../src/hooks', () => ({
    useLectures: () => ({
        data: {
            items: [
                {
                    id: 'p1',
                    title: 'Processing Lecture',
                    status: 'processing',
                    updatedAt: new Date().toISOString(),
                    createdAt: new Date().toISOString(),
                },
                {
                    id: 'r1',
                    title: 'Ready Lecture',
                    status: 'ready',
                    updatedAt: new Date().toISOString(),
                    createdAt: new Date().toISOString(),
                },
            ],
        },
    }),
    useUploadStatusPolling: () => ({
        status: {
            lectureId: 'p1',
            state: 'running',
            stage: 'transcribing',
            progress: 45,
            errorMessage: null,
            transcriptionStage: null,
            slidesStage: null,
        },
    }),
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: (values: any) => {
        if (Object.prototype.hasOwnProperty.call(values, 'sm') && Object.prototype.hasOwnProperty.call(values, 'md')) {
            return mockMobileMode ? values.sm : values.md;
        }
        return values.md ?? values.sm;
    },
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#10b981',
        textPrimary: '#0f172a',
        textSecondary: '#64748b',
        borderSubtle: '#dbe3ea',
        surfaceElevated: '#ffffff',
        chipBgProcessing: '#ecfeff',
        chipBgFailed: '#fee2e2',
        chipBgReady: '#ecfdf5',
        info: '#0ea5e9',
        error: '#ef4444',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid' }),
}));

jest.mock('../../src/store', () => ({
    useLectureStatusStore: () => ({
        overrides: {},
        hydrated: true,
        hydrate: mockHydrate,
        setOverride: mockSetOverride,
        pruneOverrides: mockPrune,
    }),
    applyEffectiveLectureStatus: (lecture: any) => lecture,
}));

describe('GlobalProcessingDock', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockPathname = '/search';
        mockMobileMode = true;
    });

    it('renders status summary outside dashboard desktop route', () => {
        const { getByText } = render(<GlobalProcessingDock />);
        expect(getByText('Lecture Updates')).toBeTruthy();
        expect(getByText(/processing/i)).toBeTruthy();
    });

    it('does not render on dashboard desktop layout', () => {
        mockPathname = '/dashboard';
        mockMobileMode = false;
        const { queryByText } = render(<GlobalProcessingDock />);
        expect(queryByText('Lecture Updates')).toBeNull();
    });
});
