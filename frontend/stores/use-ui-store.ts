import { create } from "zustand";

interface UiState {
  isCommandSidebarOpen: boolean;
  setCommandSidebarOpen: (isOpen: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  isCommandSidebarOpen: true,
  setCommandSidebarOpen: (isCommandSidebarOpen) => set({ isCommandSidebarOpen }),
}));
