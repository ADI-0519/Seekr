import { ApiResponse, GeneratedNote, GeneratedNotesResponse, Lecture, PaginatedResponse, ProfileSummary, QAResult, QueryResult, SearchResult, SlideFrame, TopicSegment, TranscriptSegment, UploadStatus, UserSettings } from '@/types';
import { ApiHttpClient } from './http';
import { LecturesApi } from './lectures';
import { BackendProfileSyncResponse, SyncProfileRequest, UserSettingsUpdateRequest, DeleteLectureResponse } from './shared';
import { UserApi } from './user';

export class ApiService {
    private readonly http = new ApiHttpClient();
    private readonly lectures = new LecturesApi(this.http.request, this.http.baseUrl);
    private readonly user = new UserApi(this.http.request);

    getLectures(): Promise<PaginatedResponse<Lecture>> {
        return this.lectures.getLectures();
    }

    getLecture(id: string): Promise<ApiResponse<Lecture>> {
        return this.lectures.getLecture(id);
    }

    updateLecturePlaybackPosition(
        lectureId: string,
        positionSeconds: number
    ): Promise<ApiResponse<{ videoId: string; positionSeconds: number }>> {
        return this.lectures.updateLecturePlaybackPosition(lectureId, positionSeconds);
    }

    uploadVideo(file: any, title: string): Promise<ApiResponse<Lecture>> {
        return this.lectures.uploadVideo(file, title);
    }

    uploadLink(url: string, title: string): Promise<ApiResponse<Lecture>> {
        return this.lectures.uploadLink(url, title);
    }

    getUploadStatus(lectureId: string): Promise<ApiResponse<UploadStatus>> {
        return this.lectures.getUploadStatus(lectureId);
    }

    cancelUpload(
        lectureId: string
    ): Promise<ApiResponse<{ lectureId: string; status: string; message: string }>> {
        return this.lectures.cancelUpload(lectureId);
    }

    deleteLecture(lectureId: string): Promise<ApiResponse<DeleteLectureResponse>> {
        return this.lectures.deleteLecture(lectureId);
    }

    getTranscript(lectureId: string): Promise<ApiResponse<TranscriptSegment[]>> {
        return this.lectures.getTranscript(lectureId);
    }

    getSlides(lectureId: string): Promise<ApiResponse<SlideFrame[]>> {
        return this.lectures.getSlides(lectureId);
    }

    getTopics(lectureId: string): Promise<ApiResponse<TopicSegment[]>> {
        return this.lectures.getTopics(lectureId);
    }

    search(lectureId: string, query: string): Promise<ApiResponse<SearchResult[]>> {
        return this.lectures.search(lectureId, query);
    }

    askQuestion(lectureId: string, question: string): Promise<ApiResponse<QAResult>> {
        return this.lectures.askQuestion(lectureId, question);
    }

    query(
        lectureId: string,
        query: string,
        mode: 'auto' | 'retrieval' | 'qa' = 'auto'
    ): Promise<ApiResponse<QueryResult>> {
        return this.lectures.query(lectureId, query, mode);
    }

    generateNotes(lectureId: string): Promise<ApiResponse<GeneratedNotesResponse>> {
        return this.lectures.generateNotes(lectureId);
    }

    exportNotesPDF(lectureId: string, notes: GeneratedNote[]): Promise<Blob> {
        return this.lectures.exportNotesPDF(lectureId, notes);
    }

    downloadSlides(lectureId: string): Promise<Blob> {
        return this.lectures.downloadSlides(lectureId);
    }

    getSlidePreviewUrl(lectureId: string, slideId: string): string {
        return this.lectures.getSlidePreviewUrl(lectureId, slideId);
    }

    getChatHistory(lectureId: string): Promise<ApiResponse<any[]>> {
        return this.lectures.getChatHistory(lectureId);
    }

    saveChatHistory(lectureId: string, messages: any[]): Promise<void> {
        return this.lectures.saveChatHistory(lectureId, messages);
    }

    getProfileSummary(): Promise<ApiResponse<ProfileSummary>> {
        return this.user.getProfileSummary();
    }

    syncMyProfile(
        profile: SyncProfileRequest
    ): Promise<ApiResponse<BackendProfileSyncResponse>> {
        return this.user.syncMyProfile(profile);
    }

    getUserSettings(): Promise<ApiResponse<UserSettings>> {
        return this.user.getUserSettings();
    }

    updateUserSettings(payload: UserSettingsUpdateRequest): Promise<ApiResponse<UserSettings>> {
        return this.user.updateUserSettings(payload);
    }
}
