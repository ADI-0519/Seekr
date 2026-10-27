import React from 'react';
import { Redirect, useRouter } from 'expo-router';
import { GraduationCap, Microscope, Presentation } from 'lucide-react-native';
import { Animated, ScrollView, View } from 'react-native';
import { PageFrame } from '../src/design/primitives/PageFrame';
import { Footer } from '../src/components/shell/Footer';
import { LandingNavbar } from '../src/components/shell/LandingNavbar';
import { useAuth } from '../src/hooks/useAuth';
import { useBreakpointValue } from '../src/hooks/useBreakpoint';
import { useThemeColors } from '../src/theme/ThemeProvider';
import { HeroSection } from '../src/components/landing/HeroSection';
import { CoreFeaturesSection } from '../src/components/landing/CoreFeaturesSection';
import { HowItWorksSection } from '../src/components/landing/HowItWorksSection';
import { UseCasesSection } from '../src/components/landing/UseCasesSection';
import { FinalCtaSection } from '../src/components/landing/FinalCtaSection';
import { landingStyles as styles } from '../src/components/landing/styles';
import { buildGlassStyle } from '../src/components/landing/utils';
import { useLandingAnimations } from '../src/components/landing/useLandingAnimations';
import { LandingUseCase } from '../src/components/landing/types';

export default function LandingPage() {
    const { user, isInitializing } = useAuth();
    const router = useRouter();
    const colors = useThemeColors();
    const isMobile = useBreakpointValue({ sm: true, md: true, lg: false, xl: false });
    const glassStrong = React.useMemo(() => buildGlassStyle(colors.surfaceBase, 0.62), [colors.surfaceBase]);
    const glassMedium = React.useMemo(() => buildGlassStyle(colors.surfaceBase, 0.5), [colors.surfaceBase]);
    const glassSoft = React.useMemo(() => buildGlassStyle(colors.surfaceBase, 0.42), [colors.surfaceBase]);

    const {
        handleScroll,
        onSectionLayout,
        getHeroPartStyle,
        getSectionStyle,
        getWorkflowCardStyle,
    } = useLandingAnimations();

    const scrollRef = React.useRef<ScrollView>(null);
    const [coreFeaturesY, setCoreFeaturesY] = React.useState<number | null>(null);
    const [howItWorksY, setHowItWorksY] = React.useState<number | null>(null);

    const scrollToSection = React.useCallback((y: number | null) => {
        if (y == null) return;
        scrollRef.current?.scrollTo({
            y: Math.max(0, y - 24),
            animated: true,
        });
    }, []);

    const audienceItems = React.useMemo<LandingUseCase[]>(
        () => [
            {
                icon: <GraduationCap size={21} color={colors.primaryEmerald} />,
                title: 'Students revising',
                body: 'Find exactly what was said about a topic across a semester of lectures - in seconds, not hours.',
            },
            {
                icon: <Presentation size={21} color={colors.primaryEmerald} />,
                title: 'Lecturers summarising',
                body: 'Quickly locate and reference specific explanations or examples from past lectures.',
            },
            {
                icon: <Microscope size={21} color={colors.primaryEmerald} />,
                title: 'Researchers exploring',
                body: 'Search seminar series and talks to find discussions of specific methods or findings.',
            },
        ],
        [colors.primaryEmerald],
    );

    if (isInitializing) return null;
    if (user) return <Redirect href="/dashboard" />;

    return (
        <PageFrame withSidebar={false}>
            <ScrollView
                ref={scrollRef}
                style={styles.page}
                contentContainerStyle={[styles.content, isMobile && styles.contentMobile]}
                showsVerticalScrollIndicator={true}
                persistentScrollbar={true}
                onScroll={handleScroll}
                scrollEventThrottle={16}
            >
                <LandingNavbar
                    isMobile={isMobile}
                    onPressProduct={() => scrollToSection(coreFeaturesY)}
                    onPressHowItWorks={() => scrollToSection(howItWorksY)}
                />

                <HeroSection isMobile={isMobile} glassStrong={glassStrong} getHeroPartStyle={getHeroPartStyle} />

                {/* Core Features — scroll reveal */}
                <Animated.View
                    style={getSectionStyle(0)}
                    onLayout={(event) => {
                        const y = event.nativeEvent.layout.y;
                        setCoreFeaturesY(y);
                        onSectionLayout(0)(event);
                    }}
                >
                    <CoreFeaturesSection isMobile={isMobile} glassMedium={glassMedium} glassSoft={glassSoft} />
                </Animated.View>

                {/* How It Works — scroll reveal with staggered cards */}
                <Animated.View
                    style={getSectionStyle(1)}
                    onLayout={(event) => {
                        const y = event.nativeEvent.layout.y;
                        setHowItWorksY(y);
                        onSectionLayout(1)(event);
                    }}
                >
                    <HowItWorksSection
                        isMobile={isMobile}
                        getWorkflowCardAnimatedStyle={getWorkflowCardStyle}
                    />
                </Animated.View>

                {/* Use Cases — scroll reveal */}
                <Animated.View style={getSectionStyle(2)} onLayout={onSectionLayout(2)}>
                    <UseCasesSection isMobile={isMobile} audienceItems={audienceItems} />
                </Animated.View>

                {/* Final CTA — scroll reveal */}
                <Animated.View style={getSectionStyle(3)} onLayout={onSectionLayout(3)}>
                    <FinalCtaSection glassMedium={glassMedium} onGetStarted={() => router.push('/(auth)/register')} />
                </Animated.View>

                <Footer />
            </ScrollView>
        </PageFrame>
    );
}
