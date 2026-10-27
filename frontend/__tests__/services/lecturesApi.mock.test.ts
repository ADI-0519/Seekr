import { LecturesApi } from '../../src/services/api-client/lectures';

const mockedLectures = [
    {
        id: '1',
        title: 'Mock Ready',
        description: '',
        overview: null,
        duration: 120,
        thumbnailUrl: '',
        videoUrl: 'https://video/1.mp4',
        resumePosition: 0,
        status: 'ready',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
        userId: 'u1',
    },
    {
        id: '2',
        title: 'Mock Processing',
        description: '',
        overview: null,
        duration: 60,
        thumbnailUrl: '',
        videoUrl: 'https://video/2.mp4',
        resumePosition: 0,
        status: 'processing',
        createdAt: '2026-01-02T00:00:00Z',
        updatedAt: '2026-01-02T00:00:00Z',
        userId: 'u1',
    },
] as any;

jest.mock('../../src/services/api-client/shared', () => ({
    FEATURES: { enableMockData: true },
    delay: jest.fn(() => Promise.resolve()),
    getMockLectures: jest.fn(() => mockedLectures),
    getMockTopics: jest.fn((lectureId: string) => [{ id: 't1', title: `Topic ${lectureId}`, summary: '', startTime: 0, endTime: 10, transcriptSegmentIds: [] }]),
    getMockTranscript: jest.fn((lectureId: string) => [{ id: 's1', text: `Transcript ${lectureId}`, startTime: 0, endTime: 1, words: [] }]),
    mockQAResult: {
        id: 'qa1',
        question: 'q',
        answer: 'a',
        citations: [],
        confidence: 0.9,
    },
    mockQueryResult: jest.fn((query: string, mode: 'auto' | 'retrieval' | 'qa') => ({
        query,
        mode: mode === 'qa' ? 'qa' : 'retrieval',
        results: mode === 'qa' ? undefined : [{ id: 'r1', lectureId: '1', timestamp: 1, text: 'x', relevanceScore: 0.8, context: 'c' }],
        answer: mode === 'qa' ? 'answer' : undefined,
    })),
    mockSearch: jest.fn((query: string) => [{ id: 'r1', lectureId: '1', timestamp: 1, text: query, relevanceScore: 0.8, context: 'c' }]),
    mockSlides: [{ id: 'sl1', startTime: 0, endTime: 1, ocrText: 'slide', frameUrl: 'https://slide.jpg' }],
    buildMockLecture: jest.fn((title: string, index: number, imported = false) => ({
        id: String(index + 1),
        title,
        description: imported ? 'Imported from link' : '',
        overview: null,
        duration: 0,
        thumbnailUrl: '',
        videoUrl: '',
        resumePosition: 0,
        status: 'processing',
        createdAt: '2026-01-01T00:00:00Z',
        updatedAt: '2026-01-01T00:00:00Z',
        userId: 'u1',
    })),
    transformNotesResponse: jest.fn(),
    transformQueryResponse: jest.fn(),
    transformSearchResponse: jest.fn(),
    transformSegmentsToTopics: jest.fn(),
    transformSlideFrame: jest.fn(),
    transformTranscriptResponse: jest.fn(),
    transformVideoResponse: jest.fn(),
}));

describe('LecturesApi mock mode', () => {
    const request = jest.fn();
    const api = new LecturesApi(request as any, 'http://localhost:8000/api');

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('covers all mock-mode methods and returns expected shapes', async () => {
        const list = await api.getLectures();
        expect(list.items).toHaveLength(2);

        const one = await api.getLecture('1');
        expect(one.success).toBe(true);
        const missing = await api.getLecture('999');
        expect(missing.success).toBe(false);

        const playback = await api.updateLecturePlaybackPosition('1', -3);
        expect(playback.data.positionSeconds).toBe(0);

        const upload = await api.uploadVideo({ uri: 'file://x', name: 'x.mp4' }, 'Uploaded');
        expect(upload.success).toBe(true);
        const link = await api.uploadLink('https://youtu.be/abc', 'Imported');
        expect(link.success).toBe(true);

        const status = await api.getUploadStatus('2');
        expect(status.success).toBe(true);
        expect(status.data.lectureId).toBe('2');

        const cancel = await api.cancelUpload('2');
        expect(cancel.data.status).toBe('cancelled');

        const del = await api.deleteLecture('2');
        expect(del.data.lectureId).toBe('2');

        const transcript = await api.getTranscript('1');
        expect(transcript.data[0].id).toBe('s1');

        const slides = await api.getSlides('1');
        expect(slides.data[0].id).toBe('sl1');

        const topics = await api.getTopics('1');
        expect(topics.data[0].id).toBe('t1');

        const search = await api.search('1', 'activation');
        expect(search.success).toBe(true);

        const qa = await api.askQuestion('1', 'What is this?');
        expect(qa.data.answer).toBe('a');

        const query = await api.query('1', 'activation', 'retrieval');
        expect(query.success).toBe(true);

        const notes = await api.generateNotes('1');
        expect(notes.success).toBe(true);
        expect(notes.data.notes.length).toBeGreaterThan(0);

        const pdfBlob = await api.exportNotesPDF('1', []);
        expect(pdfBlob.type).toBe('application/pdf');

        const zipBlob = await api.downloadSlides('1');
        expect(zipBlob.type).toBe('application/zip');

        expect(api.getSlidePreviewUrl('1', '99')).toContain('/videos/1/slides/99/preview');

        const chat = await api.getChatHistory('1');
        expect(chat.success).toBe(true);
        expect(chat.data).toEqual([]);

        await api.saveChatHistory('1', [{ role: 'user', text: 'hello' }]);
        expect(request).not.toHaveBeenCalled();
    });
});
