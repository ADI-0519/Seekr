import React, { useEffect, useRef, useState } from 'react';
import { View, StyleSheet, Pressable, TextInput, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { FloatingShell } from '../src/design/primitives/FloatingShell';
import { Typography } from '../src/components/ui/Typography';
import { PrimaryButton } from '../src/components/ui/PrimaryButton';
import { theme } from '../src/design/index';
import { X, UploadCloud, Link as LinkIcon, FileVideo, AlertCircle, CheckCircle } from 'lucide-react-native';
import * as DocumentPicker from 'expo-document-picker';
import { useUploadVideo, useUploadLink } from '../src/hooks';
import { useThemeColors } from '../src/theme/ThemeProvider';

const MAX_FILE_SIZE_MB = 1024; // 1GB
const ALLOWED_TYPES = ['video/mp4', 'video/quicktime', 'video/webm', 'video/x-matroska'];
const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mkv'];

function formatFileSize(bytes: number): string {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function validateFile(file: DocumentPicker.DocumentPickerAsset): string | null {
    if (file.size && file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        return `File is too large (${formatFileSize(file.size)}). Maximum size is ${MAX_FILE_SIZE_MB / 1024} GB.`;
    }
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return `Unsupported file type (${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }
    return null;
}

export default function UploadModalScreen() {
    const router = useRouter();
    const [title, setTitle] = useState('');
    const [youtubeUrl, setYoutubeUrl] = useState('');
    const [selectedFile, setSelectedFile] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
    const [validationError, setValidationError] = useState<string | null>(null);
    const [uploadProgress, setUploadProgress] = useState<number>(0);
    const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const uploadVideoMutation = useUploadVideo();
    const uploadLinkMutation = useUploadLink();
    const themeColors = useThemeColors();

    const isUploading = uploadState === 'uploading';
    const progressWidth = `${Math.min(100, uploadProgress)}%` as `${number}%`;
    const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const redirectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const mountedRef = useRef(true);

    const styles = React.useMemo(() => getStyles(themeColors), [themeColors]);
    const webInputReset = Platform.OS === 'web'
        ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
        : null;

    const clearProgressInterval = () => {
        if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
        }
    };

    const clearRedirectTimeout = () => {
        if (redirectTimeoutRef.current) {
            clearTimeout(redirectTimeoutRef.current);
            redirectTimeoutRef.current = null;
        }
    };

    useEffect(() => {
        return () => {
            mountedRef.current = false;
            clearProgressInterval();
            clearRedirectTimeout();
        };
    }, []);

    const pickDocument = async () => {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: ALLOWED_TYPES,
                copyToCacheDirectory: true,
            });

            if (!result.canceled && result.assets && result.assets.length > 0) {
                const file = result.assets[0];
                const error = validateFile(file);
                if (error) {
                    setValidationError(error);
                    setSelectedFile(null);
                    return;
                }
                setValidationError(null);
                setSelectedFile(file);
                if (!title) {
                    const fileName = file.name.split('.').slice(0, -1).join('.');
                    setTitle(fileName);
                }
            }
        } catch (err) {
            console.error('Error picking document:', err);
        }
    };

    const handleFileUpload = async () => {
        if (!selectedFile || !title) return;

        setUploadState('uploading');
        setUploadProgress(0);
        setErrorMessage(null);
        setSuccessMessage(null);
        clearProgressInterval();
        clearRedirectTimeout();

        progressIntervalRef.current = setInterval(() => {
            setUploadProgress(prev => {
                if (prev >= 90) return prev; // Hold at 90 until complete
                return prev + Math.random() * 15;
            });
        }, 500);

        try {
            const response = await uploadVideoMutation.mutateAsync({
                file: selectedFile,
                title,
            });
            if (!mountedRef.current) return;
            clearProgressInterval();
            setUploadProgress(100);
            setUploadState('success');
            setSuccessMessage(response.message ?? 'Processing will begin shortly. Redirecting...');
            redirectTimeoutRef.current = setTimeout(() => {
                if (response.fromCache) {
                    router.replace(`/(app)/lectures/${response.data.id}`);
                    return;
                }
                router.back();
            }, 1200);
        } catch (error: unknown) {
            if (!mountedRef.current) return;
            clearProgressInterval();
            setUploadState('error');
            setErrorMessage(error instanceof Error ? error.message : 'Upload failed. Please try again.');
        }
    };

    const handleUrlImport = async () => {
        if (!youtubeUrl || !title) return;

        setUploadState('uploading');
        setUploadProgress(0);
        setErrorMessage(null);
        setSuccessMessage(null);
        clearProgressInterval();
        clearRedirectTimeout();

        progressIntervalRef.current = setInterval(() => {
            setUploadProgress(prev => prev >= 90 ? prev : prev + Math.random() * 20);
        }, 400);

        try {
            const response = await uploadLinkMutation.mutateAsync({ url: youtubeUrl, title });
            if (!mountedRef.current) return;
            clearProgressInterval();
            setUploadProgress(100);
            setUploadState('success');
            setSuccessMessage(response.message ?? 'Processing will begin shortly. Redirecting...');
            redirectTimeoutRef.current = setTimeout(() => {
                if (response.fromCache) {
                    router.replace(`/(app)/lectures/${response.data.id}`);
                    return;
                }
                router.back();
            }, 1200);
        } catch (error: unknown) {
            if (!mountedRef.current) return;
            clearProgressInterval();
            setUploadState('error');
            setErrorMessage(error instanceof Error ? error.message : 'Import failed. Check the URL and try again.');
        }
    };

    const resetState = () => {
        clearProgressInterval();
        clearRedirectTimeout();
        setUploadState('idle');
        setUploadProgress(0);
        setErrorMessage(null);
        setSuccessMessage(null);
    };

    return (
        <View style={styles.backdrop}>
            <Pressable style={styles.backdropPressable} onPress={() => !isUploading && router.back()} />

            <FloatingShell
                style={styles.modalShell}
                padding={40}
                radius="modal"
                elevation="modal"
            >
                <View style={styles.header}>
                    <Typography variant="headingLg" color={themeColors.textPrimary}>
                        Upload Lecture
                    </Typography>
                    <Pressable onPress={() => !isUploading && router.back()} style={styles.closeBtn} disabled={isUploading}>
                        <X color={themeColors.textSecondary} size={24} />
                    </Pressable>
                </View>

                <View style={styles.content}>
                    <View style={styles.titleSection}>
                        <Typography variant="headingSm" color={themeColors.textPrimary} style={{ marginBottom: 12 }}>
                            Title
                        </Typography>
                        <TextInput
                            style={[styles.textInput, webInputReset]}
                            placeholder="Lecture Title (e.g. Intro to Genetics)"
                            placeholderTextColor={themeColors.textSecondary}
                            value={title}
                            onChangeText={setTitle}
                            editable={!isUploading}
                        />
                    </View>

                    {validationError && (
                        <View style={styles.errorBanner}>
                            <AlertCircle color={themeColors.error} size={16} />
                            <Typography variant="bodySm" color={themeColors.error} style={{ marginLeft: 8, flex: 1 }}>
                                {validationError}
                            </Typography>
                        </View>
                    )}

                    {uploadState !== 'idle' && (
                        <View style={styles.progressSection}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 16 }}>
                                {uploadState === 'success' ? (
                                    <CheckCircle color={themeColors.success} size={24} />
                                ) : uploadState === 'error' ? (
                                    <AlertCircle color={themeColors.error} size={24} />
                                ) : (
                                    <UploadCloud color={themeColors.primaryEmerald} size={24} />
                                )}
                                <Typography variant="headingMd" color={uploadState === 'error' ? themeColors.error : themeColors.textPrimary} style={{ marginLeft: 12 }}>
                                    {uploadState === 'success' ? 'Upload Complete' : uploadState === 'error' ? 'Upload Failed' : 'Validating & Uploading'}
                                </Typography>
                            </View>

                            <View style={styles.progressBarBg}>
                                <View style={[
                                    styles.progressBarFill,
                                    {
                                        width: progressWidth,
                                        backgroundColor: uploadState === 'error' ? themeColors.error
                                            : uploadState === 'success' ? themeColors.success
                                                : themeColors.primaryEmerald,
                                    }
                                ]} />
                            </View>
                            <View style={styles.progressLabel}>
                                {uploadState === 'success' ? (
                                    <Typography variant="bodySm" color={themeColors.textSecondary}>
                                        {successMessage ?? 'Processing will begin shortly. Redirecting...'}
                                    </Typography>
                                ) : uploadState === 'error' ? (
                                    <>
                                        <Typography variant="bodySm" color={themeColors.error} style={{ flex: 1 }}>
                                            {errorMessage}
                                        </Typography>
                                        <Pressable onPress={resetState}>
                                            <Typography variant="bodySm" color={themeColors.textPrimary} style={{ fontWeight: '600', textDecorationLine: 'underline' }}>
                                                Try Again
                                            </Typography>
                                        </Pressable>
                                    </>
                                ) : (
                                    <Typography variant="bodySm" color={themeColors.textSecondary} style={{ fontWeight: '600' }}>
                                        {Math.round(uploadProgress)}% Complete
                                    </Typography>
                                )}
                            </View>
                        </View>
                    )}

                    {uploadState === 'idle' && (
                        <>
                            <View style={styles.dropZone}>
                                {!selectedFile ? (
                                    <>
                                        <View style={styles.uploadIconCircle}>
                                            <UploadCloud color={themeColors.primaryEmerald} size={32} />
                                        </View>
                                        <Typography variant="headingSm" color={themeColors.textPrimary} style={{ marginTop: 16 }}>
                                            Select your video file
                                        </Typography>
                                        <Typography variant="bodySm" color={themeColors.textSecondary} style={{ marginTop: 8, textAlign: 'center' }}>
                                            MP4, MOV, MKV, or WEBM • Max 1 GB
                                        </Typography>
                                        <PrimaryButton
                                            label="Browse Files"
                                            variant="secondary"
                                            size="md"
                                            style={{ marginTop: 24 }}
                                            onPress={pickDocument}
                                        />
                                    </>
                                ) : (
                                    <View style={styles.selectedFileContainer}>
                                        <View style={styles.fileIconRow}>
                                            <FileVideo color={themeColors.primaryEmerald} size={32} />
                                            <View style={{ marginLeft: 16, flex: 1 }}>
                                                <Typography variant="bodyLg" color={themeColors.textPrimary} numberOfLines={1}>
                                                    {selectedFile.name}
                                                </Typography>
                                                <Typography variant="meta" color={themeColors.textSecondary}>
                                                    {selectedFile.size ? formatFileSize(selectedFile.size) : 'Unknown size'}
                                                </Typography>
                                            </View>
                                            <Pressable onPress={() => setSelectedFile(null)}>
                                                <Typography variant="meta" color={themeColors.error}>Remove</Typography>
                                            </Pressable>
                                        </View>
                                        <View style={{ opacity: !title ? 0.5 : 1 }}>
                                            <PrimaryButton
                                                label="Start Upload"
                                                variant="primary"
                                                size="lg"
                                                style={{ marginTop: 24, width: '100%' }}
                                                onPress={handleFileUpload}
                                                disabled={!title}
                                            />
                                        </View>
                                    </View>
                                )}
                            </View>

                            <View style={styles.dividerRow}>
                                <View style={styles.dividerLine} />
                                <Typography variant="meta" color={themeColors.textSecondary} style={{ marginHorizontal: 16 }}>
                                    OR
                                </Typography>
                                <View style={styles.dividerLine} />
                            </View>

                            <View style={styles.urlSection}>
                                <Typography variant="headingSm" color={themeColors.textPrimary} style={{ marginBottom: 12 }}>
                                    Import from URL
                                </Typography>
                                <View style={styles.urlInputRow}>
                                    <View style={styles.inputWrapper}>
                                        <LinkIcon color={themeColors.textSecondary} size={18} style={styles.inputIcon} />
                                        <TextInput
                                            style={[styles.textInputRaw, webInputReset]}
                                            placeholder="Paste a YouTube or Kaltura link..."
                                            placeholderTextColor={themeColors.textSecondary}
                                            value={youtubeUrl}
                                            onChangeText={setYoutubeUrl}
                                        />
                                    </View>
                                    <PrimaryButton
                                        label="Import"
                                        onPress={handleUrlImport}
                                        disabled={!youtubeUrl || !title}
                                    />
                                </View>
                            </View>
                        </>
                    )}
                </View>
            </FloatingShell>
        </View>
    );
}

const getStyles = (themeColors: ReturnType<typeof useThemeColors>) => StyleSheet.create({
    backdrop: {
        flex: 1,
        backgroundColor: 'rgba(10, 18, 20, 0.4)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    backdropPressable: {
        ...StyleSheet.absoluteFillObject,
    },
    modalShell: {
        width: '100%',
        maxWidth: 540,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: theme.spacing[32],
    },
    closeBtn: {
        padding: 4,
    },
    content: {
        width: '100%',
    },
    titleSection: {
        marginBottom: theme.spacing[24],
    },
    textInput: {
        backgroundColor: themeColors.surfaceElevated,
        borderWidth: 1,
        borderColor: themeColors.borderSubtle,
        borderRadius: theme.radii.controlSm,
        paddingHorizontal: theme.spacing[16],
        height: 54,
        fontSize: 16,
        color: themeColors.textPrimary,
        fontFamily: 'PlusJakartaSans_500Medium',
        outlineWidth: 0,
    },
    errorBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: themeColors.chipBgFailed,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderRadius: theme.radii.controlSm,
        marginBottom: theme.spacing[20],
    },
    progressSection: {
        backgroundColor: themeColors.surfaceElevated,
        borderWidth: 1,
        borderColor: themeColors.borderSubtle,
        borderRadius: theme.radii.card,
        padding: 24,
        marginBottom: theme.spacing[24],
    },
    progressBarBg: {
        height: 6,
        backgroundColor: themeColors.surfaceBase,
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressBarFill: {
        height: '100%',
        borderRadius: 3,
    },
    progressLabel: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 10,
    },
    dropZone: {
        borderWidth: 2,
        borderColor: themeColors.borderSubtle,
        borderStyle: 'dashed',
        borderRadius: theme.radii.card,
        padding: theme.spacing[40],
        alignItems: 'center',
        backgroundColor: themeColors.surfaceBase,
    },
    selectedFileContainer: {
        width: '100%',
    },
    fileIconRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: theme.spacing[16],
        backgroundColor: themeColors.surfaceElevated,
        borderRadius: theme.radii.controlSm,
        borderWidth: 1,
        borderColor: themeColors.borderSubtle,
    },
    uploadIconCircle: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: themeColors.chipBgReady,
        alignItems: 'center',
        justifyContent: 'center',
    },
    dividerRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: theme.spacing[32],
    },
    dividerLine: {
        flex: 1,
        height: 1,
        backgroundColor: themeColors.borderSubtle,
    },
    urlSection: {
        width: '100%',
    },
    urlInputRow: {
        flexDirection: 'row',
        gap: theme.spacing[12],
    },
    inputWrapper: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: themeColors.surfaceElevated,
        borderWidth: 1,
        borderColor: themeColors.borderSubtle,
        borderRadius: theme.radii.controlSm,
        paddingHorizontal: theme.spacing[16],
        height: 54,
    },
    textInputRaw: {
        flex: 1,
        fontSize: 15,
        color: themeColors.textPrimary,
        fontFamily: 'PlusJakartaSans_500Medium',
        padding: 0,
        outlineWidth: 0,
    },
    inputIcon: {
        marginRight: theme.spacing[12],
    },
});
