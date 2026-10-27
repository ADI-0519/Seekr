import React from 'react';
import { render } from '@testing-library/react-native';

import FooterInfoPage from '../../app/info/[slug]';

const mockGetFooterPage = jest.fn();
const mockUseLocalSearchParams = jest.fn();

jest.mock('expo-router', () => ({
    useLocalSearchParams: () => mockUseLocalSearchParams(),
}));

jest.mock('../../src/content/footerPages', () => ({
    getFooterPage: (...args: unknown[]) => mockGetFooterPage(...args),
}));

jest.mock('../../src/components/info/InfoPageScreen', () => {
    const React = require('react');
    const { Text } = require('react-native');
    return {
        InfoPageScreen: ({ page }: { page?: { slug?: string } }) =>
            React.createElement(Text, null, page?.slug ? `PAGE:${page.slug}` : 'PAGE:none'),
    };
});

describe('info/[slug] route', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('resolves and renders footer page content for slug', () => {
        mockUseLocalSearchParams.mockReturnValue({ slug: 'privacy-policy' });
        mockGetFooterPage.mockReturnValue({ slug: 'privacy-policy' });

        const { getByText } = render(<FooterInfoPage />);

        expect(mockGetFooterPage).toHaveBeenCalledWith('privacy-policy');
        expect(getByText('PAGE:privacy-policy')).toBeTruthy();
    });

    it('passes undefined page when slug is missing', () => {
        mockUseLocalSearchParams.mockReturnValue({});
        mockGetFooterPage.mockReturnValue(undefined);

        const { getByText } = render(<FooterInfoPage />);
        expect(getByText('PAGE:none')).toBeTruthy();
    });
});
