import {
    UPLOAD_STAGE_PROGRESS,
    getStageProgress,
    mapBackendStateToJobState,
    mapProcessingStatus,
    transformVideoStatusResponse,
} from '../../src/services/uploadStatus';

describe('Upload Status Service', () => {
    it('maps backend video statuses into lecture statuses', () => {
        expect(mapProcessingStatus('pending')).toBe('processing');
        expect(mapProcessingStatus('transcribing')).toBe('transcribing');
        expect(mapProcessingStatus('segmenting')).toBe('segmenting');
        expect(mapProcessingStatus('summarising')).toBe('processing');
        expect(mapProcessingStatus('complete')).toBe('ready');
        expect(mapProcessingStatus('failed')).toBe('failed');
    });

    it('covers queued, running, failed, and done job states', () => {
        expect(mapBackendStateToJobState('pending')).toBe('queued');
        expect(mapBackendStateToJobState('transcribing')).toBe('running');
        expect(mapBackendStateToJobState('failed')).toBe('failed');
        expect(mapBackendStateToJobState('complete')).toBe('done');
    });

    it('uses a single stage progress mapping for running stages', () => {
        expect(UPLOAD_STAGE_PROGRESS.extracting_audio).toBe(10);
        expect(UPLOAD_STAGE_PROGRESS.transcribing).toBe(40);
        expect(UPLOAD_STAGE_PROGRESS.extracting_slides).toBe(55);
        expect(UPLOAD_STAGE_PROGRESS.segmenting).toBe(70);
        expect(UPLOAD_STAGE_PROGRESS.summarising).toBe(80);
        expect(UPLOAD_STAGE_PROGRESS.embedding).toBe(95);
        expect(UPLOAD_STAGE_PROGRESS.complete).toBe(100);
    });

    it('returns terminal progress for failed and done states', () => {
        expect(getStageProgress('failed', 'embedding')).toBe(100);
        expect(getStageProgress('done', 'complete')).toBe(100);
        expect(getStageProgress('queued', null)).toBe(5);
    });

    it('transforms backend status responses into upload status shape', () => {
        expect(
            transformVideoStatusResponse({
                id: 42,
                status: 'pending',
                current_stage: null,
                transcription_stage: null,
                slides_stage: null,
                error_message: null,
            })
        ).toEqual({
            lectureId: '42',
            state: 'queued',
            stage: null,
            transcriptionStage: null,
            slidesStage: null,
            progress: 5,
            errorMessage: null,
        });

        expect(
            transformVideoStatusResponse({
                id: 42,
                status: 'transcribing',
                current_stage: 'transcribing',
                transcription_stage: 'transcribing',
                slides_stage: 'processing',
                error_message: null,
            })
        ).toEqual({
            lectureId: '42',
            state: 'running',
            stage: 'transcribing',
            transcriptionStage: 'transcribing',
            slidesStage: 'processing',
            progress: 40,
            errorMessage: null,
        });

        expect(
            transformVideoStatusResponse({
                id: 42,
                status: 'failed',
                current_stage: 'embedding',
                transcription_stage: 'failed',
                slides_stage: 'failed',
                error_message: 'boom',
            })
        ).toEqual({
            lectureId: '42',
            state: 'failed',
            stage: 'embedding',
            transcriptionStage: 'failed',
            slidesStage: 'failed',
            progress: 100,
            errorMessage: 'boom',
        });

        expect(
            transformVideoStatusResponse({
                id: 42,
                status: 'complete',
                current_stage: 'complete',
                transcription_stage: 'complete',
                slides_stage: 'complete',
                error_message: null,
            })
        ).toEqual({
            lectureId: '42',
            state: 'done',
            stage: 'complete',
            transcriptionStage: 'complete',
            slidesStage: 'complete',
            progress: 100,
            errorMessage: null,
        });
    });
});
