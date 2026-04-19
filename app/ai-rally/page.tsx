"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import {
  Wifi,
  WifiOff,
  RotateCcw,
  Trophy,
  Loader2,
  Camera,
  Zap,
} from "lucide-react";

const WS_URL = "ws://localhost:8765";

type ConnState = "disconnected" | "connecting" | "connected" | "error";

type Difficulty = "easy" | "medium" | "hard";

interface GameState {
  stroke: string | null;
  velocity: number;
  playerScore: number;
  aiScore: number;
  gameOver: boolean;
  winner: string | null;
  hitWindow: boolean;
  rally: number;
  difficulty?: Difficulty;
  error?: string;
}

const STROKE_COLORS: Record<string, string> = {
  FOREHAND: "text-green-400 bg-green-400/10 border-green-400/30",
  BACKHAND: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  READY: "text-white bg-white/5 border-white/20",
  UNIDENTIFIABLE: "text-red-400 bg-red-400/10 border-red-400/30",
};

export default function AIRallyPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [conn, setConn] = useState<ConnState>("disconnected");
  const [gameState, setGameState] = useState<GameState>({
    stroke: null,
    velocity: 0,
    playerScore: 0,
    aiScore: 0,
    gameOver: false,
    winner: null,
    hitWindow: false,
    rally: 0,
  });
  const [launching, setLaunching] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>("hard");

  const drawFrame = useCallback(async (blob: Blob) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bitmap = await createImageBitmap(blob);
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConn("connecting");
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "blob";

    ws.onopen = () => setConn("connected");

    ws.onmessage = (ev) => {
      if (ev.data instanceof Blob) {
        drawFrame(ev.data);
      } else {
        try {
          const data = JSON.parse(ev.data);
          if (data.error) {
            setGameState((prev) => ({ ...prev, error: data.error }));
            setConn("error");
            ws.close();
            return;
          }
          setGameState(data);
          if (data.difficulty) setDifficulty(data.difficulty);
        } catch {
          /* ignore malformed json */
        }
      }
    };

    ws.onerror = () => setConn("error");
    ws.onclose = () => setConn("disconnected");

    wsRef.current = ws;
  }, [drawFrame]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConn("disconnected");
  }, []);

  const resetGame = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "reset" }));
  }, []);

  const changeDifficulty = useCallback((level: Difficulty) => {
    setDifficulty(level);
    wsRef.current?.send(JSON.stringify({ action: "set_difficulty", level }));
  }, []);

  const launchAndConnect = useCallback(async () => {
    setLaunching(true);
    try {
      await fetch("/api/rally/launch-cv", { method: "POST" });
      // YOLO + MediaPipe + Pygame take ~10s to initialise on first run
      const maxAttempts = 8;
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const probe = new WebSocket(WS_URL);
          await new Promise<void>((resolve, reject) => {
            probe.onopen = () => { probe.close(); resolve(); };
            probe.onerror = () => reject();
            setTimeout(() => reject(), 1500);
          });
          connect();
          return;
        } catch {
          /* server not ready yet, retry */
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
    try {
      await fetch("/api/rally/stop-cv", { method: "POST" });
    } catch {
      /* best-effort */
    }
  }, [disconnect]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  const strokeClass =
    STROKE_COLORS[gameState.stroke || "READY"] || STROKE_COLORS.READY;

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">AI Rally — CV Mode</h1>
          <p className="text-muted-foreground mt-1">
            Swing your paddle in front of the webcam to return the ball. First
            to 11 wins.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main video panel */}
          <div className="flex-1">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm overflow-hidden">
              <CardContent className="p-0 relative">
                {conn === "connected" ? (
                  <canvas
                    ref={canvasRef}
                    className="w-full h-auto rounded-lg"
                  />
                ) : (
                  <div className="aspect-[1066/480] flex flex-col items-center justify-center bg-secondary/30 rounded-lg gap-4">
                    {conn === "connecting" || launching ? (
                      <>
                        <Loader2 className="h-12 w-12 text-primary animate-spin" />
                        <p className="text-muted-foreground text-sm">
                          {launching
                            ? "Starting CV server..."
                            : "Connecting to WebSocket..."}
                        </p>
                      </>
                    ) : conn === "error" ? (
                      <>
                        <WifiOff className="h-12 w-12 text-red-400" />
                        <p className="text-red-400 text-sm font-medium">
                          {gameState.error
                            ? "Camera Error"
                            : "Could not connect to the CV server"}
                        </p>
                        <p className="text-muted-foreground text-xs max-w-sm text-center">
                          {gameState.error ||
                            'Make sure the Python server is running, or click "Launch & Connect" to start it automatically.'}
                        </p>
                      </>
                    ) : (
                      <>
                        <Camera className="h-16 w-16 text-muted-foreground/30" />
                        <p className="text-muted-foreground text-sm">
                          Connect to the CV server to start playing
                        </p>
                        <p className="text-muted-foreground/50 text-xs">
                          Webcam + YOLOv8 + MediaPipe → real-time paddle game
                        </p>
                      </>
                    )}
                  </div>
                )}

                {/* Hit window flash overlay */}
                {conn === "connected" && gameState.hitWindow && (
                  <div className="absolute inset-x-0 bottom-0 h-2 bg-yellow-400/60 animate-pulse" />
                )}
              </CardContent>
            </Card>

            {/* Connection controls */}
            <div className="flex items-center gap-3 mt-4">
              {conn === "disconnected" || conn === "error" ? (
                <>
                  <Button
                    onClick={launchAndConnect}
                    disabled={launching}
                    className="font-semibold"
                  >
                    {launching ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Zap className="mr-2 h-4 w-4" />
                    )}
                    Launch & Connect
                  </Button>
                  <Button variant="outline" onClick={connect}>
                    <Wifi className="mr-2 h-4 w-4" />
                    Connect Only
                  </Button>
                </>
              ) : (
                <Button
                  variant="destructive"
                  onClick={stopServer}
                  className="font-semibold"
                >
                  <WifiOff className="mr-2 h-4 w-4" />
                  Disconnect & Stop
                </Button>
              )}
            </div>
          </div>

          {/* Side panel */}
          <div className="w-full lg:w-72 space-y-4">
            {/* Score */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  Score
                </p>
                <div className="flex items-center justify-center gap-6 text-center">
                  <div>
                    <p className="text-3xl font-bold text-primary">
                      {gameState.playerScore}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">You</p>
                  </div>
                  <p className="text-2xl text-muted-foreground/50">—</p>
                  <div>
                    <p className="text-3xl font-bold text-red-400">
                      {gameState.aiScore}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">AI</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Stroke State */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  Stroke Detected
                </p>
                <Badge
                  variant="outline"
                  className={`text-base px-4 py-1.5 font-semibold ${strokeClass}`}
                >
                  {gameState.stroke || "READY"}
                </Badge>
              </CardContent>
            </Card>

            {/* Velocity */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  Wrist Velocity
                </p>
                <div className="h-3 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-100"
                    style={{ width: `${(gameState.velocity || 0) * 100}%` }}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Rally */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-1">
                  Rally Length
                </p>
                <p className="text-2xl font-bold">{gameState.rally}</p>
              </CardContent>
            </Card>

            {/* Connection status */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5 flex items-center gap-3">
                <span
                  className={`relative flex h-2.5 w-2.5 ${
                    conn === "connected" ? "" : "opacity-50"
                  }`}
                >
                  {conn === "connected" && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  )}
                  <span
                    className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                      conn === "connected"
                        ? "bg-green-500"
                        : conn === "error"
                          ? "bg-red-500"
                          : "bg-gray-500"
                    }`}
                  />
                </span>
                <span className="text-sm text-muted-foreground capitalize">
                  {conn === "connected"
                    ? "Live — streaming"
                    : conn === "connecting"
                      ? "Connecting…"
                      : conn === "error"
                        ? "Connection failed"
                        : "Disconnected"}
                </span>
              </CardContent>
            </Card>

            {/* Difficulty */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  Difficulty
                </p>
                <div className="flex gap-2">
                  {(["easy", "medium", "hard"] as Difficulty[]).map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => changeDifficulty(lvl)}
                      disabled={conn !== "connected"}
                      className={`flex-1 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                        difficulty === lvl
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary/60 text-muted-foreground hover:bg-secondary"
                      } disabled:opacity-40`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Reset / New Game */}
            <Button
              variant="outline"
              className="w-full"
              onClick={resetGame}
              disabled={conn !== "connected"}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              New Game
            </Button>
          </div>
        </div>

        {/* Game Over Overlay */}
        {gameState.gameOver && conn === "connected" && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
            <div className="text-center space-y-4">
              <Trophy className="h-16 w-16 text-yellow-400 mx-auto" />
              <p className="text-3xl font-bold">
                {gameState.winner === "Player" ? "You Win!" : "AI Wins!"}
              </p>
              <p className="text-muted-foreground text-lg">
                {gameState.playerScore} — {gameState.aiScore}
              </p>
              <Button onClick={resetGame} size="lg" className="font-semibold">
                <RotateCcw className="mr-2 h-4 w-4" />
                Play Again
              </Button>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
