import {
    ApiResponse,
    GeneratedNote,
    GeneratedNotesResponse,
    Lecture,
    PaginatedResponse,
    QAResult,
    QueryResult,
    SearchResult,
    SlideFrame,
    TopicSegment,
    TranscriptSegment,
    UploadStatus,
} from '@/types';
import {
    BackendCancelJobResponse,
    BackendNotesResponse,
    BackendQueryResponse,
    BackendSearchResponse,
    BackendSlideListResponse,
    BackendTranscriptResponse,
    BackendVideoResponse,
    DeleteLectureResponse,
    FEATURES,
    buildMockLecture,
    delay,
    getMockLectures,
    getMockTopics,
    getMockTranscript,
    mockQAResult,
    mockQueryResult,
    mockSearch,
    mockSlides,
    transformNotesResponse,
    transformQueryResponse,
    transformSearchResponse,
    transformSegmentsToTopics,
    transformSlideFrame,
    transformTranscriptResponse,
    transformVideoResponse,
} from './shared';
import { buildApiError, RequestFn } from './http';
import {
    BackendVideoStatusResponse,
    getStageProgress,
    mapBackendStateToJobState,
    transformVideoStatusResponse,
} from '../uploadStatus';

export class LecturesApi {
    constructor(
        private readonly request: RequestFn,
        private readonly baseUrl: string
    ) {}

    async getLectures(): Promise<PaginatedResponse<Lecture>> {
        if (FEATURES.enableMockData) {
            await delay(500);
            const mockLectures = getMockLectures();
            return {
                items: mockLectures,
                total: mockLectures.length,
                page: 1,
                pageSize: 10,
                hasMore: false,
            };
        }

        const response = await this.request('/videos/');
        if (!response.ok) {
            throw await buildApiError(response, 'Failed to load lectures');
        }
        const backendVideos: BackendVideoResponse[] = await response.json();
        return {
            items: backendVideos.map(transformVideoResponse),
            total: backendVideos.length,
            page: 1,
            pageSize: 20,
            hasMore: false,
        };
    }

    async getLecture(id: string): Promise<ApiResponse<Lecture>> {
        if (FEATURES.enableMockData) {
            await delay(300);
            const mockLectures = getMockLectures();
            const lecture = mockLectures.find(l => l.id === id);
            if (!lecture) {
                return { data: null as any, success: false, message: 'Lecture not found' };
            }
            return { data: lecture, success: true };
        }

        const response = await this.request(`/videos/${id}`);
        if (!response.ok) {
            return { data: null as any, success: false, message: 'Video not found' };
        }
        const backendVideo: BackendVideoResponse = await response.json();
        return { data: transformVideoResponse(backendVideo), success: true };
    }

    async updateLecturePlaybackPosition(
        lectureId: string,
        positionSeconds: number
    ): Promise<ApiResponse<{ videoId: string; positionSeconds: number }>> {
        if (FEATURES.enableMockData) {
            return {
                data: { videoId: lectureId, positionSeconds: Math.max(0, positionSeconds) },
                success: true,
            };
        }

        const response = await this.request(`/videos/${lectureId}/playback`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ position_seconds: Math.max(0, positionSeconds) }),
        });

        if (!response.ok) {
            throw await buildApiError(response, 'Failed to save playback position');
        }

        const data: { video_id: number; position_seconds: number } = await response.json();
        return {
            data: {
                videoId: String(data.video_id),
                positionSeconds: data.position_seconds,
            },
            success: true,
        };
    }

    async uploadVideo(file: any, title: string): Promise<ApiResponse<Lecture>> {
        if (FEATURES.enableMockData) {
            await delay(1000);
            const mockLectures = getMockLectures();
            return {
                data: buildMockLecture(title, mockLectures.length),
                success: true,
            };
        }

        const formData = new FormData();

        if (typeof window !== 'undefined' && typeof window.document !== 'undefined') {
            const blobResp = await fetch(file.uri);
            const blob = await blobResp.blob();
            formData.append('file', blob, file.name);
        } else {
            formData.append(
                'file',
                {
                    uri: file.uri,
                    name: file.name,
                    type: file.mimeType || 'video/mp4',
                } as any
            );
        }

        formData.append('title', title);

        const response = await this.request('/videos/upload', {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) {
            throw await buildApiError(response, 'Upload failed');
        }
        const backendVideo: BackendVideoResponse = await response.json();
        return {
            data: transformVideoResponse(backendVideo),
            success: true,
            message: backendVideo.from_cache
                ? 'This video is already in your library.'
                : undefined,
            fromCache: Boolean(backendVideo.from_cache),
        };
    }

    async uploadLink(url: string, title: string): Promise<ApiResponse<Lecture>> {
        if (FEATURES.enableMockData) {
            await delay(1000);
            const mockLectures = getMockLectures();
            return {
                data: buildMockLecture(title, mockLectures.length, true),
                success: true,
            };
        }

        const response = await this.request('/videos/link', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, title }),
        });
        if (!response.ok) {
            throw await buildApiError(response, 'Link import failed');
        }
        const backendVideo: BackendVideoResponse = await response.json();
        return {
            data: transformVideoResponse(backendVideo),
            success: true,
            message: backendVideo.from_cache
                ? 'This link was already processed. Using your existing lecture.'
                : undefined,
            fromCache: Boolean(backendVideo.from_cache),
        };
    }

    async getUploadStatus(lectureId: string): Promise<ApiResponse<UploadStatus>> {
        if (FEATURES.enableMockData) {
            await delay(500);
            const mockLectures = getMockLectures();
            const lecture = mockLectures.find(item => item.id === lectureId);
            const mockStage: UploadStatus['stage'] =
                lecture?.status === 'transcribing'
                    ? 'transcribing'
                    : lecture?.status === 'segmenting'
                      ? 'segmenting'
                      : lecture?.status === 'processing'
                        ? 'parallel_processing'
                        : lecture?.status === 'ready'
                          ? 'complete'
                          : null;
            const backendStatus =
                lecture?.status === 'failed'
                    ? 'failed'
                    : lecture?.status === 'ready'
                      ? 'complete'
                      : lecture?.status === 'processing'
                        ? 'extracting_slides'
                        : lecture?.status === 'transcribing'
                          ? 'transcribing'
                          : lecture?.status === 'segmenting'
                            ? 'segmenting'
                            : 'pending';
            const state = mapBackendStateToJobState(backendStatus);

            return {
                data: {
                    lectureId,
                    state,
                    stage: mockStage,
                    transcriptionStage:
                        lecture?.status === 'transcribing' ? 'transcribing' : null,
                    slidesStage:
                        lecture?.status === 'processing' ? 'extracting_slides' : null,
                    progress: getStageProgress(state, mockStage),
                    errorMessage:
                        lecture?.status === 'failed'
                            ? 'Mock processing failed for testing.'
                            : null,
                },
                success: true,
            };
        }

        const response = await this.request(`/videos/${lectureId}/status`);
        if (!response.ok) {
            throw new Error(`Status check failed (${response.status})`);
        }

        const backendStatus: BackendVideoStatusResponse = await response.json();
        return { data: transformVideoStatusResponse(backendStatus), success: true };
    }

    async cancelUpload(
        lectureId: string
    ): Promise<ApiResponse<{ lectureId: string; status: string; message: string }>> {
        if (FEATURES.enableMockData) {
            await delay(300);
            return {
                data: {
                    lectureId,
                    status: 'cancelled',
                    message: 'Processing cancelled',
                },
                success: true,
            };
        }

        const response = await this.request(`/jobs/${lectureId}/cancel`, {
            method: 'POST',
        });

        if (!response.ok) {
            throw await buildApiError(response, 'Cancel failed');
        }

        const backendResponse: BackendCancelJobResponse = await response.json();
        return {
            data: {
                lectureId: String(backendResponse.video_id),
                status: backendResponse.status,
                message: backendResponse.message,
            },
            success: true,
        };
    }

    async deleteLecture(lectureId: string): Promise<ApiResponse<DeleteLectureResponse>> {
        if (FEATURES.enableMockData) {
            await delay(300);
            return { data: { lectureId }, success: true };
        }

        const response = await this.request(`/videos/${lectureId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw await buildApiError(response, 'Delete failed');
        }

        return { data: { lectureId }, success: true };
    }

    async getTranscript(lectureId: string): Promise<ApiResponse<TranscriptSegment[]>> {
        if (FEATURES.enableMockData) {
            await delay(400);
            return { data: getMockTranscript(lectureId), success: true };
        }

        const response = await this.request(`/videos/${lectureId}/transcript`);
        if (!response.ok) {
            return { data: [], success: false, message: 'Transcript not found' };
        }
        const backendTranscript: BackendTranscriptResponse = await response.json();
        return { data: transformTranscriptResponse(backendTranscript), success: true };
    }

    async getSlides(lectureId: string): Promise<ApiResponse<SlideFrame[]>> {
        if (FEATURES.enableMockData) {
            await delay(300);
            return { data: mockSlides, success: true };
        }

        const response = await this.request(`/videos/${lectureId}/slides?limit=100`);
        if (!response.ok) {
            return { data: [], success: false, message: 'Slides not found' };
        }

        const backendSlides: BackendSlideListResponse = await response.json();
        return { data: backendSlides.slides.map(transformSlideFrame), success: true };
    }

    async getTopics(lectureId: string): Promise<ApiResponse<TopicSegment[]>> {
        if (FEATURES.enableMockData) {
            await delay(300);
            return { data: getMockTopics(lectureId), success: true };
        }

        const response = await this.request(`/videos/${lectureId}/transcript`);
        if (!response.ok) {
            return { data: [], success: false, message: 'Topics not found' };
        }
        const backendTranscript: BackendTranscriptResponse = await response.json();
        return { data: transformSegmentsToTopics(backendTranscript.segments), success: true };
    }

    async search(lectureId: string, query: string): Promise<ApiResponse<SearchResult[]>> {
        if (FEATURES.enableMockData) {
            await delay(600);
            return { data: mockSearch(query), success: true };
        }

        const response = await this.request(`/videos/${lectureId}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, mode: 'retrieval', top_k: 5 }),
        });
        if (!response.ok) {
            return { data: [], success: false, message: 'Search failed' };
        }
        const backendQuery: BackendQueryResponse = await response.json();
        const data = backendQuery.results
            ? transformSearchResponse(
                  { results: backendQuery.results, query: backendQuery.query },
                  lectureId
              )
            : [];
        return { data, success: true };
    }

    async askQuestion(lectureId: string, question: string): Promise<ApiResponse<QAResult>> {
        if (FEATURES.enableMockData) {
            await delay(800);
            return {
                data: { ...mockQAResult, question },
                success: true,
            };
        }

        const response = await this.request(`/videos/${lectureId}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: question, mode: 'qa', top_k: 5 }),
        });
        if (!response.ok) {
            return {
                data: {
                    id: '',
                    question,
                    answer: 'Could not get an answer',
                    citations: [],
                    confidence: 0,
                },
                success: false,
                message: 'QA failed',
            };
        }
        const backendQuery: BackendQueryResponse = await response.json();
        return {
            data: {
                id: String(Date.now()),
                question,
                answer: backendQuery.answer || '',
                citations: (backendQuery.citations || []).map(c => ({
                    startTime: c.start_time,
                    endTime: c.end_time,
                    text: c.text,
                    segmentTitle: c.segment_title || '',
                })),
                confidence: 0.9,
            },
            success: true,
        };
    }

    async query(
        lectureId: string,
        query: string,
        mode: 'auto' | 'retrieval' | 'qa' = 'auto'
    ): Promise<ApiResponse<QueryResult>> {
        if (FEATURES.enableMockData) {
            await delay(700);
            return { data: mockQueryResult(query, mode), success: true };
        }

        const response = await this.request(`/videos/${lectureId}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, mode, top_k: 5 }),
        });

        if (!response.ok) {
            return {
                data: { query, mode: 'retrieval', results: [] },
                success: false,
                message: 'Query failed',
            };
        }
        const backendQuery: BackendQueryResponse = await response.json();
        return { data: transformQueryResponse(backendQuery, lectureId), success: true };
    }

    async generateNotes(
        lectureId: string
    ): Promise<ApiResponse<GeneratedNotesResponse>> {
        if (FEATURES.enableMockData) {
            await delay(1200);
            return {
                data: {
                    videoId: parseInt(lectureId),
                    notes: [
                        {
                            segmentId: 1,
                            title: 'Introduction',
                            notesMarkdown:
                                'Overview of the lecture content.\n\n- **Key concept**: First important point\n- Second important point\n  - Supporting detail',
                            startTime: 0,
                            endTime: 120,
                        },
                        {
                            segmentId: 2,
                            title: 'Main Content',
                            notesMarkdown:
                                'Core material covered in this section.\n\n- **Algorithm**: Step-by-step breakdown\n- Practical application details',
                            startTime: 120,
                            endTime: 360,
                        },
                    ],
                },
                success: true,
            };
        }

        const response = await this.request(`/videos/${lectureId}/notes`);
        if (!response.ok) {
            return {
                data: { videoId: parseInt(lectureId), notes: [] },
                success: false,
                message: 'Notes generation failed',
            };
        }
        const backendNotes: BackendNotesResponse = await response.json();
        return { data: transformNotesResponse(backendNotes), success: true };
    }

    async exportNotesPDF(lectureId: string, notes: GeneratedNote[]): Promise<Blob> {
        if (FEATURES.enableMockData) {
            await delay(500);
            return new Blob(['Mock PDF content'], { type: 'application/pdf' });
        }

        const body = {
            notes: notes.map(n => ({
                segment_id: n.segmentId,
                title: n.title,
                notes_markdown: n.notesMarkdown,
                start_time: n.startTime,
                end_time: n.endTime,
            })),
        };

        const response = await this.request(`/videos/${lectureId}/notes/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw new Error(`PDF export failed (${response.status})`);
        }
        return response.blob();
    }

    async downloadSlides(lectureId: string): Promise<Blob> {
        if (FEATURES.enableMockData) {
            await delay(300);
            return new Blob(['Mock ZIP content'], { type: 'application/zip' });
        }

        const response = await this.request(`/videos/${lectureId}/slides/download`);
        if (!response.ok) {
            throw new Error(`Slides download failed (${response.status})`);
        }
        return response.blob();
    }

    getSlidePreviewUrl(lectureId: string, slideId: string): string {
        return `${this.baseUrl}/videos/${lectureId}/slides/${slideId}/preview`;
    }

    async getChatHistory(lectureId: string): Promise<ApiResponse<any[]>> {
        if (FEATURES.enableMockData) {
            return { data: [], success: true };
        }

        try {
            const response = await this.request(`/videos/${lectureId}/chat`);
            if (!response.ok) {
                return { data: [], success: false, message: 'Chat history not found' };
            }
            const messages = await response.json();
            return { data: messages, success: true };
        } catch {
            return { data: [], success: true };
        }
    }

    async saveChatHistory(lectureId: string, messages: any[]): Promise<void> {
        if (FEATURES.enableMockData) return;

        try {
            await this.request(`/videos/${lectureId}/chat`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages }),
            });
        } catch {
            // Silently fail — chat persistence is best-effort
        }
    }
}
