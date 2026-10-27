import React from 'react';
import { render } from '@testing-library/react-native';
import { useAuth as useAuthAlias } from '@/hooks';

import AppLayout from '../../app/(app)/_layout';
import AuthLayout from '../../app/(auth)/_layout';
import { useAuth } from '../../src/hooks/useAuth';
import { useBreakpointValue } from '../../src/hooks/useBreakpoint';
import { useSidebarEntryAnimation } from '../../src/hooks/useSidebarEntryAnimation';
import { useSidebarStore } from '../../src/store';

jest.mock('expo-router', () => {
    const React = require('react');
    const { Text } = require('react-native');

    return {
        Redirect: ({ href }: { href: string }) => React.createElement(Text, null, `REDIRECT:${href}`),
        Stack: () => React.createElement(Text, null, 'AUTH_STACK'),
        Slot: () => React.createElement(Text, null, 'APP_SLOT'),
        usePathname: () => '/dashboard',
    };
});

jest.mock('../../src/hooks/useAuth', () => ({
    useAuth: jest.fn(),
}));

jest.mock('@/hooks', () => ({
    useAuth: jest.fn(),
}));

jest.mock('../../src/hooks/useBreakpoint', () => ({
    useBreakpointValue: jest.fn(),
}));

jest.mock('../../src/store', () => ({
    useSidebarStore: jest.fn(),
}));

jest.mock('../../src/hooks/useSidebarEntryAnimation', () => ({
    useSidebarEntryAnimation: jest.fn(),
}));

jest.mock('../../src/components/navigation/SidebarShell', () => {
    const React = require('react');
    const { Text } = require('react-native');
    return {
        SidebarShell: () => React.createElement(Text, null, 'SIDEBAR'),
    };
});

jest.mock('../../src/components/processing/GlobalProcessingDock', () => {
    const React = require('react');
    const { Text } = require('react-native');
    return {
        GlobalProcessingDock: () => React.createElement(Text, null, 'PROCESSING_DOCK'),
    };
});

jest.mock('../../src/design/primitives/PageFrame', () => {
    const React = require('react');
    const { View } = require('react-native');
    return {
        PageFrame: ({ children }: { children: React.ReactNode }) => React.createElement(View, null, children),
    };
});

describe('auth bootstrap layouts', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (useSidebarStore as unknown as jest.Mock).mockReturnValue({ isManuallyCollapsed: false });
        (useSidebarEntryAnimation as unknown as jest.Mock).mockReturnValue({});
    });

    it('waits for auth bootstrap before redirecting from auth layout', () => {
        (useAuth as jest.Mock).mockReturnValue({ user: null, isInitializing: true });
        (useAuthAlias as unknown as jest.Mock).mockReturnValue({ user: null, isInitializing: true });

        const { getByTestId, queryByText } = render(<AuthLayout />);

        expect(getByTestId('auth-bootstrap-loading')).toBeTruthy();
        expect(queryByText('REDIRECT:/dashboard')).toBeNull();
        expect(queryByText('AUTH_STACK')).toBeNull();
    });

    it('redirects authenticated users away from auth layout once bootstrap completes', () => {
        (useAuth as jest.Mock).mockReturnValue({ user: { id: 'user-1' }, isInitializing: false });
        (useAuthAlias as unknown as jest.Mock).mockReturnValue({ user: { id: 'user-1' }, isInitializing: false });

        const { getByText } = render(<AuthLayout />);

        expect(getByText('REDIRECT:/dashboard')).toBeTruthy();
    });

    it('waits for auth bootstrap before redirecting from app layout', () => {
        (useAuth as jest.Mock).mockReturnValue({ user: null, isInitializing: true });
        (useAuthAlias as unknown as jest.Mock).mockReturnValue({ user: null, isInitializing: true });

        const { getByTestId, queryByText } = render(<AppLayout />);

        expect(getByTestId('auth-bootstrap-loading')).toBeTruthy();
        expect(queryByText('REDIRECT:/')).toBeNull();
    });

    it('redirects unauthenticated users to login once bootstrap completes', () => {
        (useAuth as jest.Mock).mockReturnValue({ user: null, isInitializing: false });
        (useAuthAlias as unknown as jest.Mock).mockReturnValue({ user: null, isInitializing: false });

        const { getByText } = render(<AppLayout />);

        expect(getByText('REDIRECT:/')).toBeTruthy();
    });

    it('renders the app shell for authenticated users', () => {
        (useAuth as jest.Mock).mockReturnValue({ user: { id: 'user-1' }, isInitializing: false });
        (useAuthAlias as unknown as jest.Mock).mockReturnValue({ user: { id: 'user-1' }, isInitializing: false });
        (useBreakpointValue as jest.Mock)
            .mockReturnValueOnce(280)
            .mockReturnValueOnce(false);

        const { getByText, queryByTestId } = render(<AppLayout />);

        expect(queryByTestId('auth-bootstrap-loading')).toBeNull();
        expect(getByText('APP_SLOT')).toBeTruthy();
        expect(getByText('SIDEBAR')).toBeTruthy();
    });
});
