import React from 'react';
import { render } from '@testing-library/react-native';

import { SidebarShell } from '../../src/components/navigation/SidebarShell';

const mockToggleSidebar = jest.fn();
let mockPathname = '/dashboard';

jest.mock('expo-router', () => ({
    useRouter: () => ({ push: jest.fn() }),
    usePathname: () => mockPathname,
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: (values: any) => values.sm,
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

jest.mock('../../src/store', () => ({
    useSidebarStore: () => ({
        isManuallyCollapsed: true,
        toggleSidebar: mockToggleSidebar,
    }),
}));

describe('SidebarShell', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockPathname = '/dashboard';
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.runOnlyPendingTimers();
        jest.useRealTimers();
    });

    it('renders mobile bottom nav items', () => {
        const { UNSAFE_getAllByProps } = render(<SidebarShell />);
        expect(UNSAFE_getAllByProps({ accessible: true }).length).toBeGreaterThanOrEqual(5);
    });
});
