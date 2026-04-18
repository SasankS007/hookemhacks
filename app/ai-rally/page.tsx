"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageTransition } from "@/components/PageTransition";
import { RotateCcw, Trophy } from "lucide-react";

type Difficulty = "easy" | "medium" | "hard";

const COURT_WIDTH = 400;
const COURT_HEIGHT = 600;
const PADDLE_WIDTH = 80;
const PADDLE_HEIGHT = 12;
const BALL_SIZE = 10;
const WIN_SCORE = 11;

const AI_SPEEDS: Record<Difficulty, number> = {
  easy: 2.5,
  medium: 4.5,
  hard: 7,
};

interface GameState {
  playerX: number;
  aiX: number;
  ballX: number;
  ballY: number;
  ballDX: number;
  ballDY: number;
  playerScore: number;
  aiScore: number;
  running: boolean;
  gameOver: boolean;
}

function initialState(): GameState {
  return {
    playerX: COURT_WIDTH / 2 - PADDLE_WIDTH / 2,
    aiX: COURT_WIDTH / 2 - PADDLE_WIDTH / 2,
    ballX: COURT_WIDTH / 2 - BALL_SIZE / 2,
    ballY: COURT_HEIGHT / 2 - BALL_SIZE / 2,
    ballDX: 3 * (Math.random() > 0.5 ? 1 : -1),
    ballDY: 4,
    playerScore: 0,
    aiScore: 0,
    running: false,
    gameOver: false,
  };
}

export default function AIRallyPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [game, setGame] = useState<GameState>(initialState);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gameRef = useRef(game);
  const animFrameRef = useRef<number>(0);
  const keysRef = useRef<Set<string>>(new Set());

  gameRef.current = game;

  const resetGame = useCallback(() => {
    cancelAnimationFrame(animFrameRef.current);
    setGame(initialState());
  }, []);

  const startGame = useCallback(() => {
    setGame((g) => ({ ...g, running: true }));
  }, []);

  // Key listeners
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      keysRef.current.add(e.key);
      if (["ArrowLeft", "ArrowRight"].includes(e.key)) e.preventDefault();
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      keysRef.current.delete(e.key);
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  // Mouse/touch control
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handlePointer = (e: MouseEvent | TouchEvent) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = COURT_WIDTH / rect.width;
      const clientX =
        "touches" in e ? e.touches[0].clientX : (e as MouseEvent).clientX;
      const x = (clientX - rect.left) * scaleX;
      setGame((g) => ({
        ...g,
        playerX: Math.max(
          0,
          Math.min(COURT_WIDTH - PADDLE_WIDTH, x - PADDLE_WIDTH / 2)
        ),
      }));
    };

    canvas.addEventListener("mousemove", handlePointer);
    canvas.addEventListener("touchmove", handlePointer as EventListener);
    return () => {
      canvas.removeEventListener("mousemove", handlePointer);
      canvas.removeEventListener("touchmove", handlePointer as EventListener);
    };
  }, []);

  // Game loop
  useEffect(() => {
    if (!game.running || game.gameOver) return;

    const aiSpeed = AI_SPEEDS[difficulty];
    const PLAYER_SPEED = 6;

    const loop = () => {
      setGame((g) => {
        let { playerX, aiX, ballX, ballY, ballDX, ballDY, playerScore, aiScore } = g;

        // Player keyboard input
        if (keysRef.current.has("ArrowLeft")) {
          playerX = Math.max(0, playerX - PLAYER_SPEED);
        }
        if (keysRef.current.has("ArrowRight")) {
          playerX = Math.min(COURT_WIDTH - PADDLE_WIDTH, playerX + PLAYER_SPEED);
        }

        // AI movement
        const aiCenter = aiX + PADDLE_WIDTH / 2;
        const ballCenter = ballX + BALL_SIZE / 2;
        if (aiCenter < ballCenter - 5) {
          aiX = Math.min(COURT_WIDTH - PADDLE_WIDTH, aiX + aiSpeed);
        } else if (aiCenter > ballCenter + 5) {
          aiX = Math.max(0, aiX - aiSpeed);
        }

        // Ball movement
        ballX += ballDX;
        ballY += ballDY;

        // Wall collisions
        if (ballX <= 0 || ballX >= COURT_WIDTH - BALL_SIZE) {
          ballDX = -ballDX;
          ballX = Math.max(0, Math.min(COURT_WIDTH - BALL_SIZE, ballX));
        }

        // Paddle collisions - player (bottom)
        if (
          ballDY > 0 &&
          ballY + BALL_SIZE >= COURT_HEIGHT - PADDLE_HEIGHT - 20 &&
          ballY + BALL_SIZE <= COURT_HEIGHT - 20 + PADDLE_HEIGHT &&
          ballX + BALL_SIZE > playerX &&
          ballX < playerX + PADDLE_WIDTH
        ) {
          ballDY = -Math.abs(ballDY);
          const hitPos = (ballX + BALL_SIZE / 2 - playerX) / PADDLE_WIDTH;
          ballDX = (hitPos - 0.5) * 8;
          ballY = COURT_HEIGHT - PADDLE_HEIGHT - 20 - BALL_SIZE;
        }

        // Paddle collisions - AI (top)
        if (
          ballDY < 0 &&
          ballY <= PADDLE_HEIGHT + 20 &&
          ballY >= 20 - PADDLE_HEIGHT &&
          ballX + BALL_SIZE > aiX &&
          ballX < aiX + PADDLE_WIDTH
        ) {
          ballDY = Math.abs(ballDY);
          const hitPos = (ballX + BALL_SIZE / 2 - aiX) / PADDLE_WIDTH;
          ballDX = (hitPos - 0.5) * 8;
          ballY = PADDLE_HEIGHT + 20;
        }

        // Scoring
        let gameOver = false;
        if (ballY < -BALL_SIZE) {
          playerScore += 1;
          if (playerScore >= WIN_SCORE) gameOver = true;
          ballX = COURT_WIDTH / 2 - BALL_SIZE / 2;
          ballY = COURT_HEIGHT / 2 - BALL_SIZE / 2;
          ballDX = 3 * (Math.random() > 0.5 ? 1 : -1);
          ballDY = -4;
        } else if (ballY > COURT_HEIGHT + BALL_SIZE) {
          aiScore += 1;
          if (aiScore >= WIN_SCORE) gameOver = true;
          ballX = COURT_WIDTH / 2 - BALL_SIZE / 2;
          ballY = COURT_HEIGHT / 2 - BALL_SIZE / 2;
          ballDX = 3 * (Math.random() > 0.5 ? 1 : -1);
          ballDY = 4;
        }

        return {
          ...g,
          playerX,
          aiX,
          ballX,
          ballY,
          ballDX,
          ballDY,
          playerScore,
          aiScore,
          gameOver,
          running: !gameOver,
        };
      });

      animFrameRef.current = requestAnimationFrame(loop);
    };

    animFrameRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [game.running, game.gameOver, difficulty]);

  // Rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, COURT_WIDTH, COURT_HEIGHT);

    // Court background
    ctx.fillStyle = "#0f1729";
    ctx.fillRect(0, 0, COURT_WIDTH, COURT_HEIGHT);

    // Court lines
    ctx.strokeStyle = "rgba(74, 222, 128, 0.15)";
    ctx.lineWidth = 2;
    ctx.strokeRect(10, 10, COURT_WIDTH - 20, COURT_HEIGHT - 20);

    // Center line
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(10, COURT_HEIGHT / 2);
    ctx.lineTo(COURT_WIDTH - 10, COURT_HEIGHT / 2);
    ctx.stroke();
    ctx.setLineDash([]);

    // Kitchen/NVZ lines
    ctx.strokeStyle = "rgba(74, 222, 128, 0.1)";
    ctx.beginPath();
    ctx.moveTo(10, COURT_HEIGHT * 0.25);
    ctx.lineTo(COURT_WIDTH - 10, COURT_HEIGHT * 0.25);
    ctx.moveTo(10, COURT_HEIGHT * 0.75);
    ctx.lineTo(COURT_WIDTH - 10, COURT_HEIGHT * 0.75);
    ctx.stroke();

    // NVZ labels
    ctx.fillStyle = "rgba(74, 222, 128, 0.08)";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("NVZ", COURT_WIDTH / 2, COURT_HEIGHT * 0.22);
    ctx.fillText("NVZ", COURT_WIDTH / 2, COURT_HEIGHT * 0.78);

    // AI paddle
    ctx.fillStyle = "#ef4444";
    ctx.shadowColor = "#ef4444";
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.roundRect(game.aiX, 20, PADDLE_WIDTH, PADDLE_HEIGHT, 6);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Player paddle
    ctx.fillStyle = "#4ade80";
    ctx.shadowColor = "#4ade80";
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.roundRect(
      game.playerX,
      COURT_HEIGHT - PADDLE_HEIGHT - 20,
      PADDLE_WIDTH,
      PADDLE_HEIGHT,
      6
    );
    ctx.fill();
    ctx.shadowBlur = 0;

    // Ball
    ctx.fillStyle = "#fbbf24";
    ctx.shadowColor = "#fbbf24";
    ctx.shadowBlur = 16;
    ctx.beginPath();
    ctx.arc(
      game.ballX + BALL_SIZE / 2,
      game.ballY + BALL_SIZE / 2,
      BALL_SIZE / 2,
      0,
      Math.PI * 2
    );
    ctx.fill();
    ctx.shadowBlur = 0;
  }, [game]);

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">AI Rally</h1>
          <p className="text-muted-foreground mt-1">
            Use arrow keys or mouse to move your paddle. First to {WIN_SCORE} wins!
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 items-start">
          {/* Court */}
          <div className="flex-1 flex justify-center">
            <div className="relative">
              <canvas
                ref={canvasRef}
                width={COURT_WIDTH}
                height={COURT_HEIGHT}
                className="rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm"
                style={{ maxWidth: "100%", height: "auto" }}
              />
              {!game.running && !game.gameOver && (
                <div className="absolute inset-0 flex items-center justify-center bg-background/60 backdrop-blur-sm rounded-xl">
                  <Button
                    size="lg"
                    className="font-semibold px-8"
                    onClick={startGame}
                  >
                    Start Game
                  </Button>
                </div>
              )}
              {game.gameOver && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/70 backdrop-blur-sm rounded-xl gap-4">
                  <Trophy className="h-12 w-12 text-yellow-400" />
                  <p className="text-2xl font-bold">
                    {game.playerScore >= WIN_SCORE ? "You Win!" : "AI Wins!"}
                  </p>
                  <p className="text-muted-foreground">
                    {game.playerScore} — {game.aiScore}
                  </p>
                  <Button onClick={resetGame} className="font-semibold">
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Play Again
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="w-full lg:w-64 space-y-4">
            {/* Score */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-muted-foreground font-medium">Score</p>
                </div>
                <div className="flex items-center justify-center gap-6 text-center">
                  <div>
                    <p className="text-3xl font-bold text-primary">
                      {game.playerScore}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">You</p>
                  </div>
                  <p className="text-2xl text-muted-foreground/50">—</p>
                  <div>
                    <p className="text-3xl font-bold text-red-400">
                      {game.aiScore}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">AI</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Difficulty */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-5">
                <p className="text-sm text-muted-foreground font-medium mb-3">
                  Difficulty
                </p>
                <div className="flex flex-col gap-2">
                  {(["easy", "medium", "hard"] as Difficulty[]).map((d) => (
                    <Button
                      key={d}
                      variant={difficulty === d ? "default" : "secondary"}
                      size="sm"
                      onClick={() => {
                        setDifficulty(d);
                        resetGame();
                      }}
                      className="capitalize w-full"
                    >
                      {d}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* New Game */}
            <Button
              variant="outline"
              className="w-full"
              onClick={resetGame}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              New Game
            </Button>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
