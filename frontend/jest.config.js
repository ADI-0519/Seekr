module.exports = {
    preset: 'jest-expo',
    maxWorkers: 1,
    transformIgnorePatterns: [
        'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|zustand)',
    ],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
    },
    testMatch: ['**/__tests__/**/*.test.ts?(x)', '**/*.test.ts?(x)'],
    testPathIgnorePatterns: ['/node_modules/'],
    collectCoverageFrom: [
        'app/**/*.{ts,tsx}',
        'src/**/*.{ts,tsx}',
        '!**/__tests__/**',
        '!**/*.test.{ts,tsx}',
        '!**/*.perf-test.{ts,tsx}',
        '!e2e/**',
        '!**/node_modules/**',
        '!**/vendor/**',
        '!**/*.d.ts',
    ],
    coverageThreshold: {
        global: {
            statements: 40,
            branches: 35,
            functions: 40,
            lines: 40,
        },
    },
    testEnvironment: 'node',
};
