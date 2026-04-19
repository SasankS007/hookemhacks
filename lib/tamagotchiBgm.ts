/**
 * Lo-fi looping "pet device" background (Web Audio square-wave arp).
 * Browsers may start AudioContext suspended — call resumeTamagotchiBgm() on first user gesture.
 */

let sharedCtx: AudioContext | null = null;
let cleanupFn: (() => void) | null = null;

export function resumeTamagotchiBgm(): void {
  void sharedCtx?.resume();
}

export function startTamagotchiBgm(): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  if (cleanupFn) {
    cleanupFn();
    cleanupFn = null;
  }

  let ctx: AudioContext;
  try {
    ctx = new AudioContext();
    sharedCtx = ctx;
  } catch {
    return () => {};
  }

  const master = ctx.createGain();
  master.gain.value = 0.19;
  master.connect(ctx.destination);

  const freqs = [
    261.63, 293.66, 329.63, 392.0, 440.0, 392.0, 329.63, 293.66,
    196.0, 220.0, 246.94, 293.66, 329.63, 293.66, 246.94, 220.0,
  ];
  let i = 0;

  const tick = () => {
    if (ctx.state !== "running") return;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "square";
    o.frequency.value = freqs[i % freqs.length];
    g.gain.setValueAtTime(0.38, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.09);
    o.connect(g);
    g.connect(master);
    o.start();
    o.stop(ctx.currentTime + 0.1);
    i += 1;
  };

  const id = window.setInterval(tick, 200);

  const stop = () => {
    window.clearInterval(id);
    master.disconnect();
    void ctx.close().catch(() => {});
    if (sharedCtx === ctx) sharedCtx = null;
    cleanupFn = null;
  };

  cleanupFn = stop;
  void ctx.resume().catch(() => {});
  return stop;
}
