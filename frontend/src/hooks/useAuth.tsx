import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User } from '@/types';
import { authService, api } from '@/services';
import { useQueryClient } from '@tanstack/react-query';
import { useVideoPlayerStore } from '@/store/videoStore';

const NOTES_CACHE_PREFIX = 'seekr_notes_';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isInitializing: boolean;
    isAuthenticated: boolean;
    signIn: (email: string, password: string) => Promise<void>;
    signUp: (email: string, password: string, displayName: string) => Promise<void>;
    signInWithGoogle: () => Promise<void>;
    signUpWithGoogle: () => Promise<void>;
    signOut: () => Promise<void>;
    resetPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isInitializing, setIsInitializing] = useState(true);
    const lastSyncedUidRef = useRef<string | null>(null);
    const currentUidRef = useRef<string | null>(null);
    const queryClient = useQueryClient();

    const clearNotesStorageCache = async () => {
        try {
            const keys = await AsyncStorage.getAllKeys();
            const noteKeys = keys.filter((key) => key.startsWith(NOTES_CACHE_PREFIX));
            if (noteKeys.length > 0) {
                await AsyncStorage.multiRemove(noteKeys);
            }
        } catch {
            // Ignore note-cache cleanup failures.
        }
    };

    const syncProfile = async (u: User | null) => {
        if (!u) return;
        if (lastSyncedUidRef.current === u.id) return;
        try {
            await api.syncMyProfile({
                displayName: u.displayName,
                photoURL: u.photoURL,
            });
            lastSyncedUidRef.current = u.id;
        } catch (error) {
            console.warn('[Auth] Profile sync failed:', error);
            lastSyncedUidRef.current = null;
        }
    };

    useEffect(() => {
        const unsubscribe = authService.onAuthStateChange((nextUser) => {
            const nextUid = nextUser?.id ?? null;
            const previousUid = currentUidRef.current;
            const authIdentityChanged = previousUid !== nextUid;

            if (authIdentityChanged) {
                // Reset user-scoped playback and lecture caches when the auth identity changes.
                useVideoPlayerStore.getState().clearProgress();
                void clearNotesStorageCache();
                queryClient.removeQueries({ queryKey: ['lecture'] });
                queryClient.removeQueries({ queryKey: ['transcript'] });
                queryClient.removeQueries({ queryKey: ['topics'] });
                queryClient.removeQueries({ queryKey: ['notes'] });
                queryClient.removeQueries({ queryKey: ['slides'] });
            }

            setUser(nextUser);
            if (nextUser) {
                void syncProfile(nextUser);
                void queryClient.invalidateQueries({ queryKey: ['lectures'] });
                void queryClient.invalidateQueries({ queryKey: ['profileSummary'] });
                void queryClient.invalidateQueries({ queryKey: ['profileSettings'] });
            } else {
                lastSyncedUidRef.current = null;
                // Clear player state and user-scoped caches on logout.
                useVideoPlayerStore.getState().unloadSession();
                queryClient.removeQueries({ queryKey: ['lectures'] });
                queryClient.removeQueries({ queryKey: ['profileSummary'] });
                queryClient.removeQueries({ queryKey: ['profileSettings'] });
                queryClient.removeQueries({ queryKey: ['lecture'] });
                queryClient.removeQueries({ queryKey: ['transcript'] });
                queryClient.removeQueries({ queryKey: ['topics'] });
                queryClient.removeQueries({ queryKey: ['notes'] });
                queryClient.removeQueries({ queryKey: ['slides'] });
            }
            currentUidRef.current = nextUid;
            setIsInitializing(false);
        });

        return unsubscribe;
    }, [queryClient]);


    const signIn = async (email: string, password: string) => {
        setIsLoading(true);
        try {
            const user = await authService.signIn(email, password);
            setUser(user);
        } finally {
            setIsLoading(false);
        }
    };

    const signUp = async (email: string, password: string, displayName: string) => {
        setIsLoading(true);
        try {
            const user = await authService.signUp(email, password, displayName);
            setUser(user);
        } finally {
            setIsLoading(false);
        }
    };

    const signInWithGoogle = async () => {
        setIsLoading(true);
        try {
            const user = await authService.signInWithGoogle();
            setUser(user);
        } finally {
            setIsLoading(false);
        }
    };

    const signUpWithGoogle = async () => {
        setIsLoading(true);
        try {
            const user = await authService.signUpWithGoogle();
            setUser(user);
        } finally {
            setIsLoading(false);
        }
    };

    const signOut = async () => {
        setIsLoading(true);
        try {
            await authService.signOut();
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    const resetPassword = async (email: string) => {
        setIsLoading(true);
        try {
            await authService.resetPassword(email);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isInitializing,
                isAuthenticated: !!user,
                signIn,
                signUp,
                signInWithGoogle,
                signUpWithGoogle,
                signOut,
                resetPassword,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
