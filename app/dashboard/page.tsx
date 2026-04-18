"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageTransition } from "@/components/PageTransition";
import { useAppStore } from "@/store/useAppStore";
import {
  Crosshair,
  Gamepad2,
  Video,
  ArrowRight,
  TrendingUp,
  Target,
  Flame,
  Award,
} from "lucide-react";

const modes = [
  {
    href: "/stroke-analysis",
    icon: Crosshair,
    title: "Stroke Analysis",
    description:
      "Practice and refine individual strokes with AI coaching feedback in real time.",
    color: "from-green-500/20 to-emerald-500/10",
    iconBg: "bg-green-500/10",
    iconColor: "text-green-400",
  },
  {
    href: "/ai-rally",
    icon: Gamepad2,
    title: "AI Rally",
    description:
      "Play a 2D rally game against an AI opponent. Test your positioning and reactions.",
    color: "from-blue-500/20 to-cyan-500/10",
    iconBg: "bg-blue-500/10",
    iconColor: "text-blue-400",
  },
  {
    href: "/footage",
    icon: Video,
    title: "Footage Review",
    description:
      "Upload match videos for automated shot tracking, heatmaps, and stats.",
    color: "from-purple-500/20 to-pink-500/10",
    iconBg: "bg-purple-500/10",
    iconColor: "text-purple-400",
  },
];

const stats = [
  { label: "Sessions", value: "24", icon: Flame, color: "text-orange-400" },
  { label: "Strokes Analyzed", value: "1,847", icon: Target, color: "text-green-400" },
  { label: "Top Stroke", value: "Forehand", icon: Award, color: "text-yellow-400" },
  { label: "Improvement", value: "+18%", icon: TrendingUp, color: "text-blue-400" },
];

const modeIcons: Record<string, typeof Crosshair> = {
  "stroke-analysis": Crosshair,
  "ai-rally": Gamepad2,
  footage: Video,
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const sessionHistory = useAppStore((s) => s.sessionHistory);

  return (
    <PageTransition>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Choose a training mode or review your progress.
          </p>
        </div>

        {/* Stats Row */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8"
          variants={container}
          initial="hidden"
          animate="show"
        >
          {stats.map((stat) => (
            <motion.div key={stat.label} variants={item}>
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardContent className="p-5 flex items-center gap-4">
                  <div className="rounded-lg bg-secondary/50 p-2.5">
                    <stat.icon className={`h-5 w-5 ${stat.color}`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stat.value}</p>
                    <p className="text-xs text-muted-foreground">{stat.label}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Mode Selection Cards */}
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
          variants={container}
          initial="hidden"
          animate="show"
        >
          {modes.map((mode) => (
            <motion.div key={mode.title} variants={item}>
              <Link href={mode.href} className="block group h-full">
                <Card className="relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 h-full">
                  <div
                    className={`absolute inset-0 bg-gradient-to-br ${mode.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                  />
                  <CardContent className="relative p-8 flex flex-col items-start h-full">
                    <div
                      className={`mb-4 rounded-xl ${mode.iconBg} p-3.5 ${mode.iconColor}`}
                    >
                      <mode.icon className="h-7 w-7" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">{mode.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed flex-1">
                      {mode.description}
                    </p>
                    <div className="mt-4 inline-flex items-center text-sm text-primary font-medium">
                      Start Training
                      <ArrowRight className="ml-1.5 h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Recent Activity */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sessionHistory.map((session) => {
                const Icon = modeIcons[session.mode || "stroke-analysis"] || Crosshair;
                return (
                  <div
                    key={session.id}
                    className="flex items-center gap-4 rounded-lg bg-secondary/30 p-4 transition-colors hover:bg-secondary/50"
                  >
                    <div className="rounded-lg bg-secondary p-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {session.summary}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {session.date}
                      </p>
                    </div>
                    <Badge variant="secondary" className="text-xs shrink-0">
                      {session.mode?.replace("-", " ")}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
