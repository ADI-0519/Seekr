import { useSidebarStore } from '../../src/store/sidebarStore';

describe('useSidebarStore', () => {
    beforeEach(() => {
        // Reset state before each test
        useSidebarStore.setState({ isManuallyCollapsed: false });
    });

    it('should have initial state of false', () => {
        expect(useSidebarStore.getState().isManuallyCollapsed).toBe(false);
    });

    it('should toggle manually collapsed state', () => {
        const { toggleSidebar } = useSidebarStore.getState();
        toggleSidebar();
        expect(useSidebarStore.getState().isManuallyCollapsed).toBe(true);
        toggleSidebar();
        expect(useSidebarStore.getState().isManuallyCollapsed).toBe(false);
    });

    it('should explicitly set sidebar collapsed state', () => {
        const { setSidebarCollapsed } = useSidebarStore.getState();
        setSidebarCollapsed(true);
        expect(useSidebarStore.getState().isManuallyCollapsed).toBe(true);
        setSidebarCollapsed(false);
        expect(useSidebarStore.getState().isManuallyCollapsed).toBe(false);
    });
});
