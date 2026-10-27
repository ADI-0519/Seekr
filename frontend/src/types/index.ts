export interface User {
    id: string;
    email: string;
    displayName: string | null;
    photoURL: string | null;
    createdAt: string;
}

export interface Lecture {
    id: string;
    title: string;
    description: string;
    overview: string | null;
    duration: number;
    thumbnailUrl: string;
    videoUrl: string;
    resumePosition?: number;
    status: 'processing' | 'transcribing' | 'segmenting' | 'ready' | 'failed';
    createdAt: string;
    updatedAt: string;
    userId: string;
}

export interface TranscriptWord {
    word: string;
    start: number;
    end: number;
    confidence: number;
}

export interface TranscriptSegment {
    id: string;
    text: string;
    startTime: number;
    endTime: number;
    words: TranscriptWord[];
}

export interface TopicSegment {
    id: string;
    title: string;
    summary: string;
    startTime: number;
    endTime: number;
    transcriptSegmentIds: string[];
}

export interface SearchResult {
    id: string;
    lectureId: string;
    timestamp: number;
    text: string;
    relevanceScore: number;
    context: string;
}

export interface QACitation {
    startTime: number;
    endTime: number;
    text: string;
    segmentTitle: string;
}

export interface QAResult {
    id: string;
    question: string;
    answer: string;
    citations: QACitation[];
    confidence: number;
}

export interface QueryResult {
    query: string;
    mode: 'retrieval' | 'qa';
    results?: SearchResult[];
    answer?: string;
    citations?: QACitation[];
}

export interface GeneratedNote {
    segmentId: number;
    title: string;
    notesMarkdown: string;
    startTime: number;
    endTime: number;
}

export interface GeneratedNotesResponse {
    videoId: number;
    notes: GeneratedNote[];
}

export interface ApiResponse<T> {
    data: T;
    success: boolean;
    message?: string;
    fromCache?: boolean;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
}

export type UploadJobState = 'queued' | 'running' | 'failed' | 'done';
export type UploadStage =
    | 'extracting_audio'
    | 'parallel_processing'
    | 'transcribing'
    | 'extracting_slides'
    | 'segmenting'
    | 'summarising'
    | 'embedding'
    | 'complete';

export interface UploadStatus {
    lectureId: string;
    state: UploadJobState;
    stage: UploadStage | null;
    transcriptionStage: string | null;
    slidesStage: string | null;
    progress: number;
    errorMessage: string | null;
}

export interface SlideFrame {
    id: string;
    startTime: number;
    endTime: number;
    ocrText: string | null;
    frameUrl: string | null;
}

export interface ProfileRecentUpload {
    id: string;
    title: string;
    status: Lecture['status'];
    createdAt: string;
    duration: number;
}

export interface ProfileSummary {
    lectureCount: number;
    readyLectureCount: number;
    processingLectureCount: number;
    failedLectureCount: number;
    totalDurationSeconds: number;
    recentUploads: ProfileRecentUpload[];
}

export interface UserSettings {
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
