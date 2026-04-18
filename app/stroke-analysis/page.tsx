"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import { useAppStore, StrokeType } from "@/store/useAppStore";
import {
  Camera,
  Play,
  Square,
  Lightbulb,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

const strokeOptions: { value: StrokeType; label: string }[] = [
  { value: "forehand", label: "Forehand" },
  { value: "backhand", label: "Backhand" },
  { value: "volley", label: "Volley" },
  { value: "slice", label: "Slice" },
];

const mockTips: Record<
  StrokeType,
  { type: "success" | "warning" | "tip"; text: string }[]
> = {
  forehand: [
    { type: "success", text: "Good continental grip detected — solid foundation." },
    { type: "warning", text: "Elbow extending too early on the follow-through." },
    { type: "tip", text: "Try rotating your hips more to generate power from the core." },
    { type: "tip", text: "Keep your paddle face slightly open at contact point." },
  ],
  backhand: [
    { type: "success", text: "Two-handed grip is well-positioned." },
    { type: "warning", text: "Footwork needs adjustment — step into the shot more." },
    { type: "tip", text: "Focus on leading with the knuckles for a cleaner contact." },
    { type: "tip", text: "Keep your non-dominant hand engaged longer through the swing." },
  ],
  volley: [
    { type: "success", text: "Good net positioning — staying compact." },
    { type: "warning", text: "Wrist is too loose on contact — firm it up." },
    { type: "tip", text: "Punch the ball, don't swing. Short, decisive movements." },
    { type: "tip", text: "Keep the paddle out in front of your body at all times." },
  ],
  slice: [
    { type: "success", text: "Nice beveled grip for the slice approach." },
    { type: "warning", text: "Opening the paddle face too much — shots floating high." },
    { type: "tip", text: "Brush under the ball with a downward-to-forward motion." },
    { type: "tip", text: "Stay low through the shot — bend your knees more." },
  ],
};

const mockScores: Record<StrokeType, { accuracy: number; power: number; consistency: number }> = {
  forehand: { accuracy: 87, power: 72, consistency: 81 },
  backhand: { accuracy: 74, power: 65, consistency: 69 },
  volley: { accuracy: 91, power: 58, consistency: 85 },
  slice: { accuracy: 68, power: 61, consistency: 73 },
};

export default function StrokeAnalysisPage() {
  const { selectedStroke, setSelectedStroke } = useAppStore();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [tips, setTips] = useState(mockTips[selectedStroke]);
  const [scores, setScores] = useState(mockScores[selectedStroke]);

  useEffect(() => {
    setTips(mockTips[selectedStroke]);
    setScores(mockScores[selectedStroke]);
  }, [selectedStroke]);

  const handleToggleAnalysis = () => {
    setIsAnalyzing((prev) => !prev);
  };

  const tipIcon = (type: string) => {
    switch (type) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0 mt-0.5" />;
      default:
        return <Lightbulb className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />;
    }
  };

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Stroke Analysis</h1>
          <p className="text-muted-foreground mt-1">
            Select a stroke type and start analyzing your technique.
          </p>
        </div>

        {/* Stroke Selector */}
        <div className="flex flex-wrap gap-2 mb-6">
          {strokeOptions.map((stroke) => (
            <Button
              key={stroke.value}
              variant={selectedStroke === stroke.value ? "default" : "secondary"}
              onClick={() => setSelectedStroke(stroke.value)}
              className="capitalize"
            >
              {stroke.label}
            </Button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Camera Feed */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm overflow-hidden">
              <CardContent className="p-0">
                <div
                  className={`relative aspect-video flex flex-col items-center justify-center bg-secondary/30 transition-all duration-500 ${
                    isAnalyzing ? "ring-2 ring-primary/50" : ""
                  }`}
                >
                  {isAnalyzing && (
                    <div className="absolute top-4 left-4 flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                      </span>
                      <span className="text-sm text-red-400 font-medium">
                        Analyzing
                      </span>
                    </div>
                  )}
                  {isAnalyzing && (
                    <Badge className="absolute top-4 right-4" variant="secondary">
                      {selectedStroke}
                    </Badge>
                  )}
                  <Camera className="h-16 w-16 text-muted-foreground/30 mb-4" />
                  <p className="text-muted-foreground text-sm">
                    {isAnalyzing
                      ? "CV module processing your stroke..."
                      : "Camera feed — CV module coming soon"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Button
              size="lg"
              className="w-full font-semibold h-12"
              onClick={handleToggleAnalysis}
              variant={isAnalyzing ? "destructive" : "default"}
            >
              {isAnalyzing ? (
                <>
                  <Square className="mr-2 h-4 w-4" />
                  Stop Analysis
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Analysis
                </>
              )}
            </Button>

            {/* Score Cards */}
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(scores).map(([key, value]) => (
                <Card
                  key={key}
                  className="border-border/50 bg-card/50 backdrop-blur-sm"
                >
                  <CardContent className="p-4 text-center">
                    <p className="text-2xl font-bold text-primary">{value}%</p>
                    <p className="text-xs text-muted-foreground capitalize mt-1">
                      {key}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Feedback Panel */}
          <div className="space-y-4">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Coaching Feedback
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Tips for your{" "}
                  <span className="capitalize text-foreground font-medium">
                    {selectedStroke}
                  </span>
                </p>
              </CardHeader>
              <CardContent className="space-y-3">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={selectedStroke}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-3"
                  >
                    {tips.map((tip, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="flex gap-3 rounded-lg bg-secondary/30 p-3"
                      >
                        {tipIcon(tip.type)}
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {tip.text}
                        </p>
                      </motion.div>
                    ))}
                  </motion.div>
                </AnimatePresence>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
