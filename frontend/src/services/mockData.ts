import { Lecture, TranscriptSegment, TopicSegment, SearchResult, QAResult } from '@/types';

const VIDEOS = [
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4',
    'http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
];

const THUMBNAILS = [
    'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400',
    'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=400',
    'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400',
    'https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=400',
    'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=400',
    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400',
    'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400',
    'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=400',
    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400',
    'https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=400',
];

type LectureSeed = Omit<Lecture, 'overview' | 'thumbnailUrl' | 'videoUrl'>;
type TopicTemplate = Omit<TopicSegment, 'title'> & { baseTitle: string };

const LECTURE_SEEDS: LectureSeed[] = [
    {
        id: '1',
        title: 'Introduction to Machine Learning',
        description: 'An overview of ML concepts, supervised vs unsupervised learning, and common algorithms.',
        duration: 596,
        status: 'ready',
        createdAt: '2024-03-01T10:00:00Z',
        updatedAt: '2024-03-01T12:00:00Z',
        userId: 'user1',
    },
    {
        id: '2',
        title: 'Data Structures: Trees and Graphs',
        description: 'Understanding binary trees, BSTs, graph representations, and traversal algorithms.',
        duration: 653,
        status: 'ready',
        createdAt: '2024-03-02T14:00:00Z',
        updatedAt: '2024-03-02T16:00:00Z',
        userId: 'user1',
    },
    {
        id: '3',
        title: 'Neural Networks Deep Dive',
        description: 'Backpropagation, activation functions, and building your first neural network.',
        duration: 15,
        status: 'ready',
        createdAt: '2024-03-03T09:00:00Z',
        updatedAt: '2024-03-03T09:30:00Z',
        userId: 'user1',
    },
    {
        id: '4',
        title: 'Advanced React Patterns',
        description: 'Higher-order components, render props, and custom hooks in depth.',
        duration: 15,
        status: 'processing',
        createdAt: '2024-03-04T10:00:00Z',
        updatedAt: '2024-03-04T10:15:00Z',
        userId: 'user1',
    },
    {
        id: '5',
        title: 'Docker for Backend Mastery',
        description: 'Containerizing applications, docker-compose, and deployment strategies.',
        duration: 61,
        status: 'ready',
        createdAt: '2024-03-05T08:00:00Z',
        updatedAt: '2024-03-05T08:45:00Z',
        userId: 'user1',
    },
    {
        id: '6',
        title: 'System Design Interview Prep',
        description: 'Scalability, microservices, load balancing, and database sharding.',
        duration: 15,
        status: 'ready',
        createdAt: '2024-03-06T11:00:00Z',
        updatedAt: '2024-03-06T12:00:00Z',
        userId: 'user1',
    },
    {
        id: '7',
        title: 'The Future of AI Hardware',
        description: 'GPUs, TPUs, and the silicon pushing the boundaries of artificial intelligence.',
        duration: 15,
        status: 'failed',
        createdAt: '2024-03-06T13:00:00Z',
        updatedAt: '2024-03-06T13:05:00Z',
        userId: 'user1',
    },
    {
        id: '8',
        title: 'Sintel: Open Movie Project',
        description: 'Independent short film independently produced by the Blender Foundation.',
        duration: 888,
        status: 'ready',
        createdAt: '2024-03-06T14:00:00Z',
        updatedAt: '2024-03-06T15:00:00Z',
        userId: 'user1',
    },
    {
        id: '9',
        title: 'Subaru Outreach on Street and Dirt',
        description: 'Promotional video showcasing vehicle capabilities in various conditions.',
        duration: 59,
        status: 'ready',
        createdAt: '2024-03-06T15:30:00Z',
        updatedAt: '2024-03-06T16:00:00Z',
        userId: 'user1',
    },
    {
        id: '10',
        title: 'Tears of Steel: VFX Breakdown',
        description: 'Short sci-fi film crowd-funded by users of the open source 3D creation tool Blender.',
        duration: 734,
        status: 'ready',
        createdAt: '2024-03-06T16:00:00Z',
        updatedAt: '2024-03-06T17:00:00Z',
        userId: 'user1',
    },
];

const TRANSCRIPT_TAIL: TranscriptSegment[] = [
    {
        id: 'seg2',
        text: 'We will be breaking down the core principles into manageable chunks so you can follow along easily.',
        startTime: 8,
        endTime: 16,
        words: [],
    },
    {
        id: 'seg3',
        text: 'Let us dive into the first main section. Pay close attention to the diagrams shown on screen.',
        startTime: 16,
        endTime: 24,
        words: [],
    },
    {
        id: 'seg4',
        text: 'Now, moving on to the advanced application of these concepts. This is where it gets interesting.',
        startTime: 24,
        endTime: 32,
        words: [],
    },
    {
        id: 'seg5',
        text: 'Finally, to summarize what we have learned today: practice is key to mastering these techniques.',
        startTime: 32,
        endTime: 45,
        words: [],
    },
    {
        id: 'seg6',
        text: 'Thank you for watching, and make sure to review the provided notes before the next session.',
        startTime: 45,
        endTime: 60,
        words: [],
    },
];

const TOPIC_TEMPLATES: TopicTemplate[] = [
    {
        id: 'topic1',
        baseTitle: 'Introduction & Basics',
        summary: 'Overview of the fundamental concepts discussed in the first half of the lecture.',
        startTime: 0,
        endTime: 24,
        transcriptSegmentIds: ['seg1', 'seg2', 'seg3'],
    },
    {
        id: 'topic2',
        baseTitle: 'Advanced Concepts & Conclusion',
        summary: 'Deep dive into advanced topics, followed by a summary of the entire session.',
        startTime: 24,
        endTime: 60,
        transcriptSegmentIds: ['seg4', 'seg5', 'seg6'],
    },
];

export function getMockVideoUrl(index: number): string {
    const safeIndex = Number.isFinite(index) ? Math.abs(Math.trunc(index)) : 0;
    return VIDEOS[safeIndex % VIDEOS.length];
}

export function getMockLectures(): Lecture[] {
    return mockLectures.map((lecture) => ({ ...lecture }));
}

export const mockLectures: Lecture[] = LECTURE_SEEDS.map((lecture, index) => ({
    ...lecture,
    overview: null,
    thumbnailUrl: THUMBNAILS[index % THUMBNAILS.length],
    videoUrl: getMockVideoUrl(index),
}));

function createIntroSegment(lectureId: string): TranscriptSegment {
    return {
        id: 'seg1',
        text: `Welcome to lecture ${lectureId}. In this introduction, we'll establish the foundational concepts for today's topic.`,
        startTime: 0,
        endTime: 8,
        words: [
            { word: 'Welcome', start: 0, end: 0.5, confidence: 0.98 },
            { word: 'to', start: 0.5, end: 0.7, confidence: 0.99 },
            { word: 'lecture', start: 0.7, end: 1.2, confidence: 0.97 },
            { word: lectureId, start: 1.2, end: 1.5, confidence: 0.96 },
            { word: 'In', start: 1.5, end: 1.7, confidence: 0.99 },
            { word: 'this', start: 1.7, end: 2.2, confidence: 0.98 },
            { word: 'introduction...', start: 2.2, end: 2.8, confidence: 0.97 },
        ],
    };
}

export const getMockTranscript = (lectureId: string): TranscriptSegment[] => {
    return [
        createIntroSegment(lectureId),
        ...TRANSCRIPT_TAIL.map((segment) => ({
            ...segment,
            words: segment.words.map((word) => ({ ...word })),
        })),
    ];
};

export const mockTranscript = getMockTranscript('1');

export const getMockTopics = (lectureId: string): TopicSegment[] =>
    TOPIC_TEMPLATES.map(({ baseTitle, ...topic }) => ({
        ...topic,
        title: `${baseTitle} (${lectureId})`,
        transcriptSegmentIds: [...topic.transcriptSegmentIds],
    }));

export const mockTopics = getMockTopics('1');

export const mockSearchResults: SearchResult[] = [
    {
        id: 'sr1',
        lectureId: '1',
        timestamp: 8,
        text: 'breaking down the core principles into manageable chunks',
        relevanceScore: 0.95,
        context: 'Discussion of foundational elements',
    },
    {
        id: 'sr2',
        lectureId: '1',
        timestamp: 24,
        text: 'advanced application of these concepts',
        relevanceScore: 0.82,
        context: 'Transitioning to advanced topics',
    },
];

export const mockQAResult: QAResult = {
    id: 'qa1',
    question: 'What are the main topics covered?',
    answer: 'The lecture covers foundational concepts first, then moves into advanced applications and concludes with a summary.',
    citations: [
        { startTime: 8, endTime: 16, text: 'We will be breaking down the core principles into manageable chunks', segmentTitle: 'Introduction & Basics' },
        { startTime: 24, endTime: 32, text: 'Now, moving on to the advanced application of these concepts.', segmentTitle: 'Advanced Concepts & Conclusion' },
    ],
    confidence: 0.89,
};
