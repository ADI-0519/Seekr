export const typography = {
    fontFamily: {
        regular: 'PlusJakartaSans_500Medium',
        medium: 'PlusJakartaSans_500Medium',
        semibold: 'PlusJakartaSans_600SemiBold',
        bold: 'PlusJakartaSans_700Bold',
    },
    sizes: {
        displayLg: { fontSize: 40, lineHeight: 44, letterSpacing: -0.5 },
        displayMd: { fontSize: 32, lineHeight: 36, letterSpacing: -0.5 },
        headingXl: { fontSize: 28, lineHeight: 34, letterSpacing: -0.5 },
        headingLg: { fontSize: 24, lineHeight: 30, letterSpacing: -0.25 },
        headingMd: { fontSize: 20, lineHeight: 26, letterSpacing: -0.25 },
        headingSm: { fontSize: 18, lineHeight: 24, letterSpacing: 0 },
        bodyLg: { fontSize: 16, lineHeight: 24, letterSpacing: 0 },
        bodyMd: { fontSize: 14, lineHeight: 22, letterSpacing: 0 },
        bodySm: { fontSize: 13, lineHeight: 20, letterSpacing: 0 },
        meta: { fontSize: 12, lineHeight: 16, letterSpacing: 0.1 },
        chip: { fontSize: 11, lineHeight: 14, letterSpacing: 0.2 },
    },
    weights: {
        displayLg: '700',
        displayMd: '700',
        headingXl: '700',
        headingLg: '700',
        headingMd: '600',
        headingSm: '600',
        bodyLg: '500',
        bodyMd: '500',
        bodySm: '500',
        meta: '500',
        chip: '600',
    }
} as const;

export type TypographyVariant = keyof typeof typography.sizes;
