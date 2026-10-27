import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signOut as firebaseSignOut,
    sendPasswordResetEmail,
    onAuthStateChanged,
    User as FirebaseUser,
    updateProfile,
    Auth,
    GoogleAuthProvider,
    signInWithPopup,
    getAdditionalUserInfo,
} from 'firebase/auth';
import { Platform } from 'react-native';
import { FIREBASE_CONFIG, FEATURES } from '@/constants';
import { User } from '@/types';

const mockUser: User = {
    id: 'mock-user-1',
    email: 'demo@seekr.app',
    displayName: 'Demo User',
    photoURL: null,
    createdAt: new Date().toISOString(),
};

const FIREBASE_ENV_VARS = {
    apiKey: 'EXPO_PUBLIC_FIREBASE_API_KEY',
    authDomain: 'EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN',
    projectId: 'EXPO_PUBLIC_FIREBASE_PROJECT_ID',
    appId: 'EXPO_PUBLIC_FIREBASE_APP_ID',
} as const;

type RequiredFirebaseConfigKey = keyof typeof FIREBASE_ENV_VARS;

let app: FirebaseApp | undefined;
let auth: Auth | undefined;

const getMissingFirebaseConfigEnvVars = () =>
    (Object.keys(FIREBASE_ENV_VARS) as RequiredFirebaseConfigKey[])
        .filter(key => !FIREBASE_CONFIG[key])
        .map(key => FIREBASE_ENV_VARS[key]);

const getFirebaseSetupError = () => {
    const missingEnvVars = getMissingFirebaseConfigEnvVars();
    if (missingEnvVars.length > 0) {
        return new Error(`Firebase Auth is not configured. Missing env vars: ${missingEnvVars.join(', ')}.`);
    }
    return new Error('Firebase Auth is unavailable. Check Firebase initialization.');
};

const getErrorDetails = (error: unknown) => {
    if (error instanceof Error) {
        return { message: error.message, stack: error.stack };
    }
    return { message: String(error) };
};

const logAuthInfo = (message: string, details?: Record<string, unknown>) => {
    console.info(`[Auth] ${message}`, details ?? {});
};

const logAuthError = (message: string, error: unknown, details?: Record<string, unknown>) => {
    console.error(`[Auth] ${message}`, {
        ...details,
        ...getErrorDetails(error),
    });
};

const initializeFirebase = () => {
    if (FEATURES.enableMockAuth) return null;

    const missingEnvVars = getMissingFirebaseConfigEnvVars();
    if (missingEnvVars.length > 0) {
        console.error('[Auth] Firebase configuration is incomplete.', { missingEnvVars });
        return null;
    }

    try {
        if (getApps().length === 0) {
            app = initializeApp(FIREBASE_CONFIG);
        } else {
            app = getApp();
        }
        auth = getAuth(app);
        logAuthInfo('Firebase initialized.', {
            platform: Platform.OS,
            projectId: FIREBASE_CONFIG.projectId,
        });
        return auth;
    } catch (error) {
        logAuthError('Firebase initialization failed.', error, {
            platform: Platform.OS,
            projectId: FIREBASE_CONFIG.projectId,
        });
        return null;
    }
};

const getConfiguredAuthOrThrow = (operation: string) => {
    if (!auth) {
        const error = getFirebaseSetupError();
        logAuthError(`${operation} blocked because Firebase Auth is unavailable.`, error);
        throw error;
    }
    return auth;
};

const firebaseToUser = (fbUser: FirebaseUser): User => ({
    id: fbUser.uid,
    email: fbUser.email || '',
    displayName: fbUser.displayName,
    photoURL: fbUser.photoURL,
    createdAt: fbUser.metadata.creationTime || new Date().toISOString(),
});

class AuthService {
    constructor() {
        initializeFirebase();
    }

    async signIn(email: string, password: string): Promise<User> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 500));
            if (email && password.length >= 6) {
                return { ...mockUser, email };
            }
            throw new Error('Invalid credentials');
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Sign-in');
        logAuthInfo('Starting email sign-in.', { email });

        const result = await signInWithEmailAndPassword(firebaseAuth, email, password);
        logAuthInfo('Email sign-in succeeded.', { uid: result.user.uid, email });
        return firebaseToUser(result.user);
    }

    async signUp(email: string, password: string, displayName: string): Promise<User> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 500));
            return { ...mockUser, email, displayName };
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Sign-up');
        logAuthInfo('Starting email sign-up.', {
            email,
            hasDisplayName: Boolean(displayName),
        });

        try {
            const result = await createUserWithEmailAndPassword(firebaseAuth, email, password);
            if (displayName) {
                await updateProfile(result.user, { displayName });
            }
            logAuthInfo('Email sign-up succeeded.', { uid: result.user.uid, email });
            return firebaseToUser(result.user);
        } catch (error) {
            logAuthError('Email sign-up failed.', error, { email });
            throw error;
        }
    }

    async signInWithGoogle(): Promise<User> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 500));
            return { ...mockUser, email: 'demo.google@seekr.app', displayName: 'Demo Google User' };
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Google sign-in');

        if (Platform.OS !== 'web') {
            throw new Error('Google auth on native requires Expo Auth Session setup and Google client IDs.');
        }

        const provider = new GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });
        logAuthInfo('Starting Google sign-in.', { platform: Platform.OS });
        const result = await signInWithPopup(firebaseAuth, provider);
        await result.user.getIdToken(true);
        const additionalInfo = getAdditionalUserInfo(result);

        logAuthInfo('Google sign-in succeeded.', {
            uid: result.user.uid,
            isNewUser: additionalInfo?.isNewUser ?? false,
        });
        return firebaseToUser(result.user);
    }

    async signUpWithGoogle(): Promise<User> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 500));
            const now = new Date().toISOString();
            return { ...mockUser, email: 'demo.google@seekr.app', displayName: 'Demo Google User', createdAt: now };
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Google sign-up');

        if (Platform.OS !== 'web') {
            throw new Error('Google auth on native requires Expo Auth Session setup and Google client IDs.');
        }

        const provider = new GoogleAuthProvider();
        provider.setCustomParameters({ prompt: 'select_account' });
        logAuthInfo('Starting Google sign-up.', { platform: Platform.OS });
        const result = await signInWithPopup(firebaseAuth, provider);
        await result.user.getIdToken(true);
        const additionalInfo = getAdditionalUserInfo(result);

        logAuthInfo('Google sign-up succeeded.', {
            uid: result.user.uid,
            isNewUser: additionalInfo?.isNewUser ?? false,
        });
        return firebaseToUser(result.user);
    }

    async signOut(): Promise<void> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 200));
            return;
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Sign-out');
        await firebaseSignOut(firebaseAuth);
    }

    async resetPassword(email: string): Promise<void> {
        if (FEATURES.enableMockAuth) {
            await new Promise(resolve => setTimeout(resolve, 500));
            return;
        }

        const firebaseAuth = getConfiguredAuthOrThrow('Password reset');
        await sendPasswordResetEmail(firebaseAuth, email);
    }

    getCurrentUser(): User | null {
        if (FEATURES.enableMockAuth || !auth) {
            return null;
        }

        const fbUser = auth.currentUser;
        return fbUser ? firebaseToUser(fbUser) : null;
    }

    onAuthStateChange(callback: (user: User | null) => void): () => void {
        if (FEATURES.enableMockAuth || !auth) {
            callback(null);
            return () => { };
        }

        return onAuthStateChanged(auth, (fbUser) => {
            callback(fbUser ? firebaseToUser(fbUser) : null);
        });
    }

    async getIdToken(forceRefresh = false): Promise<string | null> {
        if (FEATURES.enableMockAuth) {
            return 'mock-token-12345';
        }

        const user = auth?.currentUser;
        if (!user) return null;
        return user.getIdToken(forceRefresh);
    }
}

export const authService = new AuthService();
