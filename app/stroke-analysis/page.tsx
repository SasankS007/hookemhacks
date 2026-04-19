"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import {
  Camera,
  Play,
  Square,
  Lightbulb,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Activity,
  Target,
  Zap,
  RotateCcw,
  Loader2,
} from "lucide-react";

const WS_URL = "ws://localhost:8766";

type ConnState = "idle" | "connecting" | "connected" | "error";

interface CoachingTip {
  metric: string;
  score: number;
  tip: string;
  priority: number;
}

interface ShotHistoryItem {
  shotType: string;
  overall: number;
  timestamp: number;
}

interface AnalysisState {
  calibrated: boolean;
  calibrationProgress: number;
  bodyProportions: Record<string, number | boolean> | null;
  shotType: string;
  shotConfidence: number;
  phase: string;
  liveMetrics: Record<string, number>;
  kineticChain: Record<string, number | boolean> | null;
  lastShotMetrics: Record<string, number> | null;
  coachingTips: CoachingTip[];
  shotHistory: ShotHistoryItem[];
  error?: string;
}

const PHASE_LABELS: Record<string, string> = {
  ready: "Ready",
  backswing: "Backswing",
  load: "Load",
  contact: "Contact",
  follow_through: "Follow-Through",
};

const PHASE_COLORS: Record<string, string> = {
  ready: "bg-white/20 text-white",
  backswing: "bg-yellow-500/20 text-yellow-400",
  load: "bg-cyan-500/20 text-cyan-400",
  contact: "bg-green-500/20 text-green-400",
  follow_through: "bg-purple-500/20 text-purple-400",
};

const SHOT_COLORS: Record<string, string> = {
  forehand: "text-green-400",
  backhand: "text-orange-400",
  dink: "text-cyan-400",
  serve: "text-pink-400",
  volley: "text-yellow-400",
  none: "text-muted-foreground",
};

const METRIC_LABELS: Record<string, string> = {
  hipRotation: "Hip Rotation",
  contactPoint: "Contact Point",
  elbowExtension: "Elbow Extension",
  wristSnap: "Wrist Snap",
  kineticChain: "Kinetic Chain",
  kneeBend: "Knee Bend",
  followThrough: "Follow-Through",
  overall: "Overall",
};

const PHASE_ORDER = ["ready", "backswing", "load", "contact", "follow_through"];

export default function StrokeAnalysisPage() {
  const [conn, setConn] = useState<ConnState>("idle");
  const [launching, setLaunching] = useState(false);
  const [state, setState] = useState<AnalysisState | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setConn("connecting");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConn("connected");

    ws.onmessage = async (e) => {
      if (e.data instanceof Blob) {
        const bmp = await createImageBitmap(e.data);
        const cvs = canvasRef.current;
        if (cvs) {
          cvs.width = bmp.width;
          cvs.height = bmp.height;
          const ctx = cvs.getContext("2d");
          ctx?.drawImage(bmp, 0, 0);
        }
        bmp.close();
      } else {
        try {
          const parsed = JSON.parse(e.data);
          setState(parsed);
        } catch {
          /* ignore */
        }
      }
    };

    ws.onerror = () => setConn("error");
    ws.onclose = () => setConn("idle");
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConn("idle");
    setState(null);
  }, []);

  const launchAndConnect = useCallback(async () => {
    setLaunching(true);
    try {
      await fetch("/api/stroke/launch-cv", { method: "POST" });
      const maxAttempts = 10;
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const probe = new WebSocket(WS_URL);
          await new Promise<void>((resolve, reject) => {
            probe.onopen = () => {
              probe.close();
              resolve();
            };
            probe.onerror = () => reject();
            setTimeout(() => reject(), 1500);
          });
          connect();
          return;
        } catch {
          /* retry */
        }
      }
      setConn("error");
    } catch {
      setConn("error");
    } finally {
      setLaunching(false);
    }
  }, [connect]);

  const stopServer = useCallback(async () => {
    disconnect();
    await fetch("/api/stroke/stop-cv", { method: "POST" });
  }, [disconnect]);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const calibrated = state?.calibrated ?? false;
  const phase = state?.phase ?? "ready";
  const shotType = state?.shotType ?? "none";
  const liveMetrics = state?.liveMetrics ?? {};
  const lastMetrics = state?.lastShotMetrics;
  const tips = state?.coachingTips ?? [];
  const history = state?.shotHistory ?? [];
  const chain = state?.kineticChain;
  const calibrationProgress = state?.calibrationProgress ?? 0;
  const phaseIdx = PHASE_ORDER.indexOf(phase);

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold">Stroke Analysis</h1>
            <p className="text-muted-foreground mt-1">
              Real-time biomechanical swing analysis with body-proportional coaching
            </p>
          </div>

          <div className="flex items-center gap-2">
            {conn === "idle" && (
              <Button onClick={launchAndConnect} disabled={launching} size="lg">
                {launching ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting CV...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Launch Analysis
                  </>
                )}
              </Button>
            )}
            {conn === "connected" && (
              <Button onClick={stopServer} variant="destructive" size="lg">
                <Square className="mr-2 h-4 w-4" />
                Stop
              </Button>
            )}
            {conn === "connecting" && (
              <Button disabled size="lg">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Connecting...
              </Button>
            )}
            {conn === "error" && (
              <Button onClick={launchAndConnect} variant="secondary" size="lg">
                <RotateCcw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            )}
          </div>
        </div>

        {state?.error && (
          <div className="mb-6 rounded-lg bg-red-500/10 border border-red-500/30 p-4">
            <p className="text-red-400 text-sm">{state.error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Left: Camera Feed ────────────────────────────────── */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm overflow-hidden">
              <CardContent className="p-0">
                <div className="relative aspect-video bg-secondary/30 flex items-center justify-center">
                  {conn === "connected" ? (
                    <canvas
                      ref={canvasRef}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <Camera className="h-16 w-16 text-muted-foreground/30" />
                      <p className="text-muted-foreground text-sm">
                        {conn === "connecting"
                          ? "Initialising MediaPipe + camera..."
                          : "Launch analysis to begin"}
                      </p>
                    </div>
                  )}

                  {conn === "connected" && (
                    <>
                      <div className="absolute top-3 left-3 flex items-center gap-2">
                        <span className="relative flex h-3 w-3">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                        </span>
                        <span className="text-xs text-red-400 font-medium">
                          LIVE
                        </span>
                      </div>

                      {calibrated && (
                        <Badge
                          className={`absolute top-3 right-3 ${SHOT_COLORS[shotType] || ""}`}
                          variant="secondary"
                        >
                          {shotType.toUpperCase()}
                        </Badge>
                      )}
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* ── Phase Progress ───────────────────────────────── */}
            {conn === "connected" && calibrated && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="py-3 px-4">
                  <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">
                    Swing Phase
                  </p>
                  <div className="flex gap-1">
                    {PHASE_ORDER.map((p, i) => (
                      <div
                        key={p}
                        className={`flex-1 rounded-md py-1.5 text-center text-xs font-medium transition-all ${
                          i <= phaseIdx
                            ? PHASE_COLORS[p]
                            : "bg-secondary/30 text-muted-foreground/40"
                        }`}
                      >
                        {PHASE_LABELS[p]}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* ── Calibration Bar ──────────────────────────────── */}
            {conn === "connected" && !calibrated && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="py-4 px-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium">
                      Calibrating body proportions...
                    </p>
                    <span className="text-xs text-muted-foreground">
                      {Math.round(calibrationProgress * 100)}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-secondary/50 overflow-hidden">
                    <motion.div
                      className="h-full bg-primary rounded-full"
                      animate={{ width: `${calibrationProgress * 100}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Stand naturally with arms relaxed. Your body proportions are being measured to personalise all coaching targets.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* ── Live Metrics Row ─────────────────────────────── */}
            {conn === "connected" && calibrated && (
              <div className="grid grid-cols-4 gap-3">
                <MetricCard
                  icon={<Activity className="h-4 w-4 text-cyan-400" />}
                  label="Elbow"
                  value={`${Math.round(liveMetrics.elbowAngle ?? 0)}°`}
                />
                <MetricCard
                  icon={<RotateCcw className="h-4 w-4 text-orange-400" />}
                  label="Hip Rot."
                  value={`${Math.round(liveMetrics.hipRotation ?? 0)}°`}
                />
                <MetricCard
                  icon={<Zap className="h-4 w-4 text-yellow-400" />}
                  label="Wrist Vel."
                  value={`${((liveMetrics.wristVelocity ?? 0) * 1000).toFixed(0)}`}
                />
                <MetricCard
                  icon={<Target className="h-4 w-4 text-green-400" />}
                  label="Knee"
                  value={`${Math.round(liveMetrics.kneeAngle ?? 0)}°`}
                />
              </div>
            )}

            {/* ── Last Shot Scores ─────────────────────────────── */}
            {lastMetrics && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Target className="h-4 w-4 text-primary" />
                    Last Shot Breakdown
                    <Badge variant="outline" className="ml-auto text-lg">
                      {lastMetrics.overall}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(lastMetrics)
                      .filter(([k]) => k !== "overall")
                      .map(([key, val]) => (
                        <div key={key} className="space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">
                              {METRIC_LABELS[key] ?? key}
                            </span>
                            <span
                              className={`text-xs font-bold ${
                                val >= 70
                                  ? "text-green-400"
                                  : val >= 40
                                    ? "text-yellow-400"
                                    : "text-red-400"
                              }`}
                            >
                              {Math.round(val)}
                            </span>
                          </div>
                          <div className="h-1.5 rounded-full bg-secondary/50 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                val >= 70
                                  ? "bg-green-500"
                                  : val >= 40
                                    ? "bg-yellow-500"
                                    : "bg-red-500"
                              }`}
                              style={{ width: `${Math.min(100, val)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* ── Right: Sidebar ───────────────────────────────── */}
          <div className="space-y-4">
            {/* Kinetic Chain */}
            {chain && calibrated && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Zap className="h-4 w-4 text-yellow-400" />
                    Kinetic Chain
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <ChainBar label="Hip" value={chain.hipVel as number} />
                  <ChainBar label="Shoulder" value={chain.shoulderVel as number} />
                  <ChainBar label="Elbow" value={chain.elbowVel as number} />
                  <ChainBar label="Wrist" value={chain.wristVel as number} />
                  <div
                    className={`mt-2 text-xs font-medium rounded px-2 py-1 text-center ${
                      chain.chainCorrect
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {chain.chainCorrect
                      ? "Energy flowing correctly (proximal → distal)"
                      : "Chain break detected — initiate from hips first"}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Coaching Tips */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Coaching Tips
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <AnimatePresence mode="wait">
                  {tips.length > 0 ? (
                    <motion.div
                      key={tips.map((t) => t.metric).join(",")}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="space-y-2"
                    >
                      {tips.map((tip, i) => (
                        <motion.div
                          key={`${tip.metric}-${i}`}
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.06 }}
                          className="flex gap-2 rounded-lg bg-secondary/30 p-3"
                        >
                          {tip.score >= 70 ? (
                            <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
                          ) : tip.score >= 40 ? (
                            <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />
                          ) : (
                            <Lightbulb className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                          )}
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-0.5">
                              {METRIC_LABELS[tip.metric] ?? tip.metric}
                            </p>
                            <p className="text-sm text-foreground/80 leading-relaxed">
                              {tip.tip}
                            </p>
                          </div>
                        </motion.div>
                      ))}
                    </motion.div>
                  ) : (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                      {conn === "connected"
                        ? "Perform a swing to receive feedback"
                        : "Launch analysis to begin"}
                    </p>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>

            {/* Body Proportions */}
            {state?.bodyProportions && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Your Body Profile</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    {[
                      ["Shoulder/Hip", state.bodyProportions.shoulderHipRatio],
                      ["Torso/Leg", state.bodyProportions.torsoLegRatio],
                      ["Upper/Forearm", state.bodyProportions.upperForearmRatio],
                      ["Arm/Height", state.bodyProportions.armHeightRatio],
                      ["Speed Mult.", state.bodyProportions.speedMultiplier],
                    ].map(([label, val]) => (
                      <div
                        key={label as string}
                        className="flex justify-between py-1 border-b border-border/20"
                      >
                        <span className="text-muted-foreground">{label as string}</span>
                        <span className="font-mono">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Shot History */}
            {history.length > 0 && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Shot History</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5 max-h-60 overflow-y-auto">
                  {[...history].reverse().map((h, i) => (
                    <div
                      key={`${h.timestamp}-${i}`}
                      className="flex items-center justify-between rounded bg-secondary/20 px-3 py-1.5"
                    >
                      <span
                        className={`text-sm font-medium capitalize ${SHOT_COLORS[h.shotType] || ""}`}
                      >
                        {h.shotType}
                      </span>
                      <span
                        className={`text-sm font-bold ${
                          h.overall >= 70
                            ? "text-green-400"
                            : h.overall >= 40
                              ? "text-yellow-400"
                              : "text-red-400"
                        }`}
                      >
                        {Math.round(h.overall)}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </PageTransition>
  );
}

function MetricCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
      <CardContent className="p-3 flex items-center gap-2">
        {icon}
        <div>
          <p className="text-lg font-bold leading-none">{value}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ChainBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, value * 1200);
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-mono">{(value * 1000).toFixed(0)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary/40 overflow-hidden">
        <div
          className="h-full rounded-full bg-yellow-400/80 transition-all duration-100"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
