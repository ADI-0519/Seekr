import { colors } from './tokens/colors';
import { spacing } from './tokens/spacing';
import { radii } from './tokens/radii';
import { shadows } from './tokens/shadows';
import { typography } from './tokens/typography';
import { motion } from './tokens/motion';
import { breakpoints } from './tokens/breakpoints';

export const theme = {
    colors,
    spacing,
    radii,
    shadows,
    typography,
    motion,
    breakpoints,
};

export type Theme = typeof theme;
