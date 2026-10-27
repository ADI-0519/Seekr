import type { User as FirebaseUser } from 'firebase/auth';

const mockInitializeApp = jest.fn(() => ({ name: 'firebase-app' }));
const mockGetApps = jest.fn(() => []);
const mockGetApp = jest.fn(() => ({ name: 'firebase-app' }));
const mockUpdateProfile = jest.fn();
const mockCreateUserWithEmailAndPassword = jest.fn();
const mockSignInWithEmailAndPassword = jest.fn();
const mockGetAuth = jest.fn(() => ({ currentUser: null as FirebaseUser | null }));
const mockFirebaseConfig = {
    apiKey: 'test-api-key',
    authDomain: 'seekr.firebaseapp.com',
    projectId: 'seekr-test',
    appId: 'test-app-id',
};

jest.mock('firebase/app', () => ({
    initializeApp: mockInitializeApp,
    getApps: mockGetApps,
    getApp: mockGetApp,
}));

jest.mock('firebase/auth', () => ({
    getAuth: mockGetAuth,
    signInWithEmailAndPassword: mockSignInWithEmailAndPassword,
    createUserWithEmailAndPassword: mockCreateUserWithEmailAndPassword,
    signOut: jest.fn(),
    sendPasswordResetEmail: jest.fn(),
    onAuthStateChanged: jest.fn(),
    updateProfile: mockUpdateProfile,
    GoogleAuthProvider: jest.fn(),
    signInWithPopup: jest.fn(),
    getAdditionalUserInfo: jest.fn(),
}));

jest.mock('react-native', () => ({
    Platform: { OS: 'web' },
}));

jest.mock('@/constants', () => ({
    FIREBASE_CONFIG: mockFirebaseConfig,
    FEATURES: {
        enableMockAuth: false,
        enableMockData: false,
    },
}));

const loadAuthService = () => require('../../src/services/auth').authService;

describe('authService', () => {
    const baseUser = {
        uid: 'user-123',
        email: 'test@example.com',
        displayName: 'Test User',
        photoURL: null,
        metadata: { creationTime: '2024-01-01T00:00:00.000Z' },
        getIdToken: jest.fn().mockResolvedValue('token-123'),
    } as unknown as FirebaseUser;

    beforeEach(() => {
        jest.resetModules();
        jest.clearAllMocks();
        Object.assign(mockFirebaseConfig, {
            apiKey: 'test-api-key',
            authDomain: 'seekr.firebaseapp.com',
            projectId: 'seekr-test',
            appId: 'test-app-id',
        });
        mockGetApps.mockReturnValue([]);
        mockGetAuth.mockReturnValue({ currentUser: baseUser });
        mockCreateUserWithEmailAndPassword.mockResolvedValue({ user: baseUser });
        mockSignInWithEmailAndPassword.mockResolvedValue({ user: baseUser });
        mockUpdateProfile.mockResolvedValue(undefined);
    });

    it('signs up with email/password and sets display name', async () => {
        const authService = loadAuthService();

        const user = await authService.signUp('test@example.com', 'secret123', 'Alice');

        expect(user.displayName).toBe('Test User');
        expect(mockCreateUserWithEmailAndPassword).toHaveBeenCalled();
        expect(mockUpdateProfile).toHaveBeenCalledWith(baseUser, { displayName: 'Alice' });
    });

    it('signs in with email/password', async () => {
        const authService = loadAuthService();

        const user = await authService.signIn('test@example.com', 'secret123');

        expect(user.id).toBe('user-123');
        expect(mockSignInWithEmailAndPassword).toHaveBeenCalled();
    });

    it('throws a clear error when required Firebase env vars are missing', async () => {
        Object.assign(mockFirebaseConfig, {
            apiKey: '',
            authDomain: '',
            projectId: '',
            appId: '',
        });
        const authService = loadAuthService();

        await expect(authService.signUp('test@example.com', 'secret123', 'Alice')).rejects.toThrow(
            'Firebase Auth is not configured. Missing env vars: EXPO_PUBLIC_FIREBASE_API_KEY, EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN, EXPO_PUBLIC_FIREBASE_PROJECT_ID, EXPO_PUBLIC_FIREBASE_APP_ID.'
        );
    });

    it('returns ID token when current user exists', async () => {
        const authService = loadAuthService();

        const token = await authService.getIdToken();

        expect(token).toBe('token-123');
        expect(baseUser.getIdToken).toHaveBeenCalled();
    });
});
