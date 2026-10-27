import React, { useEffect } from 'react';
import { View, Platform, ViewProps } from 'react-native';
import Animated, {
    useSharedValue,
    useAnimatedStyle,
    withTiming,
    Easing,
    useReducedMotion,
} from 'react-native-reanimated';
import { useEntryAnimation } from '../../hooks/useEntryAnimation';
import { motion } from '../tokens/motion';

interface AnimatedPageProps extends ViewProps {
    children: React.ReactNode;
}

export const AnimatedPage: React.FC<AnimatedPageProps> = ({ children, style, ...rest }) => {
    if (Platform.OS === 'web') {
        return <WebAnimatedPage style={style} {...rest}>{children}</WebAnimatedPage>;
    }

    return <NativeAnimatedPage style={style} {...rest}>{children}</NativeAnimatedPage>;
};

const WebAnimatedPage: React.FC<AnimatedPageProps> = ({ children, style, ...rest }) => {
    const entryStyle = useEntryAnimation({
        direction: 'up',
        duration: motion.durationPage,
    });

    return (
        <View style={[{ flex: 1 }, entryStyle, style]} {...rest}>
            {children}
        </View>
    );
};

const NativeAnimatedPage: React.FC<AnimatedPageProps> = ({ children, style, ...rest }) => {
    const reducedMotion = useReducedMotion();
    const opacity = useSharedValue(reducedMotion ? 1 : 0);
    const translateY = useSharedValue(reducedMotion ? 0 : 14);

    useEffect(() => {
        if (reducedMotion) return;

        opacity.value = withTiming(1, {
            duration: 300,
            easing: Easing.out(Easing.cubic),
        });
        translateY.value = withTiming(0, {
            duration: 340,
            easing: Easing.out(Easing.cubic),
        });
    }, []);

    const animatedStyle = useAnimatedStyle(() => ({
        opacity: opacity.value,
        transform: [{ translateY: translateY.value }],
    }));

    return (
        <Animated.View style={[{ flex: 1 }, animatedStyle, style]} {...rest}>
            {children}
        </Animated.View>
    );
};
