import { useState, useEffect } from 'react';
import { Dimensions, ScaledSize } from 'react-native';
import { Breakpoint, breakpoints } from '../design/tokens/breakpoints';

const getBreakpoint = (width: number): Breakpoint => {
    if (width < breakpoints.sm) return 'sm';
    if (width < breakpoints.md) return 'md';
    if (width < breakpoints.lg) return 'lg';
    return 'xl';
};

export const useBreakpoint = (): Breakpoint => {
    const [breakpoint, setBreakpoint] = useState<Breakpoint>(
        getBreakpoint(Dimensions.get('window').width)
    );

    useEffect(() => {
        const onChange = ({ window }: { window: ScaledSize }) => {
            setBreakpoint(getBreakpoint(window.width));
        };

        const subscription = Dimensions.addEventListener('change', onChange);
        return () => subscription?.remove();
    }, []);

    return breakpoint;
};

export const useBreakpointValue = <T>(values: { sm: T; md?: T; lg?: T; xl?: T }): T => {
    const bp = useBreakpoint();

    if (bp === 'xl') return values.xl ?? values.lg ?? values.md ?? values.sm;
    if (bp === 'lg') return values.lg ?? values.md ?? values.sm;
    if (bp === 'md') return values.md ?? values.sm;
    return values.sm;
};
