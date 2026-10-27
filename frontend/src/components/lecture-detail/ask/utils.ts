import { SearchResult } from '@/types';

export type AnswerPart = { kind: 'text'; content: string } | { kind: 'cite'; n: number };

export function parseAnswerParts(text: string): AnswerPart[] {
    const parts: AnswerPart[] = [];
    let cursor = 0;
    const re = /\[(\d+)\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
        if (m.index > cursor) parts.push({ kind: 'text', content: text.slice(cursor, m.index) });
        parts.push({ kind: 'cite', n: parseInt(m[1], 10) });
        cursor = m.index + m[0].length;
    }
    if (cursor < text.length) parts.push({ kind: 'text', content: text.slice(cursor) });
    return parts;
}

export function dedupeByProximity(results: SearchResult[], windowSecs = 15): SearchResult[] {
    const kept: SearchResult[] = [];
    for (const r of results) {
        if (!kept.some((k) => Math.abs(k.timestamp - r.timestamp) < windowSecs)) {
            kept.push(r);
        }
    }
    return kept;
}
