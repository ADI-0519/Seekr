import React, { useState } from 'react';
import {
    View,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    Pressable,
    Alert,
} from 'react-native';
import { router } from 'expo-router';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react-native';
import { Typography } from '../../src/components/ui/Typography';
import { PrimaryButton } from '../../src/components/ui/PrimaryButton';
import { FloatingShell } from '../../src/design/primitives/FloatingShell';
import { useThemeColors } from '../../src/theme/ThemeProvider';
import { useAuth } from '../../src/hooks/useAuth';
import { AuthField } from '@/components/auth/AuthField';

export default function ForgotPasswordScreen() {
    const { resetPassword, isLoading } = useAuth();
    const colors = useThemeColors();
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [sent, setSent] = useState(false);

    const handleReset = async () => {
        if (!email) {
            setError('Email is required');
            return;
        }
        if (!/\S+@\S+\.\S+/.test(email)) {
            setError('Please enter a valid email');
            return;
        }
        setError('');
        try {
            await resetPassword(email);
            setSent(true);
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : 'Failed to send reset email';
            Alert.alert('Error', message);
        }
    };

    if (sent) {
        return (
            <View style={styles.container}>
                <View style={styles.centeredContent}>
                    <FloatingShell elevation="elevated" padding={32} style={{ alignItems: 'center' }}>
                        <CheckCircle size={56} color={colors.primaryEmerald} style={{ marginBottom: 20 }} />
                        <Typography variant="headingLg" align="center" style={{ marginBottom: 8 }}>
                            Check your email
                        </Typography>
                        <Typography
                            variant="bodyMd"
                            color={colors.textSecondary}
                            align="center"
                            style={{ marginBottom: 28 }}
                        >
                            We've sent password reset instructions to {email}
                        </Typography>
                        <PrimaryButton
                            label="Back to Login"
                            onPress={() => router.back()}
                            variant="outline"
                            size="lg"
                        />
                    </FloatingShell>
                </View>
            </View>
        );
    }

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={styles.content}>
                <Pressable
                    style={[styles.backButton, { backgroundColor: colors.surfaceElevated }]}
                    onPress={() => router.back()}
                >
                    <ArrowLeft size={22} color={colors.textPrimary} />
                </Pressable>

                <FloatingShell elevation="elevated" padding={32}>
                    <Typography variant="headingLg" style={{ marginBottom: 4 }}>
                        Forgot Password?
                    </Typography>
                    <Typography
                        variant="bodyMd"
                        color={colors.textSecondary}
                        style={{ marginBottom: 28 }}
                    >
                        No worries, we'll send you reset instructions
                    </Typography>

                    <AuthField
                        label="Email"
                        value={email}
                        onChangeText={setEmail}
                        placeholder="Enter your email"
                        keyboardType="email-address"
                        autoComplete="email"
                        icon={<Mail size={18} color={colors.textSecondary} style={{ marginRight: 10 }} />}
                        error={error}
                    />

                    <View style={{ marginTop: 8 }}>
                        <PrimaryButton
                            label={isLoading ? 'Sending…' : 'Send Reset Link'}
                            onPress={handleReset}
                            loading={isLoading}
                            disabled={isLoading}
                            size="lg"
                        />
                    </View>
                </FloatingShell>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    content: {
        flex: 1,
        paddingHorizontal: 24,
        paddingVertical: 48,
        maxWidth: 480,
        alignSelf: 'center',
        width: '100%',
    },
    centeredContent: {
        flex: 1,
        justifyContent: 'center',
        paddingHorizontal: 24,
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
});
