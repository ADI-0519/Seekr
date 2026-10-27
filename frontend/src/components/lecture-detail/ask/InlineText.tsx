import { Platform, Text } from 'react-native';

type Part = { content: string; bold: boolean; code: boolean; sub: boolean; sup: boolean };

const splitScripts = (s: string, bold: boolean, code: boolean): Part[] => {
    const result: Part[] = [];
    const re = /(_\{[^}]+\}|\^\{[^}]+\}|_[A-Za-z0-9]|\^[A-Za-z0-9])/g;
    let cursor = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s)) !== null) {
        if (m.index > cursor) {
            result.push({ content: s.slice(cursor, m.index), bold, code, sub: false, sup: false });
        }
        const raw = m[0];
        if (raw.startsWith('_{')) {
            result.push({ content: raw.slice(2, -1), bold, code, sub: true, sup: false });
        } else if (raw.startsWith('^{')) {
            result.push({ content: raw.slice(2, -1), bold, code, sub: false, sup: true });
        } else if (raw.startsWith('_')) {
            result.push({ content: raw.slice(1), bold, code, sub: true, sup: false });
        } else {
            result.push({ content: raw.slice(1), bold, code, sub: false, sup: true });
        }
        cursor = m.index + raw.length;
    }
    if (cursor < s.length) {
        result.push({ content: s.slice(cursor), bold, code, sub: false, sup: false });
    }
    return result;
};

export const InlineText = ({ text, baseColor }: { text: string; baseColor: string }) => {
    const parts: Part[] = [];
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let last = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(text)) !== null) {
        if (match.index > last) {
            parts.push(...splitScripts(text.slice(last, match.index), false, false));
        }
        const raw = match[0];
        if (raw.startsWith('**')) {
            parts.push(...splitScripts(raw.slice(2, -2), true, false));
        } else {
            parts.push({ content: raw.slice(1, -1), bold: false, code: true, sub: false, sup: false });
        }
        last = match.index + raw.length;
    }
    if (last < text.length) {
        parts.push(...splitScripts(text.slice(last), false, false));
    }

    return (
        <Text>
            {parts.map((p, i) => (
                <Text
                    key={i}
                    style={[
                        {
                            fontWeight: p.bold ? '700' : '400',
                            fontFamily: p.code ? 'monospace' : undefined,
                            color: baseColor,
                            fontSize: p.sub || p.sup ? 11 : 15,
                            lineHeight: 24,
                        },
                        Platform.OS === 'web' && p.sup ? ({ verticalAlign: 'super', fontSize: 10 } as any) : null,
                        Platform.OS === 'web' && p.sub ? ({ verticalAlign: 'sub', fontSize: 10 } as any) : null,
                        Platform.OS !== 'web' && p.sup ? ({ lineHeight: 18, marginBottom: 4 } as any) : null,
                        Platform.OS !== 'web' && p.sub ? ({ lineHeight: 28 } as any) : null,
                    ]}
                >
                    {p.content}
                </Text>
            ))}
        </Text>
    );
};
