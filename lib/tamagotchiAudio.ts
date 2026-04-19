/**
 * Gameboy-style UI sounds + optional ElevenLabs voice (when API key is configured).
 */

const audioCache = new Map<string, string>();

/** Master level for Web Audio SFX (beeps). */
const SFX_PEAK_GAIN = 0.45;

function playBeep(freq: number, durationMs: number, type: OscillatorType = "square") {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = SFX_PEAK_GAIN;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationMs / 1000);
    osc.stop(ctx.currentTime + durationMs / 1000 + 0.02);
    osc.onended = () => void ctx.close();
  } catch {
    /* ignore */
  }
}

async function playMp3FromCache(cacheKey: string, text: string): Promise<boolean> {
  let url = audioCache.get(cacheKey);
  if (!url) {
    const res = await fetch("/api/elevenlabs/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.status === 501 || !res.ok) {
      return false;
    }
    const blob = await res.blob();
    url = URL.createObjectURL(blob);
    audioCache.set(cacheKey, url);
  }
  await new Promise<void>((resolve, reject) => {
    const a = new Audio(url);
    a.volume = 1;
    a.onended = () => resolve();
    a.onerror = () => reject();
    void a.play().catch(reject);
  });
  return true;
}

/** Short UI tick — ElevenLabs one-shot or chiptune. */
export async function playUiClick(): Promise<void> {
  const ok = await playMp3FromCache("__click__", "Tick!");
  if (!ok) playBeep(880, 45);
}

/** Ball / impact — ElevenLabs or noise burst. */
export async function playBallHit(): Promise<void> {
  const ok = await playMp3FromCache("__hit__", "Pop!");
  if (!ok) {
    playBeep(420, 35);
    setTimeout(() => playBeep(180, 40), 40);
  }
}

/** Point scored — announces running totals. */
export async function announceScore(playerScore: number, aiScore: number): Promise<void> {
  const line = `You ${playerScore}. Computer ${aiScore}.`;
  const key = `score_${playerScore}_${aiScore}`;
  const ok = await playMp3FromCache(key, line);
  if (!ok) {
    playBeep(660, 60);
    setTimeout(() => playBeep(520, 80), 70);
  }
}

/** Match over. */
export async function announceGameOver(won: boolean): Promise<void> {
  const line = won ? "You win the match!" : "Computer wins the match!";
  const key = won ? "__win__" : "__lose__";
  const ok = await playMp3FromCache(key, line);
  if (!ok) {
    playBeep(won ? 784 : 220, 120);
  }
}
