import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services';
import { Lecture, UploadStatus } from '@/types';
import { useVideoPlayerStore } from '@/store/videoStore';

export function getPollingDelay(attempt: number) {
    return Math.min(8000, 1000 * 2 ** Math.min(attempt, 3));
}

export function useLectures() {
    return useQuery({
        queryKey: ['lectures'],
        queryFn: () => api.getLectures(),
        staleTime: 30_000,   // don't refetch if navigating back
        gcTime: 300_000,     // keep in cache
    });
}

export function useLecture(id: string) {
    return useQuery({
        queryKey: ['lecture', id],
        queryFn: () => api.getLecture(id),
        enabled: !!id,
        staleTime: 60_000,
        gcTime: 300_000,
    });
}

export function useProfileSummary() {
    return useQuery({
        queryKey: ['profileSummary'],
        queryFn: () => api.getProfileSummary(),
        staleTime: 30_000,
        gcTime: 300_000,
    });
}

export function useTranscript(lectureId: string) {
    return useQuery({
        queryKey: ['transcript', lectureId],
        queryFn: () => api.getTranscript(lectureId),
        enabled: !!lectureId,
        staleTime: 300_000,  // Transcripts rarely change
        gcTime: 600_000,
    });
}

export function useTopics(lectureId: string) {
    return useQuery({
        queryKey: ['topics', lectureId],
        queryFn: () => api.getTopics(lectureId),
        enabled: !!lectureId,
        staleTime: 300_000,
        gcTime: 600_000,
    });
}

export function useGenerateNotes(lectureId: string) {
    return useQuery({
        queryKey: ['notes', lectureId],
        queryFn: () => api.generateNotes(lectureId),
        enabled: false,
        staleTime: Infinity,
        gcTime: 600_000,
        retry: false,
    });
}

export function useSlides(lectureId: string) {
    return useQuery({
        queryKey: ['slides', lectureId],
        queryFn: () => api.getSlides(lectureId),
        enabled: !!lectureId,
        staleTime: 300_000,
        gcTime: 600_000,
    });
}

export function useUploadVideo() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ file, title }: { file: any; title: string }) =>
            api.uploadVideo(file, title),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lectures'] });
            queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
        },
    });
}

export function useUploadLink() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ url, title }: { url: string; title: string }) =>
            api.uploadLink(url, title),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['lectures'] });
            queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
        },
    });
}

export function useCancelUpload() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (lectureId: string) => api.cancelUpload(lectureId),
        onSuccess: (_, lectureId) => {
            useVideoPlayerStore.getState().removeLecture(lectureId);
            queryClient.invalidateQueries({ queryKey: ['lectures'] });
            queryClient.invalidateQueries({ queryKey: ['lecture', lectureId] });
            queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
        },
    });
}

export function useDeleteLecture() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (lectureId: string) => api.deleteLecture(lectureId),
        onSuccess: async (_, lectureId) => {
            useVideoPlayerStore.getState().removeLecture(lectureId);
            await queryClient.invalidateQueries({ queryKey: ['lectures'] });
            await queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
            queryClient.removeQueries({ queryKey: ['lecture', lectureId] });
            queryClient.removeQueries({ queryKey: ['transcript', lectureId] });
            queryClient.removeQueries({ queryKey: ['topics', lectureId] });
            queryClient.removeQueries({ queryKey: ['notes', lectureId] });
            queryClient.removeQueries({ queryKey: ['slides', lectureId] });
        },
    });
}

export function useLectureQuery(lectureId: string) {
    return useMutation({
        mutationFn: ({ query, mode }: { query: string; mode?: 'auto' | 'retrieval' | 'qa' }) =>
            api.query(lectureId, query, mode ?? 'auto'),
    });
}

export function useUploadStatusPolling(lectureId: string | null, enabled = true) {
    const [status, setStatus] = useState<UploadStatus | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (!lectureId || !enabled) {
            setStatus(null);
            setError(null);
            setAttempt(0);
            setIsPolling(false);
            return;
        }

        let cancelled = false;
        setStatus(null);
        setIsPolling(true);
        setError(null);
        setAttempt(0);

        const poll = async (nextAttempt: number) => {
            try {
                const response = await api.getUploadStatus(lectureId);
                if (cancelled) return;

                setStatus(response.data);
                setError(null);

                if (response.data.state === 'done' || response.data.state === 'failed') {
                    setIsPolling(false);
                    return;
                }

                const delayMs = getPollingDelay(nextAttempt);
                setAttempt(nextAttempt + 1);
                timeoutRef.current = setTimeout(() => {
                    void poll(nextAttempt + 1);
                }, delayMs);
            } catch (e: any) {
                if (cancelled) return;
                const message = e?.message || 'Failed to fetch upload status';
                setError(message);

                const delayMs = getPollingDelay(nextAttempt);
                setAttempt(nextAttempt + 1);
                timeoutRef.current = setTimeout(() => {
                    void poll(nextAttempt + 1);
                }, delayMs);
            }
        };

        void poll(0);

        return () => {
            cancelled = true;
            setIsPolling(false);
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
                timeoutRef.current = null;
            }
        };
    }, [lectureId, enabled]);

    const refetchNow = async () => {
        if (!lectureId) return;
        try {
            const response = await api.getUploadStatus(lectureId);
            setStatus(response.data);
            setError(null);
        } catch (e: any) {
            setError(e?.message || 'Failed to fetch upload status');
        }
    };

    return {
        status,
        isPolling,
        error,
        attempt,
        refetchNow,
    };
}
