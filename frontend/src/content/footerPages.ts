export interface FooterPageContent {
    slug: string;
    eyebrow: string;
    title: string;
    intro: string;
    sections: Array<{
        title: string;
        body: string[];
    }>;
}

export const FOOTER_PAGES: Record<string, FooterPageContent> = {
    'how-it-works': {
        slug: 'how-it-works',
        eyebrow: 'Product',
        title: 'How Seekr works',
        intro: 'Seekr transforms long-form lecture recordings into a structured study experience that is easier to search, revisit, and use with confidence.',
        sections: [
            {
                title: 'Upload and ingest',
                body: [
                    'A lecture may be uploaded directly or imported from a supported source. Once submitted, the platform stores the original media, generates the required preview assets, and creates the processing job that powers the rest of the workflow.',
                    'Raw assets such as video, extracted audio, thumbnails, and slide-derived images are stored in object storage, while lecture metadata and processing state are maintained in the application database.',
                ],
            },
            {
                title: 'Structure the lecture',
                body: [
                    'Seekr transcribes the lecture, reconstructs readable text, segments the recording into topic-level sections, and generates supporting summaries that make navigation significantly faster.',
                    'Where slides are visible, the pipeline also extracts frames and OCR text so retrieval is informed by both spoken content and on-screen material.',
                ],
            },
            {
                title: 'Make retrieval useful',
                body: [
                    'Search is built around hybrid retrieval rather than simple keyword matching. Dense and sparse retrieval signals are combined and reranked to surface the most useful passages with timestamps attached.',
                    'The aim is not to return a vague reference. The aim is to return the exact moment in the lecture that is worth revisiting.',
                ],
            },
        ],
    },
    changelog: {
        slug: 'changelog',
        eyebrow: 'Product',
        title: 'Changelog',
        intro: 'A concise record of the product refinements and platform work shaping the current Seekr experience.',
        sections: [
            {
                title: 'March 2026',
                body: [
                    'Introduced timestamped semantic search supported by a dedicated retrieval worker, hybrid retrieval, and reranking.',
                    'Added topic-level summaries, richer lecture overviews, slide extraction, and production-ready information pages to make the product more complete and easier to understand.',
                ],
            },
            {
                title: 'Frontend refinement',
                body: [
                    'Refined homepage cards, custom media controls, progress tracking, background modes, and detail-page presentation across light and dark themes.',
                    'Improved navigation, supporting information pages, and overall design polish so the interface presents as a focused, premium study product.',
                ],
            },
            {
                title: 'Platform quality',
                body: [
                    'Stabilised queue-driven retrieval, improved visibility around media processing, and tightened the UI around lecture summaries, topic navigation, and continuous playback state.',
                ],
            },
        ],
    },
    faq: {
        slug: 'faq',
        eyebrow: 'Support',
        title: 'Frequently asked questions',
        intro: 'These are the questions most commonly raised when people begin using Seekr to revise from lecture recordings.',
        sections: [
            {
                title: 'What kind of lectures work best?',
                body: [
                    'Seekr performs best on recordings with clear audio, a single dominant speaker, and visible slide content. The cleaner the recording, the more accurate the transcript, segmentation, and search results will be.',
                    'The platform is designed to remain useful across a wide range of lecture formats, with particularly strong results on well-captured academic recordings.',
                ],
            },
            {
                title: 'Does search only return exact keyword matches?',
                body: [
                    'No. Seekr uses semantic retrieval, which means it can surface relevant explanations even when the wording is not identical to your query. Exact phrasing still matters in some cases, but the system is designed to go beyond basic keyword matching.',
                ],
            },
            {
                title: 'Why does processing take a while after upload?',
                body: [
                    'Processing includes much more than transcription. The pipeline also reconstructs readable sentences, segments the lecture into topics, extracts slide context, generates summaries, and prepares embeddings for retrieval.',
                    'That additional work is what makes the final study experience meaningfully better than a plain video player with captions.',
                ],
            },
            {
                title: 'Can I search across more than one lecture?',
                body: [
                    'Yes. Seekr supports multi-lecture search so you can query across your library, then open a specific lecture result at the relevant timestamp.',
                    'You can also search within a single lecture when you want tighter context and faster revision on one recording.',
                ],
            },
        ],
    },
    about: {
        slug: 'about',
        eyebrow: 'Company',
        title: 'About Seekr',
        intro: 'Seekr was created to solve a simple but persistent problem: valuable lecture content is often buried inside long recordings that are difficult to revisit accurately.',
        sections: [
            {
                title: 'Why it exists',
                body: [
                    'Students rarely want an entire lecture when revising. More often, they want the exact explanation, theorem, derivation, or example that matters at a specific moment.',
                    'Seekr is designed to shorten the distance between a question and the precise point in a lecture where that question is answered.',
                ],
            },
            {
                title: 'What the product values',
                body: [
                    'The product is intended to feel calm, study-oriented, and precise. Retrieval quality matters, but so does the way timestamps, topic boundaries, summaries, and playback controls are presented.',
                    'A strong learning product should make difficult material easier to navigate without making the interface itself feel busy, noisy, or fragile.',
                ],
            },
        ],
    },
    contact: {
        slug: 'contact',
        eyebrow: 'Company',
        title: 'Contact Us',
        intro: 'If you have questions about the platform, need support, or would like to discuss the project, we would be pleased to hear from you.',
        sections: [
            {
                title: 'Contact',
                body: [
                    'Please use the contact form for support requests, product feedback, demonstration enquiries, or collaboration discussions related to Seekr.',
                ],
            },
        ],
    },
    'privacy-policy': {
        slug: 'privacy-policy',
        eyebrow: 'Legal',
        title: 'Privacy Policy',
        intro: 'This Privacy Policy explains how Seekr collects, uses, stores, and protects information associated with access to the platform, lecture uploads, generated study assets, and operational support.',
        sections: [
            {
                title: 'Scope of this policy',
                body: [
                    'This policy applies to information provided or generated when you access or use the Seekr platform, including account-related information, uploaded lecture content, generated metadata, search interactions, and technical information created through normal service operation.',
                    'It reflects the current handling of information within the platform and is intended to provide a clear account of how data is managed across the Seekr experience.',
                ],
            },
            {
                title: 'Information we collect and process',
                body: [
                    'Seekr may process lecture files, transcript text, slide-derived content, summaries, timestamps, search queries, and technical diagnostics required to keep the service reliable and functional.',
                    'Where authentication is enabled, identity data is handled through the configured authentication provider and used by the backend to authorise access to the appropriate application data.',
                ],
            },
            {
                title: 'How information is used',
                body: [
                    'Uploaded and generated content is used to provide core product features such as transcription, topic segmentation, slide extraction, retrieval, playback navigation, and other study-support functionality.',
                    'Operational data may also be used to improve system reliability, diagnose failures, measure processing performance, and maintain service integrity during development.',
                ],
            },
            {
                title: 'Retention and access',
                body: [
                    'Lecture assets and derived records are retained according to the current platform configuration and development environment.',
                    'Retention periods, deletion guarantees, and user rights are intended to be formalised further as the platform continues to mature operationally.',
                ],
            },
        ],
    },
    terms: {
        slug: 'terms',
        eyebrow: 'Legal',
        title: 'Terms of Use',
        intro: 'These Terms of Use set out the rules and expectations governing access to and use of Seekr.',
        sections: [
            {
                title: 'Permitted use',
                body: [
                    'You should only upload, link, or process lecture content that you are authorised to use.',
                    'You remain responsible for ensuring that your use of the platform complies with applicable copyright, privacy, academic, and institutional requirements.',
                ],
            },
            {
                title: 'Service status',
                body: [
                    'Seekr is continuously refined to improve the quality of the study experience, the reliability of processing, and the clarity of the interface.',
                    'As the platform develops, certain features or workflows may be updated in order to enhance performance, usability, and service quality.',
                ],
            },
            {
                title: 'Misuse and restrictions',
                body: [
                    'The service must not be used to distribute unlawful material, interfere with platform reliability, access content belonging to another user without permission, or abuse the processing pipeline in a way that harms service quality for others.',
                    'We reserve the right to restrict or suspend access where use of the platform creates operational, legal, or security risk.',
                ],
            },
        ],
    },
    cookies: {
        slug: 'cookies',
        eyebrow: 'Legal',
        title: 'Cookie Notice',
        intro: 'This Cookie Notice explains how browser-side storage and related technologies may be used to support the Seekr web experience.',
        sections: [
            {
                title: 'How browser storage may be used',
                body: [
                    'Browser storage can help preserve session state, remember interface preferences, support security-sensitive flows, and improve continuity between visits.',
                    'During development, lightweight browser storage may also be used for interface state, preferences, and implementation-specific behaviour that improves usability while the product is being refined.',
                ],
            },
            {
                title: 'Analytics, consent, and future review',
                body: [
                    'Any future analytics, consent handling, and preference controls should be documented explicitly in a final reviewed notice.',
                    'This notice is intended to provide a clear overview of current browser-side storage practices and can be expanded as the platform evolves.',
                ],
            },
        ],
    },
};

export const getFooterPage = (slug: string) => FOOTER_PAGES[slug];
