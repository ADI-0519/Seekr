import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import UploadModalScreen from '../../app/upload';
import { useUploadVideo, useUploadLink } from '../../src/hooks';
import * as DocumentPicker from 'expo-document-picker';

const mockBack = jest.fn();
const mockReplace = jest.fn();

// Mock dependencies
jest.mock('expo-router', () => ({
    useRouter: () => ({ back: mockBack, replace: mockReplace }),
}));

jest.mock('../../src/hooks', () => ({
    useUploadVideo: jest.fn(),
    useUploadLink: jest.fn(),
}));

jest.mock('expo-document-picker', () => ({
    getDocumentAsync: jest.fn(),
}));

jest.mock('../../src/theme/ThemeProvider', () => ({
    useThemeColors: () => ({
        primaryEmerald: '#00FF00',
        textPrimary: '#FFFFFF',
        textSecondary: '#AAAAAA',
        borderSubtle: '#333333',
        chipBgReady: '#111111',
        surfaceElevated: '#222222',
        surfaceBase: '#000000',
        error: '#FF0000',
        success: '#00FF00',
    }),
    useTheme: () => ({ mode: 'light', isDark: false, cardStyle: 'solid', toggleMode: jest.fn(), setMode: jest.fn(), toggleCardStyle: jest.fn(), setCardStyle: jest.fn() }),
}));

describe('UploadModalScreen Integration', () => {

    beforeEach(() => {
        jest.clearAllMocks();
        jest.useFakeTimers();

        (useUploadVideo as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
        (useUploadLink as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it('renders initial drop zone and URL inputs', () => {
        const { getByText, getByPlaceholderText } = render(<UploadModalScreen />);

        expect(getByText(/Select your video file/i)).toBeTruthy();
        expect(getByText(/MP4, MOV, MKV, or WEBM/i)).toBeTruthy();
        expect(getByPlaceholderText(/Paste a YouTube or Kaltura link/i)).toBeTruthy();
    });

    it('rejects files that are too large', async () => {
        (DocumentPicker.getDocumentAsync as jest.Mock).mockResolvedValueOnce({
            canceled: false,
            assets: [{ name: 'huge_file.mp4', size: 2048 * 1024 * 1024, uri: 'file://huge_file.mp4' }] // 2GB
        });

        const { getByText } = render(<UploadModalScreen />);

        const browseBtn = getByText('Browse Files');
        fireEvent.press(browseBtn);

        await waitFor(() => {
            expect(getByText(/File is too large/i)).toBeTruthy();
        });
    });

    it('rejects unsupported file extensions', async () => {
        (DocumentPicker.getDocumentAsync as jest.Mock).mockResolvedValueOnce({
            canceled: false,
            assets: [{ name: 'document.pdf', size: 1024, uri: 'file://document.pdf' }]
        });

        const { getByText } = render(<UploadModalScreen />);
        fireEvent.press(getByText('Browse Files'));

        await waitFor(() => {
            expect(getByText(/Unsupported file type/i)).toBeTruthy();
        });
    });

    it('accepts valid files, allows title edit, and handles upload success', async () => {
        (DocumentPicker.getDocumentAsync as jest.Mock).mockResolvedValueOnce({
            canceled: false,
            assets: [{ name: 'lecture_video.mp4', size: 1024 * 1024 * 10, uri: 'file://lecture_video.mp4' }]
        });

        const mockMutateAsync = jest.fn().mockResolvedValueOnce({
            data: { id: '123' },
            success: true,
        });
        (useUploadVideo as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });

        const { getByText, getByPlaceholderText, queryByText } = render(<UploadModalScreen />);
        fireEvent.press(getByText('Browse Files'));

        // Wait for file selection state layout changes
        await waitFor(() => {
            expect(getByText('lecture_video.mp4')).toBeTruthy();
            expect(getByText('Start Upload')).toBeTruthy();
        });

        // The title should be auto-populated
        const titleInput = getByPlaceholderText(/Lecture Title/i);
        expect(titleInput.props.value).toBe('lecture_video');

        // Click Start Upload
        fireEvent.press(getByText('Start Upload'));

        // It goes into "uploading" state
        expect(getByText(/Validating & Uploading/i)).toBeTruthy();

        // Advance timers to trigger the mock promise
        act(() => {
            jest.advanceTimersByTime(2000); // 2 seconds should finish it since mock resolves immediately
        });

        await waitFor(() => {
            expect(mockMutateAsync).toHaveBeenCalledWith({
                file: expect.any(Object),
                title: 'lecture_video'
            });
            expect(getByText(/Upload Complete/i)).toBeTruthy();
            expect(queryByText(/Processing will begin shortly/i)).toBeTruthy();
        });

    });

    it('simulates URL import successfully', async () => {
        const mockMutateAsync = jest.fn().mockResolvedValueOnce({
            data: { id: '124' },
            success: true,
        });
        (useUploadLink as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });

        const { getByText, getByPlaceholderText, queryByText } = render(<UploadModalScreen />);

        // We must enter a title and a URL
        fireEvent.changeText(getByPlaceholderText(/Lecture Title/i), 'YouTube Video');
        fireEvent.changeText(getByPlaceholderText(/Paste a YouTube/i), 'https://youtube.com/watch?v=123');

        fireEvent.press(getByText('Import'));

        act(() => {
            jest.advanceTimersByTime(2000);
        });

        await waitFor(() => {
            expect(mockMutateAsync).toHaveBeenCalledWith({
                url: 'https://youtube.com/watch?v=123',
                title: 'YouTube Video' // Matches our input
            });
            expect(getByText(/Upload Complete/i)).toBeTruthy();
        });

    });

    it('redirects to existing lecture when upload returns fromCache=true', async () => {
        (DocumentPicker.getDocumentAsync as jest.Mock).mockResolvedValueOnce({
            canceled: false,
            assets: [{ name: 'dup_video.mp4', size: 1024 * 1024 * 5, uri: 'file://dup_video.mp4' }]
        });

        const mockMutateAsync = jest.fn().mockResolvedValueOnce({
            data: { id: 'existing-lecture-9' },
            success: true,
            fromCache: true,
            message: 'This video is already in your library.',
        });
        (useUploadVideo as jest.Mock).mockReturnValue({ mutateAsync: mockMutateAsync });

        const { getByText } = render(<UploadModalScreen />);
        fireEvent.press(getByText('Browse Files'));

        await waitFor(() => {
            expect(getByText('dup_video.mp4')).toBeTruthy();
        });

        fireEvent.press(getByText('Start Upload'));

        act(() => {
            jest.advanceTimersByTime(2000);
        });

        await waitFor(() => {
            expect(getByText(/already in your library/i)).toBeTruthy();
        });

        act(() => {
            jest.runOnlyPendingTimers();
        });

        await waitFor(() => {
            expect(mockReplace).toHaveBeenCalledWith('/(app)/lectures/existing-lecture-9');
        });
        expect(mockBack).not.toHaveBeenCalled();
    });
});
