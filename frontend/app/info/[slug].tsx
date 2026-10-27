import React from 'react';
import { useLocalSearchParams } from 'expo-router';
import { getFooterPage } from '../../src/content/footerPages';
import { InfoPageScreen } from '../../src/components/info/InfoPageScreen';

const EXTERNAL_LINKS: Record<string, string> = {};

export default function FooterInfoPage() {
    const { slug } = useLocalSearchParams<{ slug: string }>();
    const page = slug ? getFooterPage(slug) : undefined;
    return <InfoPageScreen page={page} externalHref={page ? EXTERNAL_LINKS[page.slug] : undefined} />;
}
