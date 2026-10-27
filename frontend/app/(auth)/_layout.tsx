import { Stack, Redirect } from 'expo-router';
import { AuthBootstrapFallback } from '../../src/components/ui/AuthBootstrapFallback';
import { useAuth } from '../../src/hooks/useAuth';

export default function AuthLayout() {
    const { user, isInitializing } = useAuth();
    if (isInitializing) return <AuthBootstrapFallback />;
    if (user) return <Redirect href="/dashboard" />;


    return (
        <Stack
            screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: 'transparent' },
                animation: 'fade',
                animationDuration: 250,
                gestureEnabled: true,
            }}
        />
    );
}
