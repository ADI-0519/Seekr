import React from 'react';
import { Animated, Platform } from 'react-native';

export function useWorkflowEntrance() {
    const workflowSectionY = React.useRef(0);
    const workflowTriggeredRef = React.useRef(false);
    const workflowAnimValues = React.useRef([
        new Animated.Value(0),
        new Animated.Value(0),
        new Animated.Value(0),
    ]).current;

    const triggerWorkflowAnimation = React.useCallback(() => {
        if (workflowTriggeredRef.current) return;
        workflowTriggeredRef.current = true;

        const animations = workflowAnimValues.map((value, idx) =>
            Animated.timing(value, {
                toValue: 1,
                duration: 520,
                delay: idx * 120,
                useNativeDriver: Platform.OS !== 'web',
            }),
        );

        Animated.stagger(120, animations).start();
    }, [workflowAnimValues]);

    const maybeTriggerWorkflowAnimation = React.useCallback(
        (scrollY: number, viewportHeight: number) => {
            if (workflowTriggeredRef.current) return;
            const threshold = workflowSectionY.current - viewportHeight * 0.8;
            if (scrollY >= threshold) {
                triggerWorkflowAnimation();
            }
        },
        [triggerWorkflowAnimation],
    );

    const handleScroll = React.useCallback(
        (event: any) => {
            const scrollY = event.nativeEvent.contentOffset?.y ?? 0;
            const viewportHeight = event.nativeEvent.layoutMeasurement?.height ?? 0;
            maybeTriggerWorkflowAnimation(scrollY, viewportHeight);
        },
        [maybeTriggerWorkflowAnimation],
    );

    const onWorkflowLayout = React.useCallback((event: any) => {
        workflowSectionY.current = event.nativeEvent.layout.y;
    }, []);

    const getWorkflowCardAnimatedStyle = React.useCallback(
        (index: number) => {
            const value = workflowAnimValues[index];
            return {
                opacity: value,
                transform: [
                    {
                        translateY: value.interpolate({
                            inputRange: [0, 1],
                            outputRange: [28, 0],
                        }),
                    },
                ],
            };
        },
        [workflowAnimValues],
    );

    return {
        handleScroll,
        onWorkflowLayout,
        getWorkflowCardAnimatedStyle,
    };
}
