import { ApiResponse, ProfileSummary, UserSettings } from '@/types';
import { RequestFn } from './http';
import {
    BackendProfileSummaryResponse,
    BackendProfileSyncResponse,
    BackendUserSettingsResponse,
    FEATURES,
    SyncProfileRequest,
    UserSettingsUpdateRequest,
    buildMockProfileSummary,
    transformProfileSummaryResponse,
    transformUserSettingsResponse,
} from './shared';

export class UserApi {
    constructor(private readonly request: RequestFn) {}

    async getProfileSummary(): Promise<ApiResponse<ProfileSummary>> {
        if (FEATURES.enableMockData) {
            return buildMockProfileSummary();
        }

        const response = await this.request('/profile/me');
        if (!response.ok) {
            throw new Error(`Profile summary failed (${response.status})`);
        }

        const backendSummary: BackendProfileSummaryResponse = await response.json();
        return { data: transformProfileSummaryResponse(backendSummary), success: true };
    }

    async syncMyProfile(
        profile: SyncProfileRequest
    ): Promise<ApiResponse<BackendProfileSyncResponse>> {
        if (FEATURES.enableMockData) {
            return {
                data: {
                    uid: 'mock-user-1',
                    email: 'demo@seekr.app',
                    display_name: profile.displayName ?? 'Demo User',
                    photo_url: profile.photoURL ?? null,
                    provider: 'mock',
                    last_login_at: new Date().toISOString(),
                },
                success: true,
            };
        }

        const response = await this.request(
            '/profile/me',
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    display_name: profile.displayName ?? null,
                    photo_url: profile.photoURL ?? null,
                }),
            },
            { forceRefreshToken: true }
        );

        if (!response.ok) {
            throw new Error(`Profile sync failed (${response.status})`);
        }

        const data: BackendProfileSyncResponse = await response.json();
        return { data, success: true };
    }

    async getUserSettings(): Promise<ApiResponse<UserSettings>> {
        if (FEATURES.enableMockData) {
            return {
                data: {
                    themeMode: 'light',
                    backgroundMode: 'animated',
                    cardStyle: 'solid',
                    videoAnimation: 1,
                    autoplayNext: true,
                    pauseOnLeave: true,
                    volumeDefault: 1,
                    mutedDefault: false,
                    preferredLanguage: 'en',
                    timezone: null,
                },
                success: true,
            };
        }

        const response = await this.request('/profile/settings');
        if (!response.ok) {
            throw new Error(`Settings fetch failed (${response.status})`);
        }

        const data: BackendUserSettingsResponse = await response.json();
        return { data: transformUserSettingsResponse(data), success: true };
    }

    async updateUserSettings(
        payload: UserSettingsUpdateRequest
    ): Promise<ApiResponse<UserSettings>> {
        if (FEATURES.enableMockData) {
            return { data: payload, success: true };
        }

        const response = await this.request('/profile/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                theme_mode: payload.themeMode,
                background_mode: payload.backgroundMode,
                card_style: payload.cardStyle,
                video_animation: payload.videoAnimation,
                autoplay_next: payload.autoplayNext,
                pause_on_leave: payload.pauseOnLeave,
                volume_default: payload.volumeDefault,
                muted_default: payload.mutedDefault,
                preferred_language: payload.preferredLanguage,
                timezone: payload.timezone,
            }),
        });

        if (!response.ok) {
            throw new Error(`Settings update failed (${response.status})`);
        }

        const data: BackendUserSettingsResponse = await response.json();
        return { data: transformUserSettingsResponse(data), success: true };
    }
}
