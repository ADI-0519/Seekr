import { Lecture, UploadJobState, UploadStage, UploadStatus } from '@/types';

export interface BackendVideoStatusResponse {
    id: number;
    status: string;
    current_stage: string | null;
    transcription_stage: string | null;
    slides_stage: string | null;
    error_message: string | null;
}

export const UPLOAD_STAGE_PROGRESS: Record<UploadStage, number> = {
    extracting_audio: 10,
    parallel_processing: 30,
    transcribing: 40,
    extracting_slides: 55,
    segmenting: 70,
    summarising: 80,
    embedding: 95,
    complete: 100,
};

export function mapProcessingStatus(status: string): Lecture['status'] {
    const statusMap: Record<string, Lecture['status']> = {
        pending: 'processing',
        extracting_audio: 'processing',
        transcribing: 'transcribing',
        extracting_slides: 'processing',
        segmenting: 'segmenting',
        summarising: 'processing',
        embedding: 'processing',
        complete: 'ready',
        failed: 'failed',
    };

    return statusMap[status] || 'processing';
}

export function mapBackendStateToJobState(status: string): UploadJobState {
    if (status === 'failed') return 'failed';
    if (status === 'complete') return 'done';
    if (status === 'pending') return 'queued';
    return 'running';
}

export function getStageProgress(state: UploadJobState, stage: UploadStage | null): number {
    if (state === 'queued') return 5;
    if (state === 'done' || state === 'failed') return 100;

    return stage ? UPLOAD_STAGE_PROGRESS[stage] || 20 : 20;
}

export function transformVideoStatusResponse(backend: BackendVideoStatusResponse): UploadStatus {
    const state = mapBackendStateToJobState(backend.status);
    const stage = backend.current_stage as UploadStage | null;

    return {
        lectureId: String(backend.id),
        state,
        stage,
        transcriptionStage: backend.transcription_stage,
        slidesStage: backend.slides_stage,
        progress: getStageProgress(state, stage),
        errorMessage: backend.error_message,
    };
}
