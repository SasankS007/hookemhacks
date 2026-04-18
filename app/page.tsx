"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Crosshair, Gamepad2, Video, ArrowRight, Zap } from "lucide-react";
import { PageTransition } from "@/components/PageTransition";

const features = [
  {
    icon: Crosshair,
    title: "Stroke Analysis",
    description:
      "Get real-time AI coaching on your forehand, backhand, volley, and slice technique with computer vision feedback.",
    href: "/stroke-analysis",
    color: "from-green-500/20 to-emerald-500/20",
    iconColor: "text-green-400",
  },
  {
    icon: Gamepad2,
    title: "AI Rally",
    description:
      "Practice your court positioning and shot placement against an AI opponent in an interactive 2D rally simulation.",
    href: "/ai-rally",
    color: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-400",
  },
  {
    icon: Video,
    title: "Footage Review",
    description:
      "Upload match footage and get automated shot tracking, heatmaps, and performance statistics breakdowns.",
    href: "/footage",
    color: "from-purple-500/20 to-pink-500/20",
    iconColor: "text-purple-400",
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <PageTransition>
      <div className="relative min-h-screen overflow-hidden">
        {/* Background gradient effects */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 h-[600px] w-[600px] rounded-full bg-primary/5 blur-3xl" />
          <div className="absolute bottom-0 left-0 h-[400px] w-[400px] rounded-full bg-blue-500/5 blur-3xl" />
          <div className="absolute top-0 right-0 h-[400px] w-[400px] rounded-full bg-purple-500/5 blur-3xl" />
        </div>

        {/* Hero Section */}
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-24 pb-16 md:pt-32 md:pb-24">
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary mb-6">
              <Zap className="h-3.5 w-3.5" />
              AI-Powered Training Platform
            </div>
            <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold tracking-tight">
              Elevate Your{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-400">
                Pickleball
              </span>{" "}
              Game
            </h1>
            <p className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Analyze your strokes, rally against AI, and review match footage — all
              in one platform built to sharpen every aspect of your game.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" className="text-base px-8 h-12 font-semibold" asChild>
                <Link href="/dashboard">
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="text-base px-8 h-12"
                asChild
              >
                <Link href="/stroke-analysis">Try Stroke Analysis</Link>
              </Button>
            </div>
          </motion.div>
        </section>

        {/* Feature Cards */}
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24">
          <motion.div
            className="grid grid-cols-1 md:grid-cols-3 gap-6"
            variants={container}
            initial="hidden"
            animate="show"
          >
            {features.map((feature) => (
              <motion.div key={feature.title} variants={item}>
                <Link href={feature.href} className="block group">
                  <Card className="relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 h-full">
                    <div
                      className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
                    />
                    <CardContent className="relative p-8">
                      <div
                        className={`mb-4 inline-flex items-center justify-center rounded-xl bg-secondary/50 p-3 ${feature.iconColor}`}
                      >
                        <feature.icon className="h-6 w-6" />
                      </div>
                      <h3 className="text-xl font-semibold mb-2">
                        {feature.title}
                      </h3>
                      <p className="text-muted-foreground text-sm leading-relaxed">
                        {feature.description}
                      </p>
                      <div className="mt-4 inline-flex items-center text-sm text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        Explore
                        <ArrowRight className="ml-1 h-3.5 w-3.5" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        </section>
      </div>
    </PageTransition>
  );
}
