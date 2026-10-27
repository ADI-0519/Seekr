import { formatDuration } from '../../src/utils/formatDuration';

describe('formatDuration', () => {
    it('handles null, undefined, and NaN properly', () => {
        expect(formatDuration(null)).toBe('--:--');
        expect(formatDuration(undefined)).toBe('--:--');
        expect(formatDuration(NaN)).toBe('--:--');
    });

    it('formats 0 seconds correctly', () => {
        expect(formatDuration(0)).toBe('0:00');
    });

    it('formats seconds into MM:SS correctly', () => {
        expect(formatDuration(45)).toBe('0:45');
        expect(formatDuration(60)).toBe('1:00');
        expect(formatDuration(599)).toBe('9:59');
        expect(formatDuration(600)).toBe('10:00');
    });

    it('formats seconds into H:MM:SS correctly', () => {
        expect(formatDuration(3600)).toBe('1:00:00');
        expect(formatDuration(3665)).toBe('1:01:05');
        expect(formatDuration(7200)).toBe('2:00:00');
        expect(formatDuration(45300)).toBe('12:35:00');
    });
});
