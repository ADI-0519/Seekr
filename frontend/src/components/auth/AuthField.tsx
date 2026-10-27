import React from 'react';
import { View, StyleSheet, TextInput, Pressable, Platform, TextInputProps } from 'react-native';
import { Eye, EyeOff } from 'lucide-react-native';
import { Typography } from '@/components/ui/Typography';
import { useThemeColors } from '@/theme/ThemeProvider';

interface AuthFieldProps {
    label: string;
    value: string;
    onChangeText: (value: string) => void;
    placeholder: string;
    icon: React.ReactNode;
    error?: string;
    secureTextEntry?: boolean;
    showPassword?: boolean;
    onTogglePassword?: () => void;
    keyboardType?: TextInputProps['keyboardType'];
    autoCapitalize?: TextInputProps['autoCapitalize'];
    autoComplete?: TextInputProps['autoComplete'];
}

export function AuthField({
    label,
    value,
    onChangeText,
    placeholder,
    icon,
    error,
    secureTextEntry = false,
    showPassword = false,
    onTogglePassword,
    keyboardType = 'default',
    autoCapitalize = 'none',
    autoComplete,
}: AuthFieldProps) {
    const colors = useThemeColors();
    const webInputStyle = Platform.OS === 'web'
        ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
        : null;

    return (
        <View style={styles.fieldGroup}>
            <Typography variant="bodySm" style={styles.fieldLabel}>
                {label}
            </Typography>
            <View style={[styles.inputRow, { borderColor: error ? colors.error : colors.borderSubtle }]}>
                {icon}
                <TextInput
                    style={[styles.input, { color: colors.textPrimary }, webInputStyle]}
                    placeholder={placeholder}
                    placeholderTextColor={colors.textSecondary}
                    secureTextEntry={secureTextEntry && !showPassword}
                    autoCapitalize={autoCapitalize}
                    keyboardType={keyboardType}
                    autoComplete={autoComplete}
                    value={value}
                    onChangeText={onChangeText}
                />
                {secureTextEntry && onTogglePassword ? (
                    <Pressable onPress={onTogglePassword}>
                        {showPassword ? (
                            <EyeOff size={18} color={colors.textSecondary} />
                        ) : (
                            <Eye size={18} color={colors.textSecondary} />
                        )}
                    </Pressable>
                ) : null}
            </View>
            {error ? (
                <Typography variant="bodySm" color={colors.error} style={styles.errorText}>
                    {error}
                </Typography>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    fieldGroup: {
        marginBottom: 16,
    },
    fieldLabel: {
        marginBottom: 6,
        fontWeight: '600',
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        borderWidth: 1,
        borderRadius: 12,
        paddingHorizontal: 14,
        height: 48,
    },
    input: {
        flex: 1,
        fontSize: 15,
        fontFamily: 'PlusJakartaSans_400Regular',
        height: '100%',
        ...(Platform.OS === 'web' ? { outlineStyle: 'none' } : {}),
    },
    errorText: {
        marginTop: 4,
    },
});
