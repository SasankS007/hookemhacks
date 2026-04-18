import { create } from "zustand";

export type StrokeType = "forehand" | "backhand" | "volley" | "slice";
export type AppMode = "stroke-analysis" | "ai-rally" | "footage" | null;

interface SessionEntry {
  id: string;
  mode: AppMode;
  date: string;
  summary: string;
}

interface AppState {
  currentMode: AppMode;
  selectedStroke: StrokeType;
  sessionHistory: SessionEntry[];
  setCurrentMode: (mode: AppMode) => void;
  setSelectedStroke: (stroke: StrokeType) => void;
  addSession: (entry: SessionEntry) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentMode: null,
  selectedStroke: "forehand",
  sessionHistory: [
    {
      id: "1",
      mode: "stroke-analysis",
      date: "2025-04-17",
      summary: "Forehand drill — 87% form accuracy",
    },
    {
      id: "2",
      mode: "ai-rally",
      date: "2025-04-16",
      summary: "AI Rally — Won 11-7 on Medium",
    },
    {
      id: "3",
      mode: "footage",
      date: "2025-04-15",
      summary: "Match footage analyzed — 142 shots tracked",
    },
    {
      id: "4",
      mode: "stroke-analysis",
      date: "2025-04-14",
      summary: "Backhand session — improved 12%",
    },
    {
      id: "5",
      mode: "ai-rally",
      date: "2025-04-13",
      summary: "AI Rally — Lost 8-11 on Hard",
    },
  ],
  setCurrentMode: (mode) => set({ currentMode: mode }),
  setSelectedStroke: (stroke) => set({ selectedStroke: stroke }),
  addSession: (entry) =>
    set((state) => ({ sessionHistory: [entry, ...state.sessionHistory] })),
}));
