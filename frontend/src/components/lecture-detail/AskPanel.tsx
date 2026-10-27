import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Image, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { MessageCircleQuestion, Send } from 'lucide-react-native';

import { useLectureQuery } from '@/hooks';
import { useThemeColors } from '@/theme/ThemeProvider';
import { Typography } from '@/components/ui/Typography';
import { api } from '@/services';
import type { LectureDetailStyles } from './lectureDetail.styles';

import { ChatBubbleAnimated, InlineAnswerText, LoadingDots, RetrievalResults } from './ask/MessagePieces';
import { ChatMessage } from './ask/types';
export const AskPanel = ({
    lectureId,
    onSeek,
    styles,
}: {
    lectureId: string;
    onSeek: (time: number) => void;
    styles: LectureDetailStyles;
}) => {
    const themeColors = useThemeColors();
    const queryMutation = useLectureQuery(lectureId);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [inputFocused, setInputFocused] = useState(false);
    const scrollRef = useRef<ScrollView>(null);

    useEffect(() => {
        if (Platform.OS !== 'web') return;
        const id = 'seekr-ask-pulse-keyframes';
        if (document.getElementById(id)) return;
        const style = document.createElement('style');
        style.id = id;
        style.textContent = [
            '@keyframes askPulse { 0%,80%,100%{opacity:0.3;transform:scale(0.8)} 40%{opacity:1;transform:scale(1.1)} }',
            '@keyframes seekrTipIn { from{opacity:0;transform:translateY(3px)} to{opacity:1;transform:translateY(0)} }',
        ].join(' ');
        document.head.appendChild(style);
    }, []);

    useEffect(() => {
        let cancelled = false;
        api.getChatHistory(lectureId).then((res) => {
            if (cancelled || !res.data?.length) return;
            const loaded: ChatMessage[] = res.data.map((m: any) => ({
                id: `db-${m.id}`,
                role: m.role,
                text: m.text || undefined,
                mode: m.mode || undefined,
                citations: m.citations_json ? JSON.parse(m.citations_json) : undefined,
                results: m.results_json ? JSON.parse(m.results_json) : undefined,
            }));
            setMessages(loaded);
        });
        return () => {
            cancelled = true;
        };
    }, [lectureId]);

    const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const persistMessages = useCallback(
        (messageList: ChatMessage[]) => {
            const toSave = messageList.map((m) => ({
                role: m.role,
                text: m.text || null,
                mode: m.mode || null,
                citations_json: m.citations ? JSON.stringify(m.citations) : null,
                results_json: m.results ? JSON.stringify(m.results) : null,
            }));
            api.saveChatHistory(lectureId, toSave);
        },
        [lectureId]
    );

    useEffect(() => {
        if (!messages.length) return;
        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        const pendingMessages = [...messages];
        saveTimeoutRef.current = setTimeout(() => {
            persistMessages(pendingMessages);
            saveTimeoutRef.current = null;
        }, 1000);
        return () => {
            if (saveTimeoutRef.current) {
                clearTimeout(saveTimeoutRef.current);
                saveTimeoutRef.current = null;
                persistMessages(pendingMessages);
            }
        };
    }, [messages, persistMessages]);

    const submitQuery = useCallback(
        (text: string, modeOverride?: 'retrieval' | 'qa') => {
            const q = text.trim();
            if (!q || queryMutation.isPending) return;

            const userMsg: ChatMessage = {
                id: `user-${Date.now()}`,
                role: 'user',
                text: q,
            };
            setMessages((prev) => [...prev, userMsg]);
            if (!modeOverride) setInput('');

            queryMutation.mutate(
                { query: q, mode: modeOverride ?? 'auto' },
                {
                    onSuccess: (response: any) => {
                        const { mode, results, answer, citations } = response.data;
                        const aiMsg: ChatMessage = {
                            id: `ai-${Date.now()}`,
                            role: 'assistant',
                            mode,
                            text: mode === 'qa' ? answer : undefined,
                            citations: mode === 'qa' ? citations : undefined,
                            results: mode === 'retrieval' ? results : undefined,
                        };
                        setMessages((prev) => [...prev, aiMsg]);
                    },
                    onError: () => {
                        const errMsg: ChatMessage = {
                            id: `err-${Date.now()}`,
                            role: 'assistant',
                            text: 'Sorry, something went wrong. Please try again.',
                        };
                        setMessages((prev) => [...prev, errMsg]);
                    },
                }
            );
        },
        [queryMutation]
    );

    const handleSend = useCallback(() => {
        submitQuery(input);
    }, [input, submitQuery]);

    useEffect(() => {
        setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    }, [messages.length]);

    const handleKeyPress = (e: any) => {
        if (Platform.OS === 'web' && e.nativeEvent?.key === 'Enter' && !e.nativeEvent?.shiftKey) {
            e.preventDefault?.();
            handleSend();
        }
    };

    const inputWrapperFocusStyle =
        Platform.OS === 'web' && inputFocused
            ? ({
                  borderColor: themeColors.primaryEmerald,
                  boxShadow: `0 0 0 3px rgba(16, 185, 129, 0.15)`,
              } as any)
            : {};

    const getLastUserQuery = (msgIndex: number): string => {
        for (let i = msgIndex - 1; i >= 0; i--) {
            if (messages[i].role === 'user' && messages[i].text) return messages[i].text!;
        }
        return '';
    };

    return (
        <View style={styles.askPanelContainer}>
            <ScrollView
                ref={scrollRef}
                style={styles.askMessagesScroll}
                contentContainerStyle={styles.askMessagesContent}
                showsVerticalScrollIndicator
            >
                {messages.length === 0 && (
                    <View style={styles.askEmptyState}>
                        <MessageCircleQuestion
                            color={themeColors.textSecondary}
                            size={40}
                            style={{ marginBottom: 12, opacity: 0.5 }}
                        />
                        <Typography variant="bodyLg" color={themeColors.textSecondary} style={{ textAlign: 'center' }}>
                            Ask a question or search this lecture
                        </Typography>
                        <Typography
                            variant="bodySm"
                            color={themeColors.textSecondary}
                            style={{ textAlign: 'center', marginTop: 8, opacity: 0.7 }}
                        >
                            Try "when is X covered" or "explain how X works"
                        </Typography>
                    </View>
                )}
                {messages.map((msg, index) => (
                    <ChatBubbleAnimated key={msg.id} index={index}>
                        {msg.role === 'user' ? (
                            <View style={[styles.chatBubble, styles.chatBubbleUser, { backgroundColor: themeColors.primaryEmerald }]}>
                                <Typography variant="bodyLg" color="#FFFFFF" style={{ fontSize: 17, lineHeight: 27 }}>
                                    {msg.text}
                                </Typography>
                            </View>
                        ) : (
                            <>
                                <View style={styles.botHeader}>
                                    <View style={[styles.botAvatarBadge, { backgroundColor: themeColors.chipBgReady, width: 28, height: 28, borderRadius: 14 }]}>
                                        <Image
                                            source={require('../../../assets/seekr-logo.png')}
                                            style={{ width: 18, height: 18 }}
                                            resizeMode="contain"
                                        />
                                    </View>
                                    <Typography variant="meta" color={themeColors.textSecondary} style={styles.botHeaderLabel}>
                                        SEEKR AI
                                    </Typography>
                                </View>

                                <View
                                    style={[
                                        styles.chatBubble,
                                        styles.chatBubbleAi,
                                        {
                                            backgroundColor: themeColors.surfaceElevated,
                                            borderColor: themeColors.borderSubtle,
                                        },
                                    ]}
                                >
                                    {msg.mode === 'retrieval' ? (
                                        <RetrievalResults results={msg.results ?? []} onSeek={onSeek} styles={styles} />
                                    ) : (
                                        <InlineAnswerText text={msg.text ?? ''} citations={msg.citations ?? []} onSeek={onSeek} />
                                    )}
                                </View>

                                {msg.mode && (
                                    <Pressable
                                        onPress={() =>
                                            submitQuery(
                                                getLastUserQuery(index),
                                                msg.mode === 'retrieval' ? 'qa' : 'retrieval'
                                            )
                                        }
                                        style={{ marginTop: 6, paddingLeft: 2 }}
                                    >
                                        <Typography
                                            variant="bodySm"
                                            color={themeColors.textSecondary}
                                            style={{ opacity: 0.7, textDecorationLine: 'underline', fontSize: 14 }}
                                        >
                                            {msg.mode === 'retrieval'
                                                ? 'Looking for an explanation instead →'
                                                : 'See matching moments instead →'}
                                        </Typography>
                                    </Pressable>
                                )}
                            </>
                        )}
                    </ChatBubbleAnimated>
                ))}
                {queryMutation.isPending && (
                    <ChatBubbleAnimated index={messages.length}>
                        <View style={styles.botHeader}>
                            <View style={[styles.botAvatarBadge, { backgroundColor: themeColors.chipBgReady, width: 28, height: 28, borderRadius: 14 }]}>
                                <Image
                                    source={require('../../../assets/seekr-logo.png')}
                                    style={{ width: 18, height: 18 }}
                                    resizeMode="contain"
                                />
                            </View>
                            <Typography variant="meta" color={themeColors.textSecondary} style={styles.botHeaderLabel}>
                                SEEKR AI
                            </Typography>
                        </View>
                        <View
                            style={[
                                styles.chatBubble,
                                styles.chatBubbleAi,
                                { backgroundColor: themeColors.surfaceElevated, borderColor: themeColors.borderSubtle },
                            ]}
                        >
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                                <Typography
                                    variant="bodyMd"
                                    color={themeColors.textSecondary}
                                    style={{ fontStyle: 'italic', fontSize: 16, lineHeight: 24 }}
                                >
                                    Searching lecture content
                                </Typography>
                                <LoadingDots />
                            </View>
                        </View>
                    </ChatBubbleAnimated>
                )}
            </ScrollView>

            <View
                style={[
                    styles.askInputBar,
                    {
                        borderTopColor: themeColors.borderSubtle,
                        backgroundColor: themeColors.surfaceElevated,
                    },
                    Platform.OS === 'web'
                        ? ({
                              backdropFilter: 'blur(20px)',
                              WebkitBackdropFilter: 'blur(20px)',
                          } as any)
                        : null,
                ]}
            >
                <View
                    style={[
                        styles.askInputWrapper,
                        { borderColor: themeColors.borderSubtle },
                        inputWrapperFocusStyle,
                    ]}
                >
                    <TextInput
                        value={input}
                        onChangeText={setInput}
                        placeholder="Ask a question or search this lecture..."
                        placeholderTextColor={themeColors.textSecondary}
                        style={[
                            styles.askInput,
                            { color: themeColors.textPrimary },
                            Platform.OS === 'web'
                                ? ({ outlineStyle: 'none', outlineWidth: 0, boxShadow: 'none' } as any)
                                : null,
                        ]}
                        onKeyPress={handleKeyPress}
                        onFocus={() => setInputFocused(true)}
                        onBlur={() => setInputFocused(false)}
                        editable={!queryMutation.isPending}
                        multiline={false}
                    />
                    <Pressable
                        onPress={handleSend}
                        style={[
                            styles.askSendButton,
                            {
                                backgroundColor:
                                    input.trim() && !queryMutation.isPending
                                        ? themeColors.primaryEmerald
                                        : themeColors.borderSubtle,
                            },
                        ]}
                        disabled={!input.trim() || queryMutation.isPending}
                    >
                        <Send color="#FFFFFF" size={16} />
                    </Pressable>
                </View>
                <Typography variant="meta" color={themeColors.textSecondary} style={styles.askDisclaimer}>
                    Seekr AI can make mistakes. Check important info.
                </Typography>
            </View>
        </View>
    );
};
