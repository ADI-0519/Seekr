import {
    buildMockLecture,
    buildMockProfileSummary,
    extractYoutubeId,
    mockQueryResult,
    mockSearch,
    transformNotesResponse,
    transformProfileSummaryResponse,
    transformQueryResponse,
    transformSearchResponse,
    transformSegmentsToTopics,
    transformSlideFrame,
    transformTranscriptResponse,
    transformUserSettingsResponse,
    transformVideoResponse,
    type BackendProfileSummaryResponse,
    type BackendQueryResponse,
    type BackendSearchResponse,
    type BackendTranscriptResponse,
    type BackendUserSettingsResponse,
    type BackendVideoResponse,
} from '../../src/services/api-client/shared';

describe('api-client/shared transforms', () => {
    it('extractYoutubeId handles full, short and invalid urls', () => {
        expect(extractYoutubeId('https://www.youtube.com/watch?v=jNQXAC9IVRw')).toBe('jNQXAC9IVRw');
        expect(extractYoutubeId('https://youtu.be/jNQXAC9IVRw?t=10')).toBe('jNQXAC9IVRw');
        expect(extractYoutubeId('https://vimeo.com/123')).toBe('');
        expect(extractYoutubeId(null)).toBe('');
    });

    it('transformVideoResponse prefers direct backend urls and falls back correctly', () => {
        const backendWithDirectUrls: BackendVideoResponse = {
            id: 7,
            title: 'Lecture A',
            duration: 123,
            youtube_url: 'https://youtu.be/abc123',
            thumbnail_path: '/thumb.jpg',
            thumbnail_url: 'https://cdn/thumb.jpg',
            video_url: 'https://cdn/video.mp4',
            overview: '  Trim me  ',
            status: 'done',
            created_at: '2026-01-01T00:00:00Z',
            from_cache: false,
        };

        const transformedDirect = transformVideoResponse(backendWithDirectUrls);
        expect(transformedDirect.thumbnailUrl).toBe('https://cdn/thumb.jpg');
        expect(transformedDirect.videoUrl).toBe('https://cdn/video.mp4');
        expect(transformedDirect.overview).toBe('Trim me');
        expect(transformedDirect.description).toBe('Trim me');
        expect(transformedDirect.resumePosition).toBe(0);

        const backendWithFallbacks: BackendVideoResponse = {
            id: 9,
            title: 'Lecture B',
            duration: null,
            youtube_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            thumbnail_path: '/thumb.jpg',
            thumbnail_url: null,
            video_url: null,
            overview: null,
            status: 'processing',
            created_at: '2026-01-02T00:00:00Z',
            last_playback_position: 12.5,
        };

        const transformedFallback = transformVideoResponse(backendWithFallbacks);
        expect(transformedFallback.duration).toBe(0);
        expect(transformedFallback.thumbnailUrl).toContain('/api/videos/9/thumbnail');
        expect(transformedFallback.videoUrl).toContain('/api/videos/9/stream');
        expect(transformedFallback.resumePosition).toBe(12.5);
        expect(transformedFallback.overview).toBeNull();
        expect(transformedFallback.description).toBe('');
    });

    it('transforms transcript, segments and slide frame payloads', () => {
        const transcriptBackend: BackendTranscriptResponse = {
            video_id: 1,
            sentences: [
                { id: 1, text: 'hello', start_time: 0.1, end_time: 0.9 },
                { id: 2, text: 'world', start_time: 1.0, end_time: 1.9 },
            ],
            segments: [],
        };
        const transcript = transformTranscriptResponse(transcriptBackend);
        expect(transcript).toHaveLength(2);
        expect(transcript[0]).toEqual({
            id: '1',
            text: 'hello',
            startTime: 0.1,
            endTime: 0.9,
            words: [],
        });

        const topics = transformSegmentsToTopics([
            { id: 10, title: 'Intro', summary: null, start_time: 0, end_time: 30 },
        ]);
        expect(topics[0].summary).toBe('');
        expect(topics[0].transcriptSegmentIds).toEqual([]);

        const slide = transformSlideFrame({
            id: 5,
            start_time: 3,
            end_time: 6,
            ocr_text: 'Slide text',
            frame_url: 'https://slide/5.jpg',
        });
        expect(slide).toEqual({
            id: '5',
            startTime: 3,
            endTime: 6,
            ocrText: 'Slide text',
            frameUrl: 'https://slide/5.jpg',
        });
    });

    it('transforms search/query/notes/profile/settings payloads', () => {
        const searchBackend: BackendSearchResponse = {
            query: 'activation',
            results: [
                { text: 'relu', start_time: 10, end_time: 13, score: 0.9, segment_title: 'Acts' },
                { text: 'sigmoid', start_time: 20, end_time: 24, score: 0.7, segment_title: null },
            ],
        };
        const search = transformSearchResponse(searchBackend, '42');
        expect(search[0].lectureId).toBe('42');
        expect(search[1].context).toBe('');

        const queryBackend: BackendQueryResponse = {
            query: 'what is relu?',
            mode: 'qa',
            answer: 'A non-linear activation',
            citations: [{ start_time: 9, end_time: 14, text: 'relu info', segment_title: 'Acts' }],
        };
        const query = transformQueryResponse(queryBackend, '42');
        expect(query.mode).toBe('qa');
        expect(query.citations?.[0].segmentTitle).toBe('Acts');

        const retrievalBackend: BackendQueryResponse = {
            query: 'relu',
            mode: 'retrieval',
            results: searchBackend.results,
        };
        const retrieval = transformQueryResponse(retrievalBackend, '42');
        expect(retrieval.mode).toBe('retrieval');
        expect(retrieval.results?.length).toBe(2);

        const notes = transformNotesResponse({
            video_id: 3,
            notes: [{ segment_id: 1, title: 'T1', notes_markdown: '# md', start_time: 0, end_time: 5 }],
        });
        expect(notes.videoId).toBe(3);
        expect(notes.notes[0].notesMarkdown).toBe('# md');

        const profileBackend: BackendProfileSummaryResponse = {
            lecture_count: 2,
            ready_lecture_count: 1,
            processing_lecture_count: 1,
            failed_lecture_count: 0,
            total_duration_seconds: 100,
            recent_uploads: [{ id: 1, title: 'A', status: 'done', created_at: '2026-01-01', duration: null }],
        };
        const profile = transformProfileSummaryResponse(profileBackend);
        expect(profile.lectureCount).toBe(2);
        expect(profile.recentUploads[0].duration).toBe(0);

        const settingsBackend: BackendUserSettingsResponse = {
            uid: 'u1',
            theme_mode: 'dark',
            background_mode: 'animated',
            card_style: 'solid',
            video_animation: 3,
            autoplay_next: true,
            pause_on_leave: false,
            volume_default: 0.8,
            muted_default: false,
            preferred_language: 'en',
            timezone: 'Europe/London',
        };
        const settings = transformUserSettingsResponse(settingsBackend);
        expect(settings.themeMode).toBe('dark');
        expect(settings.videoAnimation).toBe(3);
        expect(settings.timezone).toBe('Europe/London');
    });

    it('builds deterministic mock helpers', () => {
        const uploaded = buildMockLecture('Local upload', 0, false);
        const imported = buildMockLecture('Imported', 1, true);
        expect(uploaded.status).toBe('processing');
        expect(imported.description).toBe('Imported from link');
        expect(imported.thumbnailUrl).not.toBe(uploaded.thumbnailUrl);

        const summary = buildMockProfileSummary();
        expect(summary.success).toBe(true);
        expect(summary.data.lectureCount).toBeGreaterThanOrEqual(summary.data.readyLectureCount);
        expect(summary.data.recentUploads.length).toBeLessThanOrEqual(5);

        const qaResult = mockQueryResult('What is this?', 'auto');
        expect(qaResult.mode).toBe('qa');

        const retrievalResult = mockQueryResult('activation', 'retrieval');
        expect(retrievalResult.mode).toBe('retrieval');
        expect(retrievalResult.results && retrievalResult.results.length).toBeGreaterThan(0);

        const searchFallback = mockSearch('__unlikely_query__');
        expect(searchFallback.length).toBeGreaterThan(0);
    });
});
