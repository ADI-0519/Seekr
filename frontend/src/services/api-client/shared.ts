import { API_BASE_URL, FEATURES } from '@/constants';
import {
    ApiResponse,
    GeneratedNotesResponse,
    Lecture,
    ProfileSummary,
    QAResult,
    QueryResult,
    SearchResult,
    SlideFrame,
    TopicSegment,
    TranscriptSegment,
    UploadStatus,
    UserSettings,
} from '@/types';
import {
    getMockLectures,
    getMockVideoUrl,
    getMockTopics,
    getMockTranscript,
    mockQAResult,
    mockSearchResults,
} from '../mockData';
import { mapProcessingStatus } from '../uploadStatus';

export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockSlides: SlideFrame[] = [
    {
        id: '1',
        startTime: 0,
        endTime: 6.3,
        ocrText: 'Introduction to Seekr',
        frameUrl: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=640',
    },
    {
        id: '2',
        startTime: 8.2,
        endTime: 16.5,
        ocrText: 'Video processing pipeline',
        frameUrl: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=640',
    },
    {
        id: '3',
        startTime: 20.1,
        endTime: 28.7,
        ocrText: 'Slides extraction architecture',
        frameUrl: 'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=640',
    },
];

export interface BackendVideoResponse {
    id: number;
    title: string;
    duration: number | null;
    youtube_url: string | null;
    thumbnail_path: string | null;
    overview: string | null;
    status: string;
    created_at: string;
    video_url?: string | null;
    thumbnail_url?: string | null;
    last_playback_position?: number | null;
    from_cache?: boolean;
}

export interface BackendSentenceResponse {
    id: number;
    text: string;
    start_time: number;
    end_time: number;
}

export interface BackendSegmentResponse {
    id: number;
    title: string;
    summary: string | null;
    start_time: number;
    end_time: number;
}

export interface BackendCancelJobResponse {
    video_id: number;
    task_id: string;
    status: string;
    message: string;
}

export interface DeleteLectureResponse {
    lectureId: string;
}

export interface BackendTranscriptResponse {
    video_id: number;
    sentences: BackendSentenceResponse[];
    segments: BackendSegmentResponse[];
}

export interface BackendSearchResult {
    text: string;
    start_time: number;
    end_time: number;
    score: number;
    segment_title: string | null;
}

export interface BackendSearchResponse {
    results: BackendSearchResult[];
    query: string;
}

export interface BackendQueryResponse {
    query: string;
    mode: 'retrieval' | 'qa';
    results?: BackendSearchResult[];
    answer?: string;
    citations?: {
        start_time: number;
        end_time: number;
        text: string;
        segment_title: string;
    }[];
}

export interface BackendSlideFrameResponse {
    id: number;
    start_time: number;
    end_time: number;
    ocr_text: string | null;
    frame_url: string | null;
}

export interface BackendSlideListResponse {
    video_id: number;
    total: number;
    slides: BackendSlideFrameResponse[];
}

export interface BackendGeneratedNoteItem {
    segment_id: number;
    title: string;
    notes_markdown: string;
    start_time: number;
    end_time: number;
}

export interface BackendNotesResponse {
    video_id: number;
    notes: BackendGeneratedNoteItem[];
}

export interface BackendProfileRecentUpload {
    id: number;
    title: string;
    status: string;
    created_at: string;
    duration: number | null;
}

export interface BackendProfileSummaryResponse {
    lecture_count: number;
    ready_lecture_count: number;
    processing_lecture_count: number;
    failed_lecture_count: number;
    total_duration_seconds: number;
    recent_uploads: BackendProfileRecentUpload[];
}

export interface SyncProfileRequest {
    displayName?: string | null;
    photoURL?: string | null;
}

export interface BackendProfileSyncResponse {
    uid: string;
    email: string | null;
    display_name: string | null;
    photo_url: string | null;
    provider: string | null;
    last_login_at: string | null;
}

export interface BackendUserSettingsResponse {
    uid: string;
    theme_mode: 'light' | 'dark';
    background_mode: 'animated' | 'static';
    card_style: 'solid' | 'transparent';
    video_animation: 1 | 2 | 3 | 4 | 5 | 6 | 7;
    autoplay_next: boolean;
    pause_on_leave: boolean;
    volume_default: number;
    muted_default: boolean;
    preferred_language: string;
    timezone: string | null;
}

export interface UserSettingsUpdateRequest {
    themeMode: 'light' | 'dark';
    backgroundMode: 'animated' | 'static';
    cardStyle: 'solid' | 'transparent';
    videoAnimation: 1 | 2 | 3 | 4 | 5 | 6 | 7;
    autoplayNext: boolean;
    pauseOnLeave: boolean;
    volumeDefault: number;
    mutedDefault: boolean;
    preferredLanguage: string;
    timezone: string | null;
}

const API_ROOT = `${API_BASE_URL}/api`;

export function extractYoutubeId(url: string | null): string {
    if (!url) return '';
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?]+)/);
    return match ? match[1] : '';
}

export function transformVideoResponse(backend: BackendVideoResponse): Lecture {
    const resolvedOverview = backend.overview?.trim() || null;
    return {
        id: String(backend.id),
        title: backend.title,
        description: resolvedOverview || '',
        overview: resolvedOverview,
        duration: backend.duration || 0,
        thumbnailUrl:
            backend.thumbnail_url ||
            (backend.thumbnail_path
                ? `${API_ROOT}/videos/${backend.id}/thumbnail`
                : backend.youtube_url
                  ? `https://img.youtube.com/vi/${extractYoutubeId(backend.youtube_url)}/maxresdefault.jpg`
                  : ''),
        videoUrl: backend.video_url || `${API_ROOT}/videos/${backend.id}/stream`,
        resumePosition: backend.last_playback_position ?? 0,
        status: mapProcessingStatus(backend.status),
        createdAt: backend.created_at,
        updatedAt: backend.created_at,
        userId: 'backend',
    };
}

export function transformTranscriptResponse(
    backend: BackendTranscriptResponse
): TranscriptSegment[] {
    return backend.sentences.map(sentence => ({
        id: String(sentence.id),
        text: sentence.text,
        startTime: sentence.start_time,
        endTime: sentence.end_time,
        words: [],
    }));
}

export function transformSegmentsToTopics(
    backend: BackendSegmentResponse[]
): TopicSegment[] {
    return backend.map(segment => ({
        id: String(segment.id),
        title: segment.title,
        summary: segment.summary || '',
        startTime: segment.start_time,
        endTime: segment.end_time,
        transcriptSegmentIds: [],
    }));
}

export function transformSlideFrame(backend: BackendSlideFrameResponse): SlideFrame {
    return {
        id: String(backend.id),
        startTime: backend.start_time,
        endTime: backend.end_time,
        ocrText: backend.ocr_text,
        frameUrl: backend.frame_url,
    };
}

export function transformSearchResponse(
    backend: BackendSearchResponse,
    lectureId: string
): SearchResult[] {
    return backend.results.map((result, index) => ({
        id: String(index),
        lectureId,
        timestamp: result.start_time,
        text: result.text,
        relevanceScore: result.score,
        context: result.segment_title || '',
    }));
}

export function transformQueryResponse(
    backend: BackendQueryResponse,
    lectureId: string
): QueryResult {
    return {
        query: backend.query,
        mode: backend.mode,
        results: backend.results
            ? transformSearchResponse(
                  { results: backend.results, query: backend.query },
                  lectureId
              )
            : undefined,
        answer: backend.answer,
        citations: backend.citations?.map(c => ({
            startTime: c.start_time,
            endTime: c.end_time,
            text: c.text,
            segmentTitle: c.segment_title,
        })),
    };
}

export function transformNotesResponse(
    backend: BackendNotesResponse
): GeneratedNotesResponse {
    return {
        videoId: backend.video_id,
        notes: backend.notes.map(n => ({
            segmentId: n.segment_id,
            title: n.title,
            notesMarkdown: n.notes_markdown,
            startTime: n.start_time,
            endTime: n.end_time,
        })),
    };
}

export function transformProfileSummaryResponse(
    backend: BackendProfileSummaryResponse
): ProfileSummary {
    return {
        lectureCount: backend.lecture_count,
        readyLectureCount: backend.ready_lecture_count,
        processingLectureCount: backend.processing_lecture_count,
        failedLectureCount: backend.failed_lecture_count,
        totalDurationSeconds: backend.total_duration_seconds,
        recentUploads: backend.recent_uploads.map(upload => ({
            id: String(upload.id),
            title: upload.title,
            status: mapProcessingStatus(upload.status),
            createdAt: upload.created_at,
            duration: upload.duration || 0,
        })),
    };
}

export function transformUserSettingsResponse(
    backend: BackendUserSettingsResponse
): UserSettings {
    return {
        themeMode: backend.theme_mode,
        backgroundMode: backend.background_mode,
        cardStyle: backend.card_style,
        videoAnimation: backend.video_animation,
        autoplayNext: backend.autoplay_next,
        pauseOnLeave: backend.pause_on_leave,
        volumeDefault: backend.volume_default,
        mutedDefault: backend.muted_default,
        preferredLanguage: backend.preferred_language,
        timezone: backend.timezone,
    };
}

export function buildMockLecture(title: string, index: number, imported = false): Lecture {
    return {
        id: String(index + 1),
        title,
        description: imported ? 'Imported from link' : '',
        overview: null,
        duration: 0,
        thumbnailUrl: imported
            ? 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400'
            : 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=400',
        videoUrl: getMockVideoUrl(index),
        resumePosition: 0,
        status: 'processing',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        userId: 'user1',
    };
}

export function buildMockProfileSummary(): ApiResponse<ProfileSummary> {
    const mockLectures = getMockLectures();
    const lectureCount = mockLectures.length;
    const readyLectureCount = mockLectures.filter(lecture => lecture.status === 'ready').length;
    const processingLectureCount = mockLectures.filter(
        lecture =>
            lecture.status === 'processing' ||
            lecture.status === 'transcribing' ||
            lecture.status === 'segmenting'
    ).length;
    const failedLectureCount = mockLectures.filter(lecture => lecture.status === 'failed').length;
    const totalDurationSeconds = mockLectures.reduce((sum, lecture) => sum + lecture.duration, 0);

    return {
        data: {
            lectureCount,
            readyLectureCount,
            processingLectureCount,
            failedLectureCount,
            totalDurationSeconds,
            recentUploads: mockLectures
                .slice()
                .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
                .slice(0, 5)
                .map(lecture => ({
                    id: lecture.id,
                    title: lecture.title,
                    status: lecture.status,
                    createdAt: lecture.createdAt,
                    duration: lecture.duration,
                })),
        },
        success: true,
    };
}

export function mockSearch(query: string): SearchResult[] {
    const q = query.toLowerCase();
    const results = mockSearchResults.filter(
        r => r.text.toLowerCase().includes(q) || r.context.toLowerCase().includes(q)
    );
    return results.length > 0 ? results : mockSearchResults;
}

export function mockQueryResult(
    query: string,
    mode: 'auto' | 'retrieval' | 'qa'
): QueryResult {
    const isMockQA = mode === 'qa' || (mode === 'auto' && query.trim().endsWith('?'));
    if (isMockQA) {
        return {
            query,
            mode: 'qa',
            answer: mockQAResult.answer,
            citations: mockQAResult.citations,
        };
    }
    return {
        query,
        mode: 'retrieval',
        results: mockSearch(query),
    };
}

export {
    FEATURES,
    getMockLectures,
    getMockTopics,
    getMockTranscript,
    mockQAResult,
    mockSearchResults,
};
