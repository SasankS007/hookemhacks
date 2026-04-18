"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { PageTransition } from "@/components/PageTransition";
import {
  Upload,
  FileVideo,
  Loader2,
  BarChart3,
  Target,
  Zap,
  AlertTriangle,
  Clock,
} from "lucide-react";

type UploadState = "idle" | "uploading" | "processing" | "done";

interface CourtZone {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  shots: number;
  opacity: number;
}

interface ShotEvent {
  id: string;
  time: string;
  type: string;
  zone: string;
  result: "winner" | "error" | "rally";
}

const mockZones: CourtZone[] = [
  { id: "tl", label: "Back Left", x: 0, y: 0, width: 50, height: 33, shots: 18, opacity: 0.4 },
  { id: "tc", label: "Back Center", x: 50, y: 0, width: 50, height: 33, shots: 12, opacity: 0.25 },
  { id: "ml", label: "Mid Left", x: 0, y: 33, width: 50, height: 34, shots: 28, opacity: 0.7 },
  { id: "mc", label: "Mid Center", x: 50, y: 33, width: 50, height: 34, shots: 35, opacity: 0.9 },
  { id: "bl", label: "Kitchen Left", x: 0, y: 67, width: 50, height: 33, shots: 32, opacity: 0.8 },
  { id: "bc", label: "Kitchen Right", x: 50, y: 67, width: 50, height: 33, shots: 17, opacity: 0.35 },
];

const mockShotTimeline: ShotEvent[] = [
  { id: "1", time: "0:12", type: "Forehand", zone: "mc", result: "rally" },
  { id: "2", time: "0:18", type: "Backhand", zone: "ml", result: "rally" },
  { id: "3", time: "0:24", type: "Volley", zone: "bl", result: "winner" },
  { id: "4", time: "0:41", type: "Forehand", zone: "tl", result: "rally" },
  { id: "5", time: "0:55", type: "Slice", zone: "tc", result: "error" },
  { id: "6", time: "1:03", type: "Forehand", zone: "mc", result: "rally" },
  { id: "7", time: "1:12", type: "Backhand", zone: "bl", result: "winner" },
  { id: "8", time: "1:28", type: "Volley", zone: "mc", result: "rally" },
  { id: "9", time: "1:35", type: "Forehand", zone: "ml", result: "error" },
  { id: "10", time: "1:49", type: "Slice", zone: "bc", result: "rally" },
];

const mockStats = {
  totalShots: 142,
  distribution: { forehand: 42, backhand: 28, volley: 38, slice: 34 },
  avgRallyLength: 6.3,
  errorRate: 18,
  winnerRate: 24,
};

const resultColors = {
  winner: "text-green-400 bg-green-400/10",
  error: "text-red-400 bg-red-400/10",
  rally: "text-blue-400 bg-blue-400/10",
};

export default function FootagePage() {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [highlightedZone, setHighlightedZone] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleUpload = useCallback(() => {
    setUploadState("uploading");
    setUploadProgress(0);

    const uploadInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(uploadInterval);
          setUploadState("processing");

          setTimeout(() => {
            setUploadState("done");
          }, 2500);

          return 100;
        }
        return prev + 8;
      });
    }, 150);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (
        file &&
        (file.type === "video/mp4" || file.type === "video/quicktime")
      ) {
        handleUpload();
      }
    },
    [handleUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        handleUpload();
      }
    },
    [handleUpload]
  );

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Footage Review</h1>
          <p className="text-muted-foreground mt-1">
            Upload match footage for automated shot tracking and analysis.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {/* Upload Zone */}
          {uploadState === "idle" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="p-0">
                  <div
                    className={`relative flex flex-col items-center justify-center py-24 px-8 rounded-lg border-2 border-dashed transition-all cursor-pointer ${
                      isDragOver
                        ? "border-primary bg-primary/5"
                        : "border-border/50 hover:border-primary/50"
                    }`}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragOver(true);
                    }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() =>
                      document.getElementById("file-input")?.click()
                    }
                  >
                    <input
                      id="file-input"
                      type="file"
                      accept=".mp4,.mov"
                      className="hidden"
                      onChange={handleFileSelect}
                    />
                    <div className="rounded-2xl bg-secondary/50 p-5 mb-6">
                      <Upload className="h-10 w-10 text-muted-foreground" />
                    </div>
                    <p className="text-lg font-semibold mb-2">
                      Drop your footage here
                    </p>
                    <p className="text-sm text-muted-foreground mb-4">
                      Supports .mp4 and .mov files
                    </p>
                    <Button variant="secondary" size="sm">
                      <FileVideo className="mr-2 h-4 w-4" />
                      Browse Files
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Uploading State */}
          {uploadState === "uploading" && (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="flex flex-col items-center justify-center py-24">
                  <Upload className="h-10 w-10 text-primary mb-4 animate-bounce" />
                  <p className="text-lg font-semibold mb-2">Uploading footage...</p>
                  <p className="text-sm text-muted-foreground mb-6">
                    {uploadProgress}% complete
                  </p>
                  <div className="w-64">
                    <Progress value={uploadProgress} />
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Processing State */}
          {uploadState === "processing" && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="flex flex-col items-center justify-center py-24">
                  <Loader2 className="h-10 w-10 text-primary mb-4 animate-spin" />
                  <p className="text-lg font-semibold mb-2">
                    Analyzing footage...
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Detecting shots, mapping court zones, computing statistics
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Results */}
          {uploadState === "done" && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Stats Row */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  {
                    label: "Total Shots",
                    value: mockStats.totalShots,
                    icon: Target,
                    color: "text-green-400",
                  },
                  {
                    label: "Avg Rally",
                    value: `${mockStats.avgRallyLength} shots`,
                    icon: Zap,
                    color: "text-blue-400",
                  },
                  {
                    label: "Winner Rate",
                    value: `${mockStats.winnerRate}%`,
                    icon: BarChart3,
                    color: "text-yellow-400",
                  },
                  {
                    label: "Error Rate",
                    value: `${mockStats.errorRate}%`,
                    icon: AlertTriangle,
                    color: "text-red-400",
                  },
                  {
                    label: "Duration",
                    value: "12:34",
                    icon: Clock,
                    color: "text-purple-400",
                  },
                ].map((stat) => (
                  <Card
                    key={stat.label}
                    className="border-border/50 bg-card/50 backdrop-blur-sm"
                  >
                    <CardContent className="p-4 flex items-center gap-3">
                      <stat.icon className={`h-5 w-5 ${stat.color} shrink-0`} />
                      <div className="min-w-0">
                        <p className="text-lg font-bold truncate">{stat.value}</p>
                        <p className="text-xs text-muted-foreground">
                          {stat.label}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Court Heatmap */}
                <Card className="lg:col-span-1 border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Court Heatmap</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="relative w-full aspect-[2/3] rounded-lg border border-border/50 overflow-hidden bg-secondary/20">
                      {/* Court lines */}
                      <div className="absolute inset-0">
                        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border/30" />
                        <div className="absolute top-1/3 left-0 right-0 h-px bg-border/30" />
                        <div className="absolute top-2/3 left-0 right-0 h-px bg-border/30" />
                      </div>
                      {/* Zones */}
                      {mockZones.map((zone) => (
                        <div
                          key={zone.id}
                          className={`absolute transition-all duration-300 flex items-center justify-center cursor-pointer ${
                            highlightedZone === zone.id
                              ? "ring-2 ring-primary z-10"
                              : ""
                          }`}
                          style={{
                            left: `${zone.x}%`,
                            top: `${zone.y}%`,
                            width: `${zone.width}%`,
                            height: `${zone.height}%`,
                            backgroundColor: `rgba(74, 222, 128, ${zone.opacity})`,
                          }}
                          onMouseEnter={() => setHighlightedZone(zone.id)}
                          onMouseLeave={() => setHighlightedZone(null)}
                        >
                          <span className="text-xs font-bold text-white drop-shadow-lg">
                            {zone.shots}
                          </span>
                        </div>
                      ))}
                      {/* Net */}
                      <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white/30" />
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background/80 px-2 py-0.5 rounded text-[10px] text-muted-foreground">
                        NET
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Shot Distribution */}
                <Card className="lg:col-span-1 border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Shot Distribution</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {Object.entries(mockStats.distribution).map(
                      ([type, count]) => {
                        const pct = Math.round(
                          (count / mockStats.totalShots) * 100
                        );
                        return (
                          <div key={type}>
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-sm capitalize font-medium">
                                {type}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {count} shots ({pct}%)
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-secondary overflow-hidden">
                              <motion.div
                                className="h-full rounded-full bg-primary"
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ duration: 0.8, delay: 0.2 }}
                              />
                            </div>
                          </div>
                        );
                      }
                    )}
                  </CardContent>
                </Card>

                {/* Shot Timeline */}
                <Card className="lg:col-span-1 border-border/50 bg-card/50 backdrop-blur-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Shot Timeline</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                      {mockShotTimeline.map((shot) => (
                        <button
                          key={shot.id}
                          className={`w-full flex items-center gap-3 rounded-lg p-2.5 text-left transition-all hover:bg-secondary/50 ${
                            highlightedZone === shot.zone
                              ? "bg-secondary/50 ring-1 ring-primary/30"
                              : "bg-secondary/20"
                          }`}
                          onClick={() =>
                            setHighlightedZone(
                              highlightedZone === shot.zone ? null : shot.zone
                            )
                          }
                        >
                          <span className="text-xs text-muted-foreground font-mono w-10 shrink-0">
                            {shot.time}
                          </span>
                          <span className="text-sm font-medium flex-1">
                            {shot.type}
                          </span>
                          <Badge
                            className={`text-[10px] ${
                              resultColors[shot.result]
                            }`}
                            variant="outline"
                          >
                            {shot.result}
                          </Badge>
                        </button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Reset */}
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  onClick={() => setUploadState("idle")}
                >
                  Upload Another Video
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
}
