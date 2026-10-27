import { Platform } from 'react-native';

import { motion } from '../../src/design/tokens/motion';
import { getResponsiveGridItemStyle, getWebStaggerStyle } from '../../src/utils/responsiveGrid';

describe('responsiveGrid utils', () => {
    const originalPlatform = Platform.OS;

    function setPlatform(next: 'ios' | 'android' | 'web') {
        Object.defineProperty(Platform, 'OS', {
            value: next,
        });
    }

    afterEach(() => {
        setPlatform(originalPlatform as 'ios' | 'android' | 'web');
    });

    it('returns 100% flex-basis on native', () => {
        setPlatform('ios');

        expect(getResponsiveGridItemStyle({ gridCols: 3 })).toEqual({
            flexBasis: '100%',
            minWidth: 280,
        });
    });

    it('returns calculated width on web', () => {
        setPlatform('web');

        expect(
            getResponsiveGridItemStyle({
                gridCols: 2,
                gapPx: 20,
                minWidthPx: 260,
            })
        ).toEqual({
            width: 'calc(50% - 10px)',
            minWidth: 260,
        });
    });

    it('returns empty stagger style on native', () => {
        setPlatform('android');

        expect(
            getWebStaggerStyle({
                index: 0,
                maxAnimatedItems: 3,
            })
        ).toEqual({});
    });

    it('returns empty stagger style when index is outside animation range', () => {
        setPlatform('web');

        expect(
            getWebStaggerStyle({
                index: 5,
                maxAnimatedItems: 3,
            })
        ).toEqual({});
    });

    it('returns full stagger style when enabled for web', () => {
        setPlatform('web');

        expect(
            getWebStaggerStyle({
                index: 2,
                maxAnimatedItems: 5,
                includeInitialOpacity: true,
                fillMode: 'both',
            })
        ).toEqual({
            opacity: 0,
            transform: `translateY(${motion.shellOffsetY}px)`,
            animation: `cardStaggerIn ${motion.durationPage}ms ${motion.easeOut} ${2 * motion.staggerInterval}ms both`,
        });
    });
});
