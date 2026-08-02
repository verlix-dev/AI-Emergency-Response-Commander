import { create } from "zustand";

import type { IncidentAnalysisResponse } from "@/lib/types";

export type OperationsView = "dashboard" | "resources" | "feed" | "status";

interface UiState {
  isCommandSidebarOpen: boolean;
  setCommandSidebarOpen: (isOpen: boolean) => void;

  /** Which workspace section is showing. */
  activeView: OperationsView;
  setActiveView: (view: OperationsView) => void;

  /** Whether the analyse dialog is open. */
  isAnalyzeOpen: boolean;
  setAnalyzeOpen: (isOpen: boolean) => void;

  /**
   * The analysis currently on the command board.
   *
   * Held in memory alongside the object URL of the analysed image, because the backend stores
   * detections but not the image itself, and the overlay needs the original pixels to draw on.
   */
  activeAnalysis: IncidentAnalysisResponse | null;
  activeImageUrl: string | null;
  setActiveAnalysis: (analysis: IncidentAnalysisResponse, imageUrl: string | null) => void;
  clearActiveAnalysis: () => void;

  /** Incident selected from the feed for review. */
  selectedIncidentId: string | null;
  setSelectedIncidentId: (incidentId: string | null) => void;

  /** Operating region, applied as the location on new analyses. */
  region: string;
  setRegion: (region: string) => void;
}

export const useUiStore = create<UiState>((set, get) => ({
  isCommandSidebarOpen: true,
  setCommandSidebarOpen: (isCommandSidebarOpen) => set({ isCommandSidebarOpen }),

  activeView: "dashboard",
  setActiveView: (activeView) => set({ activeView }),

  isAnalyzeOpen: false,
  setAnalyzeOpen: (isAnalyzeOpen) => set({ isAnalyzeOpen }),

  activeAnalysis: null,
  activeImageUrl: null,
  setActiveAnalysis: (activeAnalysis, activeImageUrl) => {
    const previous = get().activeImageUrl;
    if (previous && previous !== activeImageUrl) URL.revokeObjectURL(previous);
    set({ activeAnalysis, activeImageUrl });
  },
  clearActiveAnalysis: () => {
    const previous = get().activeImageUrl;
    if (previous) URL.revokeObjectURL(previous);
    set({ activeAnalysis: null, activeImageUrl: null });
  },

  selectedIncidentId: null,
  setSelectedIncidentId: (selectedIncidentId) => set({ selectedIncidentId }),

  region: "Central Region",
  setRegion: (region) => set({ region }),
}));
