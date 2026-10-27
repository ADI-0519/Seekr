import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { FEATURES } from '@/constants';
import { Lecture } from '@/types';

const STORAGE_KEY = 'seekr_processing_dock_overrides_v2';
const PROCESSING_STATUSES: Lecture['status'][] = ['processing', 'transcribing', 'segmenting'];

export interface LectureStatusOverride {
    status: 'ready' | 'failed';
    observedAt: number;
}

interface LectureStatusStore {
    overrides: Record<string, LectureStatusOverride>;
    hydrated: boolean;
    hydrate: () => Promise<void>;
    setOverride: (lectureId: string, status: 'ready' | 'failed', observedAt?: number) => void;
    pruneOverrides: (lectures: Lecture[]) => void;
}

function pruneAgainstLectures(
    overrides: Record<string, LectureStatusOverride>,
    lectures: Lecture[],
) {
    if (FEATURES.enableMockData) {
        return {};
    }

    const lecturesById = new Map(lectures.map((lecture) => [lecture.id, lecture]));

    return Object.fromEntries(
        Object.entries(overrides).filter(([lectureId, override]) => {
            const lecture = lecturesById.get(lectureId);
            if (!lecture) return false;
            return PROCESSING_STATUSES.includes(lecture.status) && lecture.status !== override.status;
        }),
    ) as Record<string, LectureStatusOverride>;
}

let hydrationPromise: Promise<void> | null = null;

export const useLectureStatusStore = create<LectureStatusStore>((set, get) => ({
    overrides: {},
    hydrated: false,

    hydrate: async () => {
        if (get().hydrated) return;
        if (hydrationPromise) return hydrationPromise;

        hydrationPromise = AsyncStorage.getItem(STORAGE_KEY)
            .then((raw) => {
                if (!raw) return;
                try {
                    set({ overrides: JSON.parse(raw) });
                } catch {
                    set({ overrides: {} });
                }
            })
            .finally(() => {
                set({ hydrated: true });
                hydrationPromise = null;
            });

        return hydrationPromise;
    },

    setOverride: (lectureId, status, observedAt = Date.now()) => {
        if (FEATURES.enableMockData) {
            return;
        }

        set((state) => {
            const next = {
                ...state.overrides,
                [lectureId]: {
                    status,
                    observedAt,
                },
            };
            AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => { });
            return { overrides: next };
        });
    },

    pruneOverrides: (lectures) => {
        set((state) => {
            const next = pruneAgainstLectures(state.overrides, lectures);
            AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => { });
            return { overrides: next };
        });
    },
}));

export function getEffectiveLectureStatus(
    lecture: Lecture,
    overrides: Record<string, LectureStatusOverride>,
): Lecture['status'] {
    if (FEATURES.enableMockData) return lecture.status;

    const override = overrides[lecture.id];
    if (!override) return lecture.status;
    if (!PROCESSING_STATUSES.includes(lecture.status)) return lecture.status;
    return override.status;
}

export function applyEffectiveLectureStatus(
    lecture: Lecture,
    overrides: Record<string, LectureStatusOverride>,
): Lecture {
    const effectiveStatus = getEffectiveLectureStatus(lecture, overrides);
    return effectiveStatus === lecture.status ? lecture : { ...lecture, status: effectiveStatus };
}
