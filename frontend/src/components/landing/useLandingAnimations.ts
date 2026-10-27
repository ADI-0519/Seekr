import React from 'react';
import { Animated, Platform, Dimensions } from 'react-native';

const ANIM_DURATION = 520;
const STAGGER_DELAY = 100;
const SCROLL_TRIGGER_RATIO = 0.82;

const SECTION_COUNT = 4;
const WORKFLOW_CARD_COUNT = 3;

const HERO_PART_COUNT = 5;

export function useLandingAnimations() {
    const heroValues = React.useRef(
        Array.from({ length: HERO_PART_COUNT }, () => new Animated.Value(0)),
    ).current;

    const sectionYs = React.useRef<number[]>(new Array(SECTION_COUNT).fill(0)).current;
    const sectionTriggered = React.useRef<boolean[]>(new Array(SECTION_COUNT).fill(false)).current;
    const sectionValues = React.useRef(
        Array.from({ length: SECTION_COUNT }, () => new Animated.Value(0)),
    ).current;

    const workflowValues = React.useRef(
        Array.from({ length: WORKFLOW_CARD_COUNT }, () => new Animated.Value(0)),
    ).current;

    React.useEffect(() => {
        const anims = heroValues.map((v, i) =>
            Animated.timing(v, {
                toValue: 1,
                duration: ANIM_DURATION + 80,
                delay: 200 + i * STAGGER_DELAY,
                useNativeDriver: Platform.OS !== 'web',
            }),
        );
        Animated.stagger(STAGGER_DELAY, anims).start();
    }, []);

    const triggerSection = React.useCallback((idx: number) => {
        if (sectionTriggered[idx]) return;
        sectionTriggered[idx] = true;
        Animated.timing(sectionValues[idx], {
            toValue: 1,
            duration: ANIM_DURATION,
            useNativeDriver: Platform.OS !== 'web',
        }).start();

        if (idx === 1) {
            const workflowAnims = workflowValues.map((v, i) =>
                Animated.timing(v, {
                    toValue: 1,
                    duration: ANIM_DURATION,
                    delay: i * 120,
                    useNativeDriver: Platform.OS !== 'web',
                }),
            );
            Animated.stagger(120, workflowAnims).start();
        }
    }, [sectionValues, sectionTriggered, workflowValues]);

    const handleScroll = React.useCallback(
        (event: any) => {
            const scrollY = event.nativeEvent.contentOffset?.y ?? 0;
            const viewportH = event.nativeEvent.layoutMeasurement?.height ?? 0;
            for (let i = 0; i < SECTION_COUNT; i++) {
                if (!sectionTriggered[i] && sectionYs[i] > 0) {
                    const threshold = sectionYs[i] - viewportH * SCROLL_TRIGGER_RATIO;
                    if (scrollY >= threshold) {
                        triggerSection(i);
                    }
                }
            }
        },
        [triggerSection],
    );

    const onSectionLayout = React.useCallback(
        (sectionIndex: number) => (event: any) => {
            sectionYs[sectionIndex] = event.nativeEvent.layout.y;

            const viewportH = Dimensions.get('window').height;
            const threshold = sectionYs[sectionIndex] - viewportH * SCROLL_TRIGGER_RATIO;
            if (0 >= threshold && !sectionTriggered[sectionIndex]) {
                setTimeout(() => triggerSection(sectionIndex), 300);
            }
        },
        [triggerSection],
    );

    const getHeroPartStyle = React.useCallback(
        (partIndex: number) => {
            const v = heroValues[partIndex];
            return {
                opacity: v,
                transform: [
                    {
                        translateY: v.interpolate({
                            inputRange: [0, 1],
                            outputRange: [24, 0],
                        }),
                    },
                ],
            };
        },
        [heroValues],
    );

    const getSectionStyle = React.useCallback(
        (sectionIndex: number) => {
            const v = sectionValues[sectionIndex];
            return {
                opacity: v,
                transform: [
                    {
                        translateY: v.interpolate({
                            inputRange: [0, 1],
                            outputRange: [32, 0],
                        }),
                    },
                ],
            };
        },
        [sectionValues],
    );

    const getWorkflowCardStyle = React.useCallback(
        (cardIndex: number) => {
            const v = workflowValues[cardIndex];
            return {
                opacity: v,
                transform: [
                    {
                        translateY: v.interpolate({
                            inputRange: [0, 1],
                            outputRange: [28, 0],
                        }),
                    },
                ],
            };
        },
        [workflowValues],
    );

    return {
        handleScroll,
        onSectionLayout,
        getHeroPartStyle,
        getSectionStyle,
        getWorkflowCardStyle,
    };
}
