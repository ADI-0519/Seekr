import { API_BASE_URL, FEATURES } from '@/constants';
import { authService } from '../auth';

export interface RequestOptions {
    forceRefreshToken?: boolean;
    retryOn401?: boolean;
}

export type RequestFn = (
    path: string,
    init?: RequestInit,
    options?: RequestOptions
) => Promise<Response>;

function extractDetailFromJson(payload: unknown): string | null {
    if (!payload || typeof payload !== 'object') return null;
    const body = payload as Record<string, unknown>;

    const detail = body.detail;
    if (typeof detail === 'string' && detail.trim()) return detail.trim();
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string' && first.trim()) return first.trim();
        if (
            first &&
            typeof first === 'object' &&
            typeof (first as Record<string, unknown>).message === 'string'
        ) {
            return String((first as Record<string, unknown>).message).trim();
        }
    }

    if (typeof body.error === 'string' && body.error.trim()) return body.error.trim();
    return null;
}

export async function buildApiError(
    response: Response,
    fallback: string
): Promise<Error> {
    let detail = '';
    const contentType = response.headers.get('content-type') || '';

    try {
        if (contentType.includes('application/json')) {
            const jsonBody = await response.json();
            detail = extractDetailFromJson(jsonBody) || '';
        } else {
            detail = (await response.text()).trim();
        }
    } catch {
        detail = '';
    }

    const message = detail
        ? `${fallback} (${response.status}): ${detail}`
        : `${fallback} (${response.status})`;
    return new Error(message);
}

export class ApiHttpClient {
    readonly baseUrl = `${API_BASE_URL}/api`;

    private async buildHeaders(
        headers?: HeadersInit,
        options: RequestOptions = {}
    ): Promise<Headers> {
        const requestHeaders = new Headers(headers);

        if (!FEATURES.enableMockAuth) {
            const token = await authService.getIdToken(Boolean(options.forceRefreshToken));
            if (token) {
                requestHeaders.set('Authorization', `Bearer ${token}`);
            }
        }

        return requestHeaders;
    }

    request: RequestFn = async (path, init = {}, options = {}) => {
        const headers = await this.buildHeaders(init.headers, options);
        const url = `${this.baseUrl}${path}`;
        let response = await fetch(url, { ...init, headers });

        if (
            response.status === 401 &&
            !FEATURES.enableMockAuth &&
            options.retryOn401 !== false &&
            authService.getCurrentUser()
        ) {
            const retryHeaders = await this.buildHeaders(init.headers, {
                ...options,
                forceRefreshToken: true,
            });
            response = await fetch(url, { ...init, headers: retryHeaders });
        }

        return response;
    };
}
