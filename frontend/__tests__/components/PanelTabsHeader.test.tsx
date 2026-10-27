import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { PanelTabsHeader } from '../../src/components/lecture-detail/PanelTabsHeader';
import { lectureDetailStyles } from '../../src/components/lecture-detail/lectureDetail.styles';

describe('PanelTabsHeader', () => {
    it('calls onChange with selected tab', () => {
        const onChange = jest.fn();
        const { getByText } = render(
            <PanelTabsHeader
                activeTab="transcript"
                onChange={onChange}
                styles={lectureDetailStyles}
            />
        );

        fireEvent.press(getByText('Ask'));
        expect(onChange).toHaveBeenCalledWith('ask');
    });

    it('renders close button only when onClose is provided', () => {
        const withClose = render(
            <PanelTabsHeader
                activeTab="transcript"
                onChange={jest.fn()}
                onClose={jest.fn()}
                styles={lectureDetailStyles}
            />
        );
        const withoutClose = render(
            <PanelTabsHeader
                activeTab="transcript"
                onChange={jest.fn()}
                styles={lectureDetailStyles}
            />
        );

        expect(withClose.queryByTestId('panel-tabs-close')).toBeTruthy();
        expect(withoutClose.queryByTestId('panel-tabs-close')).toBeNull();
    });
});
