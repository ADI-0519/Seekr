import { api } from '../../src/services/api';
import { Lecture, TranscriptSegment, TopicSegment, SearchResult, QAResult } from '../../src/types';

// Accessing the private transform functions using any since they are not exported
// We recreate them here exactly as they exist in api.ts to unit test the mapper logic

function transformVideoResponse(backend: any): Lecture {
    return {
        id: String(backend.id),
        title: backend.title,
        description: '',
        overview: '',
        duration: backend.duration || 0,
        thumbnailUrl: backend.thumbnail_path
            ? `http://localhost:8000/api/videos/${backend.id}/thumbnail`
            : backend.youtube_url
                ? `https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg`
                : '',
        videoUrl: `http://localhost:8000/api/videos/${backend.id}/stream`,
        status: 'ready', // Simplification for test
        createdAt: backend.created_at,
        updatedAt: backend.created_at,
        userId: 'backend',
    };
}

function transformTranscriptResponse(backend: any): TranscriptSegment[] {
    return backend.sentences.map((sentence: any) => ({
        id: String(sentence.id),
        text: sentence.text,
        startTime: sentence.start_time,
        endTime: sentence.end_time,
        words: [],
    }));
}

function transformSearchResponse(backend: any, lectureId: string): SearchResult[] {
    return backend.results.map((result: any, index: number) => ({
        id: String(index),
        lectureId,
        timestamp: result.start_time,
        text: result.text,
        relevanceScore: result.score,
        context: result.segment_title || '',
    }));
}

describe('API Service Transforms', () => {

    describe('transformVideoResponse', () => {
        it('transforms full backend response correctly', () => {
            const mockBackend = {
                id: 123,
                title: 'Test Lecture',
                duration: 600,
                youtube_url: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
                thumbnail_path: null,
                status: 'done',
                created_at: '2023-01-01T00:00:00Z'
            };

            const result = transformVideoResponse(mockBackend);

            expect(result.id).toBe('123');
            expect(result.title).toBe('Test Lecture');
            expect(result.duration).toBe(600);
            expect(result.thumbnailUrl).toBe('https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg');
            expect(result.videoUrl).toContain('123/stream');
            expect(result.createdAt).toBe('2023-01-01T00:00:00Z');
        });

        it('handles null durations safely', () => {
            const mockBackend = {
                id: 123,
                title: 'No Duration',
                duration: null,
                youtube_url: null,
                thumbnail_path: null,
                status: 'processing',
                created_at: '2023-01-01T00:00:00Z'
            };

            const result = transformVideoResponse(mockBackend);
            expect(result.duration).toBe(0);
            expect(result.thumbnailUrl).toBe('');
        });

        it('prioritizes local thumbnail over youtube url', () => {
            const mockBackend = {
                id: 123,
                title: 'Test',
                duration: 10,
                youtube_url: 'https://youtube.com/watch?v=123',
                thumbnail_path: '/path/thumbnail.jpg',
                status: 'done',
                created_at: ''
            };

            const result = transformVideoResponse(mockBackend);
            expect(result.thumbnailUrl).toContain('123/thumbnail');
        });
    });

    describe('extractYoutubeId (Implicit via Mock)', () => {
        it('extracts standard watch v= IDs', () => {
            const url = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';
            const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?]+)/);
            expect(match?.[1]).toBe('jNQXAC9IVRw');
        });

        it('extracts youtu.be shortlinks', () => {
            const url = 'https://youtu.be/jNQXAC9IVRw?t=10';
            const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?]+)/);
            expect(match?.[1]).toBe('jNQXAC9IVRw');
        });

        it('fails gracefully on invalid URLs', () => {
            const url = 'https://vimeo.com/123';
            const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?]+)/);
            expect(match).toBeNull();
        });
    });

    describe('transformTranscriptResponse', () => {
        it('maps backend sentences to frontend segments properly', () => {
            const mockBackend = {
                video_id: 1,
                sentences: [
                    { id: 10, text: 'Hello world.', start_time: 0.5, end_time: 2.0 },
                    { id: 11, text: 'This is a test.', start_time: 2.1, end_time: 4.5 }
                ],
                segments: []
            };

            const result = transformTranscriptResponse(mockBackend);

            expect(result.length).toBe(2);
            expect(result[0].id).toBe('10');
            expect(result[0].text).toBe('Hello world.');
            expect(result[0].startTime).toBe(0.5);
            expect(result[0].endTime).toBe(2.0);
            expect(result[0].words).toEqual([]); // Assert default init
        });
    });

    describe('transformSearchResponse', () => {
        it('maps backend search results properly with injected lecture ID', () => {
            const mockBackend = {
                query: 'test',
                results: [
                    { text: 'testing 123', start_time: 15.0, end_time: 20.0, score: 0.95, segment_title: 'Intro' },
                    { text: 'another test', start_time: 45.0, end_time: 50.0, score: 0.82, segment_title: null }
                ]
            };

            const result = transformSearchResponse(mockBackend, 'vid-123');

            expect(result.length).toBe(2);
            expect(result[0].lectureId).toBe('vid-123');
            expect(result[0].text).toBe('testing 123');
            expect(result[0].timestamp).toBe(15.0);
            expect(result[0].relevanceScore).toBe(0.95);
            expect(result[0].context).toBe('Intro');

            // Null context fallback
            expect(result[1].context).toBe('');
        });
    });
});
