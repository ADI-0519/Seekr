import { create } from 'zustand';

interface SidebarState {
    isManuallyCollapsed: boolean;
    toggleSidebar: () => void;
    setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
    isManuallyCollapsed: false,
    toggleSidebar: () => set((state) => ({ isManuallyCollapsed: !state.isManuallyCollapsed })),
    setSidebarCollapsed: (collapsed) => set({ isManuallyCollapsed: collapsed }),
}));
