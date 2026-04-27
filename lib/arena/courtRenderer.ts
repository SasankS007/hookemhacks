import {
  COURT_W, COURT_H, BALL_R, PADDLE_W, MARGIN_TOP,
  BOT_LEFT, BOT_RIGHT, TOP_LEFT, TOP_RIGHT, rowXs,
} from "./browserGameState";
import type { GameSnapshot } from "./browserGameState";

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

function courtPoint(nx: number, ny: number): [number, number] {
  const y = lerp(TOP_LEFT[1], BOT_LEFT[1], ny);
  const [lx, rx] = rowXs(y);
  return [lerp(lx, rx, nx), y];
}

function drawStickRacket(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  swingRight: boolean,
  swinging: boolean
) {
  const baseAngle = swingRight ? -0.75 : -2.35;
  const swingOffset = swinging ? (swingRight ? -0.65 : 0.65) : 0;
  const angle = baseAngle + swingOffset;
  const hLen = 12;
  const headOffset = 9;
  const hx = x + Math.cos(angle) * hLen;
  const hy = y + Math.sin(angle) * hLen;
  const rx = hx + Math.cos(angle) * headOffset;
  const ry = hy + Math.sin(angle) * headOffset;

  ctx.strokeStyle = "#f8fafc";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(hx, hy);
  ctx.stroke();

  ctx.fillStyle = "#f8fafc";
  ctx.beginPath();
  ctx.ellipse(rx, ry, 5, 6.5, angle, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  ctx.stroke();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

function drawPlayerFigure(
  ctx: CanvasRenderingContext2D,
  cx: number,
  feetY: number,
  palette: { shirt: string; short: string; skin: string },
  swinging: boolean,
  facing: "up" | "down"
) {
  const dir = facing === "up" ? -1 : 1;
  const bodyTopY = feetY - 22;
  const bodyH = 16;
  const bodyW = 11;
  const shoulderY = bodyTopY + 2;
  const headY = bodyTopY - 7;
  const racketHandX = cx + 8;
  const racketHandY = shoulderY + (swinging ? -2 * dir : 1 * dir);

  // Shoe shadows
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.ellipse(cx - 4, feetY + 1, 2.4, 1.5, 0, 0, Math.PI * 2);
  ctx.ellipse(cx + 4, feetY + 1, 2.4, 1.5, 0, 0, Math.PI * 2);
  ctx.fill();

  // Legs
  ctx.strokeStyle = "#1f2937";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx - 3, bodyTopY + bodyH);
  ctx.lineTo(cx - 3, feetY);
  ctx.moveTo(cx + 3, bodyTopY + bodyH);
  ctx.lineTo(cx + 3, feetY);
  ctx.stroke();

  // Shorts
  ctx.fillStyle = palette.short;
  ctx.fillRect(cx - bodyW / 2, bodyTopY + bodyH - 4, bodyW, 5);

  // Torso (cross-browser rounded rect)
  ctx.fillStyle = palette.shirt;
  roundRect(ctx, cx - bodyW / 2, bodyTopY, bodyW, bodyH, 3);
  ctx.fill();

  // Non-racket arm
  ctx.strokeStyle = palette.skin;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(cx - 4, shoulderY);
  ctx.lineTo(cx - 10, shoulderY + 4 * dir);
  ctx.stroke();

  // Racket arm
  ctx.beginPath();
  ctx.moveTo(cx + 4, shoulderY);
  ctx.lineTo(racketHandX, racketHandY);
  ctx.stroke();

  // Head
  ctx.fillStyle = palette.skin;
  ctx.beginPath();
  ctx.arc(cx, headY, 5.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Hair cap
  ctx.fillStyle = "#111827";
  ctx.beginPath();
  ctx.arc(cx, headY - 1, 5.5, Math.PI, Math.PI * 2);
  ctx.fill();

  drawStickRacket(ctx, racketHandX, racketHandY, true, swinging);
}

export function renderCourt(ctx: CanvasRenderingContext2D, snap: GameSnapshot) {
  ctx.save();

  // Sky gradient (top 12%)
  const skyH = COURT_H * 0.12;
  const skyGrad = ctx.createLinearGradient(0, 0, 0, skyH);
  skyGrad.addColorStop(0, "#191e32");
  skyGrad.addColorStop(1, "#323f5f");
  ctx.fillStyle = skyGrad;
  ctx.fillRect(0, 0, COURT_W, skyH);

  // Dark floor
  ctx.fillStyle = "#141c2a";
  ctx.fillRect(0, skyH, COURT_W, COURT_H - skyH);

  // Court shadow
  ctx.save();
  ctx.globalAlpha = 0.22;
  ctx.fillStyle = "#000a1a";
  ctx.beginPath();
  ctx.moveTo(BOT_LEFT[0] + 6, BOT_LEFT[1] + 6);
  ctx.lineTo(BOT_RIGHT[0] + 6, BOT_RIGHT[1] + 6);
  ctx.lineTo(TOP_RIGHT[0] + 3, TOP_RIGHT[1] + 3);
  ctx.lineTo(TOP_LEFT[0] + 3, TOP_LEFT[1] + 3);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Court surface
  ctx.beginPath();
  ctx.moveTo(BOT_LEFT[0], BOT_LEFT[1]);
  ctx.lineTo(BOT_RIGHT[0], BOT_RIGHT[1]);
  ctx.lineTo(TOP_RIGHT[0], TOP_RIGHT[1]);
  ctx.lineTo(TOP_LEFT[0], TOP_LEFT[1]);
  ctx.closePath();
  ctx.fillStyle = "#4a7c59";
  ctx.fill();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.stroke();

  // White court lines
  ctx.strokeStyle = "rgba(255,255,255,0.65)";
  ctx.lineWidth = 1;
  for (const ny of [0.25, 0.5, 0.75]) {
    const [x1, y1] = courtPoint(0, ny);
    const [x2, y2] = courtPoint(1, ny);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }
  { // Centre line
    const [x1, y1] = courtPoint(0.5, 0);
    const [x2, y2] = courtPoint(0.5, 1);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }

  // Net
  const netY = courtPoint(0, 0.5)[1];
  const [netLx] = rowXs(netY);
  const [, netRx] = rowXs(netY);
  const netH = 10;
  ctx.fillStyle = "rgba(30,30,30,0.85)";
  ctx.fillRect(netLx, netY - netH / 2, netRx - netLx, netH);
  ctx.strokeStyle = "rgba(80,80,80,0.6)";
  ctx.lineWidth = 0.5;
  for (let x = netLx; x < netRx; x += 8) {
    ctx.beginPath();
    ctx.moveTo(x, netY - netH / 2);
    ctx.lineTo(x, netY + netH / 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "#dcdcdc";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(netLx, netY - netH / 2);
  ctx.lineTo(netRx, netY - netH / 2);
  ctx.stroke();

  // Net flash
  if (snap.netFlash) {
    ctx.fillStyle = "rgba(255,80,0,0.38)";
    ctx.fillRect(netLx, netY - netH / 2 - 3, netRx - netLx, netH + 6);
  }

  // Hit zone highlight
  if (snap.hitWindow) {
    ctx.fillStyle = "rgba(250,204,21,0.14)";
    ctx.fillRect(0, COURT_H * 0.60, COURT_W, COURT_H * 0.40);
  }

  // AI figure
  const aiCenterX = snap.aiX + PADDLE_W / 2;
  const aiFeetY = MARGIN_TOP + 30;
  drawPlayerFigure(
    ctx,
    aiCenterX,
    aiFeetY,
    { shirt: snap.aiSwinging ? "#fb923c" : "#ef4444", short: "#7f1d1d", skin: "#f2c39b" },
    snap.aiSwinging,
    "up"
  );

  // Player figure
  const playerCenterX = snap.playerX + PADDLE_W / 2;
  const playerFeetY = COURT_H - 28;
  drawPlayerFigure(
    ctx,
    playerCenterX,
    playerFeetY,
    { shirt: snap.playerSwinging ? "#22c55e" : "#3b82f6", short: "#1e3a8a", skin: "#f5cba7" },
    snap.playerSwinging,
    "down"
  );

  // Ball shadow
  ctx.save();
  ctx.globalAlpha = 0.3;
  ctx.fillStyle = "#000";
  ctx.beginPath();
  ctx.ellipse(snap.bx + 3, snap.by + 5, BALL_R * 0.8, BALL_R * 0.4, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  // Ball
  ctx.fillStyle = snap.outFlash ? "#f43f5e" : "#fde047";
  ctx.beginPath();
  ctx.arc(snap.bx, snap.by, BALL_R, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#92400e";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Score HUD
  ctx.fillStyle = "rgba(0,0,0,0.5)";
  const hudW = 90;
  ctx.fillRect(COURT_W / 2 - hudW / 2, 14, hudW, 24);
  ctx.fillStyle = "#fde047";
  ctx.font = "bold 14px monospace";
  ctx.textAlign = "center";
  ctx.fillText(`${snap.playerScore}  —  ${snap.aiScore}`, COURT_W / 2, 31);

  // Pause reason overlay
  if (snap.pauseReason) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(COURT_W / 2 - 48, COURT_H / 2 - 14, 96, 24);
    ctx.fillStyle = snap.pauseReason === "OUT" ? "#f43f5e" : "#fb923c";
    ctx.font = "bold 13px monospace";
    ctx.textAlign = "center";
    ctx.fillText(snap.pauseReason, COURT_W / 2, COURT_H / 2 + 5);
  }

  // Rally counter
  if (snap.rally > 0) {
    ctx.fillStyle = "rgba(0,0,0,0.4)";
    ctx.fillRect(4, 14, 52, 18);
    ctx.fillStyle = "#9bbc0f";
    ctx.font = "9px monospace";
    ctx.textAlign = "left";
    ctx.fillText(`RALLY ${snap.rally}`, 8, 27);
  }

  // Labels
  ctx.fillStyle = "rgba(255,255,255,0.55)";
  ctx.font = "8px monospace";
  ctx.textAlign = "left";
  ctx.fillText("CPU", 4, MARGIN_TOP + 14);
  ctx.fillText("YOU", 4, COURT_H - 28 + 14);

  ctx.restore();
}
