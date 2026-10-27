import React, { useState } from 'react';
import {
    View,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    ScrollView,
    Alert,
    Pressable,
} from 'react-native';
import { Link, router } from 'expo-router';
import { Mail, Lock, User, ArrowLeft } from 'lucide-react-native';
import { Typography } from '../../src/components/ui/Typography';
import { PrimaryButton } from '../../src/components/ui/PrimaryButton';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { AnimatedPageEntry } from '../../src/components/ui/AnimatedPageEntry';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { useAuth } from '../../src/hooks/useAuth';
import { AuthField } from '@/components/auth/AuthField';

const GoogleLogo = ({ size = 18 }: { size?: number }) => (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
        <Typography variant="bodyLg" style={{ fontWeight: '700', fontSize: size }}>G</Typography>
    </View>
);

export default function RegisterScreen() {
    const { signUp, signUpWithGoogle, isLoading } = useAuth();
    const colors = useThemeColors();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});

    const validate = () => {
        const newErrors: Record<string, string> = {};
        if (!name.trim()) newErrors.name = 'Name is required';
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
        if (password !== confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match';
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const showSignupError = (title: string, message: string) => {
        if (Platform.OS === 'web' && typeof window !== 'undefined') {
            window.alert(`${title}

${message}`);
            return;
        }
        Alert.alert(title, message);
    };

    const handleRegister = async () => {
        if (!validate()) {
            return;
        }

        try {
            await signUp(email, password, name);
            router.replace('/dashboard');
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : 'Please try again';
            showSignupError('Registration Failed', message);
        }
    };

    const handleGoogleRegister = async () => {
        try {
            await signUpWithGoogle();
            router.replace('/dashboard');
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : 'Please try again';
            showSignupError('Google Sign-Up Failed', message);
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
                {/* Back button */}
                <Pressable
                    style={[styles.backButton, { backgroundColor: colors.surfaceElevated }]}
                    onPress={() => router.back()}
                >
                    <ArrowLeft size={22} color={colors.textPrimary} />
                </Pressable>

                {/* Form Card */}
                <FloatingShell elevation="elevated" padding={32} style={{ marginBottom: 24 }}>
                    <Typography variant="headingLg" style={{ marginBottom: 4 }}>
                        Create Account
                    </Typography>
                    <Typography variant="bodyMd" color={colors.textSecondary} style={{ marginBottom: 28 }}>
                        Join Seekr to search your lectures
                    </Typography>

                    <AuthField
                        label="Full Name"
                        value={name}
                        onChangeText={setName}
                        placeholder="Enter your name"
                        autoCapitalize="words"
                        icon={<User size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.name}
                    />
                    <AuthField
                        label="Email"
                        value={email}
                        onChangeText={setEmail}
                        placeholder="Enter your email"
                        keyboardType="email-address"
                        autoComplete="email"
                        icon={<Mail size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.email}
                    />
                    <AuthField
                        label="Password"
                        value={password}
                        onChangeText={setPassword}
                        placeholder="Create a password"
                        secureTextEntry
                        showPassword={showPassword}
                        onTogglePassword={() => setShowPassword(!showPassword)}
                        icon={<Lock size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.password}
                    />
                    <AuthField
                        label="Confirm Password"
                        value={confirmPassword}
                        onChangeText={setConfirmPassword}
                        placeholder="Confirm your password"
                        secureTextEntry
                        icon={<Lock size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={errors.confirmPassword}
                    />

                    <View style={{ marginTop: 8 }}>
                        <PrimaryButton
                            label={isLoading ? 'Creating account…' : 'Create Account'}
                            onPress={handleRegister}
                            loading={isLoading}
                            disabled={isLoading}
                            size="lg"
                        />
                    </View>

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
                        onPress={handleGoogleRegister}
                        variant="outline"
                        size="lg"
                        icon={<GoogleLogo />}
                        disabled={isLoading}
                    />

                    {/* Login link */}
                    <View style={styles.switchRow}>
                        <Typography variant="bodyMd" color={colors.textSecondary}>
                            Already have an account?{' '}
                        </Typography>
                        <Link href="/(auth)/login">
                            <Typography variant="bodyMd" color={colors.primaryEmerald} style={{ fontWeight: '600' }}>
                                Sign in
                            </Typography>
                        </Link>
                    </View>
                </FloatingShell>
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
