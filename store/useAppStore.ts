import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { supabase } from "@/lib/supabase";

export type StrokeType = "forehand" | "backhand" | "volley" | "slice";
export type AppMode = "stroke-analysis" | "ai-rally" | null;
export type ArenaDifficulty = "easy" | "medium" | "hard";

interface SessionEntry {
  id: string;
  mode: AppMode;
  date: string;
  summary: string;
}

/** Saved rep from The Dojo (stroke analysis). */
export interface DojoStrokeSave {
  id: string;
  date: string;
  strokeLabel: string;
  score: number;
  phase?: string;
  note?: string;
}

/** Finished Rally Arena match. */
export interface ArenaMatchSave {
  id: string;
  date: string;
  difficulty: ArenaDifficulty;
  won: boolean;
  playerScore: number;
  aiScore: number;
  trophyEarned: boolean;
}

export interface ArenaDifficultyStats {
  wins: number;
  losses: number;
}

interface AppState {
  currentMode: AppMode;
  selectedStroke: StrokeType;
  sessionHistory: SessionEntry[];
  /** Total arena wins — each win adds a trophy stack unit. */
  trophyCount: number;
  arenaStats: Record<ArenaDifficulty, ArenaDifficultyStats>;
  dojoSaves: DojoStrokeSave[];
  arenaMatches: ArenaMatchSave[];
  setCurrentMode: (mode: AppMode) => void;
  setSelectedStroke: (stroke: StrokeType) => void;
  addSession: (entry: SessionEntry) => void;
  saveDojoStroke: (payload: Omit<DojoStrokeSave, "id" | "date"> & { id?: string }) => void;
  recordArenaMatch: (payload: {
    difficulty: ArenaDifficulty;
    won: boolean;
    playerScore: number;
    aiScore: number;
  }) => void;
  syncFromSupabaseForUser: (userId: string) => Promise<void>;
  clearHub: () => void;
}

const emptyArenaStats = (): Record<ArenaDifficulty, ArenaDifficultyStats> => ({
  easy: { wins: 0, losses: 0 },
  medium: { wins: 0, losses: 0 },
  hard: { wins: 0, losses: 0 },
});

const formatDate = () =>
  new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

const formatDateFromIso = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      currentMode: null,
      selectedStroke: "forehand",
      sessionHistory: [],
      trophyCount: 0,
      arenaStats: emptyArenaStats(),
      dojoSaves: [],
      arenaMatches: [],

      setCurrentMode: (mode) => set({ currentMode: mode }),
      setSelectedStroke: (stroke) => set({ selectedStroke: stroke }),

      addSession: (entry) =>
        set((state) => ({
          sessionHistory: [entry, ...state.sessionHistory].slice(0, 50),
        })),

      saveDojoStroke: (payload) => {
        const id = payload.id ?? `dojo-${Date.now()}`;
        const date = formatDate();
        const row: DojoStrokeSave = {
          id,
          date,
          strokeLabel: payload.strokeLabel,
          score: payload.score,
          phase: payload.phase,
          note: payload.note,
        };
        set((state) => ({
          dojoSaves: [row, ...state.dojoSaves].slice(0, 40),
        }));
        get().addSession({
          id,
          mode: "stroke-analysis",
          date,
          summary: `Dojo — ${row.strokeLabel} · score ${Math.round(row.score)}`,
        });
        // Sync to Supabase if logged in
        supabase.auth.getUser().then(({ data }) => {
          if (!data.user) return;
          supabase.from("dojo_saves").insert({
            user_id: data.user.id,
            stroke_label: row.strokeLabel,
            score: row.score,
            phase: row.phase ?? null,
            note: row.note ?? null,
          }).then(() => {});
        });
      },

      clearHub: () =>
        set({
          sessionHistory: [],
          trophyCount: 0,
          arenaStats: emptyArenaStats(),
          dojoSaves: [],
          arenaMatches: [],
        }),

      recordArenaMatch: ({ difficulty, won, playerScore, aiScore }) => {
        const id = `arena-${Date.now()}`;
        const date = formatDate();
        const trophyEarned = won;
        set((state) => {
          const arenaStats = { ...state.arenaStats };
          const cur = arenaStats[difficulty] ?? { wins: 0, losses: 0 };
          arenaStats[difficulty] = {
            wins: cur.wins + (won ? 1 : 0),
            losses: cur.losses + (won ? 0 : 1),
          };
          const row: ArenaMatchSave = {
            id,
            date,
            difficulty,
            won,
            playerScore,
            aiScore,
            trophyEarned,
          };
          return {
            arenaStats,
            trophyCount: state.trophyCount + (trophyEarned ? 1 : 0),
            arenaMatches: [row, ...state.arenaMatches].slice(0, 40),
          };
        });
        get().addSession({
          id,
          mode: "ai-rally",
          date,
          summary: `Rally Arena (${difficulty}) — ${won ? "Won" : "Lost"} ${playerScore}-${aiScore}${trophyEarned ? " · +1 trophy" : ""}`,
        });
        // Sync to Supabase if logged in
        supabase.auth.getUser().then(({ data }) => {
          if (!data.user) return;
          supabase.from("arena_matches").insert({
            user_id: data.user.id,
            difficulty,
            won,
            player_score: playerScore,
            ai_score: aiScore,
            trophy_earned: trophyEarned,
          }).then(() => {});
        });
      },

      syncFromSupabaseForUser: async (userId) => {
        const [dojoRes, arenaRes] = await Promise.all([
          supabase
            .from("dojo_saves")
            .select("id, date, stroke_label, score, phase, note")
            .eq("user_id", userId)
            .order("date", { ascending: false })
            .limit(40),
          supabase
            .from("arena_matches")
            .select("id, date, difficulty, won, player_score, ai_score, trophy_earned")
            .eq("user_id", userId)
            .order("date", { ascending: false })
            .limit(40),
        ]);

        const dojoRows = dojoRes.data ?? [];
        const arenaRows = arenaRes.data ?? [];

        const dojoSaves: DojoStrokeSave[] = dojoRows.map((row) => ({
          id: row.id,
          date: formatDateFromIso(row.date),
          strokeLabel: row.stroke_label,
          score: row.score,
          phase: row.phase ?? undefined,
          note: row.note ?? undefined,
        }));

        const arenaMatches: ArenaMatchSave[] = arenaRows.map((row) => ({
          id: row.id,
          date: formatDateFromIso(row.date),
          difficulty: row.difficulty as ArenaDifficulty,
          won: row.won,
          playerScore: row.player_score,
          aiScore: row.ai_score,
          trophyEarned: row.trophy_earned ?? false,
        }));

        const arenaStats = emptyArenaStats();
        for (const match of arenaMatches) {
          const current = arenaStats[match.difficulty];
          arenaStats[match.difficulty] = {
            wins: current.wins + (match.won ? 1 : 0),
            losses: current.losses + (match.won ? 0 : 1),
          };
        }

        const sessionHistory: SessionEntry[] = [
          ...dojoRows.map((row) => ({
            id: row.id,
            mode: "stroke-analysis" as AppMode,
            isoDate: row.date,
            date: formatDateFromIso(row.date),
            summary: `Dojo — ${row.stroke_label} · score ${Math.round(row.score)}`,
          })),
          ...arenaRows.map((row) => ({
            id: row.id,
            mode: "ai-rally" as AppMode,
            isoDate: row.date,
            date: formatDateFromIso(row.date),
            summary: `Rally Arena (${row.difficulty}) — ${row.won ? "Won" : "Lost"} ${row.player_score}-${row.ai_score}${row.trophy_earned ? " · +1 trophy" : ""}`,
          })),
        ]
          .sort((a, b) => Date.parse(b.isoDate) - Date.parse(a.isoDate))
          .slice(0, 50)
          .map(({ isoDate: _isoDate, ...entry }) => entry);

        set({
          dojoSaves,
          arenaMatches,
          arenaStats,
          trophyCount: arenaMatches.filter((m) => m.trophyEarned).length,
          sessionHistory,
        });
      },
    }),
    {
      name: "stroke-sensei-hub",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        trophyCount: s.trophyCount,
        arenaStats: s.arenaStats,
        dojoSaves: s.dojoSaves,
        arenaMatches: s.arenaMatches,
        sessionHistory: s.sessionHistory,
      }),
    }
  )
);
