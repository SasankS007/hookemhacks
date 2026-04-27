// MediaPipe Tasks Vision swing detector
// Uses right wrist (landmark 16) horizontal velocity to classify swings.

export type SwingEvent = "FOREHAND" | "BACKHAND" | "READY";

interface WristSample {
  x: number;
  t: number;
}

// Normalized-coordinates-per-ms threshold to register a swing
const VX_THRESHOLD = 0.012;
// Minimum swing duration window (ms)
const SAMPLE_WINDOW_MS = 120;
// Cooldown after emitting a swing before next can fire
const COOLDOWN_MS = 650;
// How long the emitted state is visible before resetting to READY
const EMIT_DURATION_MS = 250;

export class SwingDetector {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private landmarker: any = null;
  private samples: WristSample[] = [];
  private lastSwingTime = 0;
  private emitResetTime = 0;

  strokeState: SwingEvent = "READY";
  wristDx = 0;   // net displacement over sample window (normalised, camera space)
  wristSpeed = 0; // abs vx

  async init(): Promise<void> {
    const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    this.landmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numPoses: 1,
    });
  }

  processFrame(video: HTMLVideoElement, timestampMs: number) {
    if (!this.landmarker) return;

    // Reset to READY after emit duration
    if (this.strokeState !== "READY" && timestampMs >= this.emitResetTime) {
      this.strokeState = "READY";
    }

    let result;
    try {
      result = this.landmarker.detectForVideo(video, timestampMs);
    } catch {
      return;
    }

    if (!result?.landmarks?.length) return;
    const lm = result.landmarks[0];

    // Right wrist = landmark 16; left = 15. Use whichever has higher visibility.
    const rw = lm[16];
    const lw = lm[15];
    if (!rw && !lw) return;

    // Pick dominant wrist (higher visibility / confidence)
    const wrist = (!lw || (rw && rw.visibility >= lw.visibility)) ? rw : lw;
    if (!wrist) return;

    this.samples.push({ x: wrist.x, t: timestampMs });
    // Trim old samples
    const cutoff = timestampMs - SAMPLE_WINDOW_MS;
    this.samples = this.samples.filter((s) => s.t >= cutoff);
    if (this.samples.length < 4) return;

    const oldest = this.samples[0];
    const newest = this.samples[this.samples.length - 1];
    const dt = newest.t - oldest.t;
    if (dt < 40) return;

    const vx = (newest.x - oldest.x) / dt;
    this.wristDx = newest.x - oldest.x;
    this.wristSpeed = Math.abs(vx);

    const inCooldown = timestampMs - this.lastSwingTime < COOLDOWN_MS;
    if (inCooldown || this.strokeState !== "READY") return;

    if (Math.abs(vx) > VX_THRESHOLD) {
      // Camera coords: wrist moves right (vx > 0) = player moving arm to THEIR left = BACKHAND
      // Camera coords: wrist moves left (vx < 0) = player moving arm to THEIR right = FOREHAND
      // (Assuming unmirrored camera, player facing camera)
      this.strokeState = vx < 0 ? "FOREHAND" : "BACKHAND";
      this.lastSwingTime = timestampMs;
      this.emitResetTime = timestampMs + EMIT_DURATION_MS;
    }
  }

  release() {
    try { this.landmarker?.close(); } catch { /* ignore */ }
    this.landmarker = null;
  }
}
