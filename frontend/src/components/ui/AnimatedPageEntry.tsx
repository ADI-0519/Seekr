import React from 'react';
import { Animated, Platform } from 'react-native';

export function AnimatedPageEntry({
    children,
    delay = 0,
    style,
}: {
    children: React.ReactNode;
    delay?: number;
    style?: any;
}) {
    const opacity = React.useRef(new Animated.Value(0)).current;
    const translateY = React.useRef(new Animated.Value(18)).current;

    React.useEffect(() => {
        Animated.parallel([
            Animated.timing(opacity, {
                toValue: 1,
                duration: 420,
                delay,
                useNativeDriver: Platform.OS !== 'web',
            }),
            Animated.timing(translateY, {
                toValue: 0,
                duration: 420,
                delay,
                useNativeDriver: Platform.OS !== 'web',
            }),
        ]).start();
    }, []);

    return (
        <Animated.View
            style={[
                { opacity, transform: [{ translateY }], flex: 1 },
                style,
            ]}
        >
            {children}
        </Animated.View>
    );
}
