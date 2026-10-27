import { QACitation, SearchResult } from '@/types';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    text?: string;
    citations?: QACitation[];
    results?: SearchResult[];
    mode?: 'retrieval' | 'qa';
}
