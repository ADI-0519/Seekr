import React, { useState } from 'react';
import {
    View,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    Pressable,
    Alert,
    Image,
} from 'react-native';
import { Link, router } from 'expo-router';
import { Mail, Lock, ArrowLeft } from 'lucide-react-native';
import { Typography } from '../../src/components/ui/Typography';
import { PrimaryButton } from '../../src/components/ui/PrimaryButton';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { AnimatedPageEntry } from '../../src/components/ui/AnimatedPageEntry';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { useAuth } from '../../src/hooks/useAuth';
import { FEATURES, APP_CONFIG } from '../../src/constants';
import { AuthField } from '@/components/auth/AuthField';

const GoogleLogo = ({ size = 18 }: { size?: number }) => (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
        <Typography variant="bodyLg" style={{ fontWeight: '700', fontSize: size }}>G</Typography>
    </View>
);

export default function LoginScreen() {
    const { signIn, signInWithGoogle, isLoading } = useAuth();
    const colors = useThemeColors();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
    const [authError, setAuthError] = useState('');

    const getAuthErrorCode = (error: unknown) => {
        if (typeof error === 'object' && error !== null && 'code' in error) {
            const code = (error as { code?: unknown }).code;
            if (typeof code === 'string') {
                return code;
            }
        }

        const message = error instanceof Error ? error.message : '';
        const match = message.match(/\((auth\/[^)]+)\)/);
        return match?.[1] ?? '';
    };

    const getLoginErrorMessage = (error: unknown) => {
        const message = error instanceof Error ? error.message : '';
        const code = getAuthErrorCode(error);
        const invalidCredentialCodes = [
            'auth/invalid-credential',
            'auth/invalid-login-credentials',
            'auth/user-not-found',
            'auth/wrong-password',
        ];

        if (invalidCredentialCodes.includes(code) || invalidCredentialCodes.some((item) => message.includes(item))) {
            return 'Email or password is incorrect.';
        }

        if (code === 'auth/too-many-requests' || message.includes('auth/too-many-requests')) {
            return 'Too many sign-in attempts. Please try again in a moment.';
        }

        return message || 'Unable to sign in right now. Please try again.';
    };

    const handleEmailChange = (value: string) => {
        setEmail(value);
        setAuthError('');

        if (errors.email) {
            setErrors((currentErrors) => ({ ...currentErrors, email: undefined }));
        }
    };

    const handlePasswordChange = (value: string) => {
        setPassword(value);
        setAuthError('');

        if (errors.password) {
            setErrors((currentErrors) => ({ ...currentErrors, password: undefined }));
        }
    };

    const validate = () => {
        const newErrors: { email?: string; password?: string } = {};
        if (!email) {
            newErrors.email = 'Email is required';
        } else if (!/\S+@\S+\.\S+/.test(email)) {
            newErrors.email = 'Please enter a valid email';
        }
        if (!password) {
            newErrors.password = 'Password is required';
        } else if (password.length < 6) {
            newErrors.password = 'Password must be at least 6 characters';
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleLogin = async () => {
        setAuthError('');
        if (!validate()) return;
        try {
            await signIn(email, password);
            router.replace('/dashboard');
        } catch (error: unknown) {
            setAuthError(getLoginErrorMessage(error));
        }
    };

    const handleGoogleLogin = async () => {
        setAuthError('');
        try {
            await signInWithGoogle();
            router.replace('/dashboard');
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : 'Please try again';
            Alert.alert('Google Sign-In Failed', message);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <ScrollView
                contentContainerStyle={styles.scrollContent}
                keyboardShouldPersistTaps="handled"
                showsVerticalScrollIndicator={false}
            >
            <AnimatedPageEntry>
                <Pressable
                    style={[styles.backButton, { backgroundColor: colors.surfaceElevated }]}
                    onPress={() => router.replace('/')}
                >
                    <ArrowLeft size={22} color={colors.textPrimary} />
                </Pressable>

                {/* Logo & Branding */}
                <View style={styles.header}>
                    <Image
                        source={require('../../assets/seekr-logo.png')}
                        style={styles.logoImage}
                        resizeMode="contain"
                    />
                    <Typography variant="displayMd" style={{ marginTop: 16, fontWeight: '700' }}>
                        {APP_CONFIG.name}
                    </Typography>
                    <Typography variant="bodyMd" color={colors.textSecondary} style={{ marginTop: 4 }}>
                        {APP_CONFIG.tagline}
                    </Typography>
                </View>

                {/* Form Card */}
                <FloatingShell elevation="elevated" padding={32} style={{ marginBottom: 24 }}>
                    <Typography variant="headingLg" style={{ marginBottom: 4 }}>
                        Welcome back
                    </Typography>
                    <Typography variant="bodyMd" color={colors.textSecondary} style={{ marginBottom: 28 }}>
                        Sign in to continue
                    </Typography>

                    <AuthField
                        label="Email"
                        value={email}
                        onChangeText={handleEmailChange}
                        placeholder="Enter your email"
                        keyboardType="email-address"
                        autoComplete="email"
                        icon={<Mail size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.email}
                    />

                    <AuthField
                        label="Password"
                        value={password}
                        onChangeText={handlePasswordChange}
                        placeholder="Enter your password"
                        secureTextEntry
                        showPassword={showPassword}
                        onTogglePassword={() => setShowPassword(!showPassword)}
                        icon={<Lock size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.password}
                    />

                    {/* Forgot password link */}
                    <View style={{ alignSelf: 'flex-end', marginBottom: 20 }}>
                        <Link href="/(auth)/forgot-password">
                            <Typography variant="bodySm" color={colors.primaryEmerald} style={{ fontWeight: '500' }}>
                                Forgot password?
                            </Typography>
                        </Link>
                    </View>

                    {/* Sign In Button */}
                    <PrimaryButton
                        label={isLoading ? 'Signing in…' : 'Sign In'}
                        onPress={handleLogin}
                        loading={isLoading}
                        disabled={isLoading}
                        size="lg"
                    />
                    {authError ? (
                        <Typography
                            variant="bodySm"
                            color={colors.error}
                            align="center"
                            style={{ marginTop: 12 }}
                        >
                            {authError}
                        </Typography>
                    ) : null}

                    {/* Divider */}
                    <View style={styles.dividerRow}>
                        <View style={[styles.dividerLine, { backgroundColor: colors.borderSubtle }]} />
                        <Typography variant="bodySm" color={colors.textSecondary} style={{ marginHorizontal: 12 }}>
                            or
                        </Typography>
                        <View style={[styles.dividerLine, { backgroundColor: colors.borderSubtle }]} />
                    </View>

                    {/* Google Button */}
                    <PrimaryButton
                        label="Continue with Google"
                        onPress={handleGoogleLogin}
                        variant="outline"
                        size="lg"
                        icon={<GoogleLogo />}
                        disabled={isLoading}
                    />

                    {/* Sign up link */}
                    <View style={styles.switchRow}>
                        <Typography variant="bodyMd" color={colors.textSecondary}>
                            Don't have an account?{' '}
                        </Typography>
                        <Link href="/(auth)/register">
                            <Typography variant="bodyMd" color={colors.primaryEmerald} style={{ fontWeight: '600' }}>
                                Sign up
                            </Typography>
                        </Link>
                    </View>
                </FloatingShell>

                {/* Demo hint */}
                {FEATURES.enableMockAuth && (
                    <FloatingShell elevation="none" padding={16} style={{ marginBottom: 24 }}>
                        <Typography variant="bodySm" color={colors.primaryEmerald} align="center">
                            Demo mode: Use any email and password (6+ chars)
                        </Typography>
                    </FloatingShell>
                )}
            </AnimatedPageEntry>
            </ScrollView>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    scrollContent: {
        flexGrow: 1,
        justifyContent: 'center',
        paddingHorizontal: 24,
        paddingVertical: 48,
        maxWidth: 480,
        alignSelf: 'center',
        width: '100%',
    },
    backButton: {
        width: 44,
        height: 44,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 24,
    },
    header: {
        alignItems: 'center',
        marginBottom: 40,
    },
    logoImage: {
        width: 72,
        height: 72,
        borderRadius: 20,
    },
    dividerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: 20,
    },
    dividerLine: {
        flex: 1,
        height: 1,
    },
    switchRow: {
        flexDirection: 'row',
        justifyContent: 'center',
        marginTop: 20,
    },
});
