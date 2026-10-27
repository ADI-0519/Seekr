import React from 'react';
import { measureRenders } from 'reassure';
import HomeScreen from '../app/(app)/dashboard';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock dependencies
jest.mock('expo-router', () => ({
    useRouter: () => ({
        push: jest.fn(),
        replace: jest.fn(),
        back: jest.fn(),
    }),
}));

jest.mock('../src/services/auth', () => ({
    authService: {},
}));

jest.mock('../src/hooks', () => ({
    useAuth: () => ({ user: { displayName: 'Seekr Tester' } }),
    useLectures: () => ({
        data: {
            items: [
                { id: '1', title: 'Test Lecture 1', status: 'ready', updatedAt: new Date().toISOString() },
                { id: '2', title: 'Test Lecture 2', status: 'processing', updatedAt: new Date().toISOString() },
            ],
        },
        isLoading: false,
    }),
    useVideoPlayer: () => ({}),
    useUploadStatusPolling: () => ({}),
    useCancelUpload: () => ({ mutateAsync: jest.fn() }),
}));

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: false,
        },
    },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
        <ThemeProvider>
            {children}
        </ThemeProvider>
    </QueryClientProvider>
);

describe('HomeScreen Performance', () => {
    it('renders smoothly', async () => {
        await measureRenders(<HomeScreen />, { wrapper: Wrapper });
    });
});
