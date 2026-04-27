import {
  COURT_W, COURT_H, BALL_R, PADDLE_W, PADDLE_H, MARGIN_TOP,
  BOT_LEFT, BOT_RIGHT, TOP_LEFT, TOP_RIGHT, rowXs,
} from "./browserGameState";
import type { GameSnapshot } from "./browserGameState";

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

function courtPoint(nx: number, ny: number): [number, number] {
  const y = lerp(TOP_LEFT[1], BOT_LEFT[1], ny);
  const [lx, rx] = rowXs(y);
  return [lerp(lx, rx, nx), y];
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

  // AI paddle
  ctx.fillStyle = snap.aiSwinging ? "#fb923c" : "#ef4444";
  ctx.fillRect(snap.aiX, MARGIN_TOP - PADDLE_H / 2, PADDLE_W, PADDLE_H);
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(snap.aiX, MARGIN_TOP - PADDLE_H / 2, PADDLE_W, PADDLE_H);

  // Player paddle (at bottom of court, visually)
  const playerY = COURT_H - 28;
  ctx.fillStyle = snap.playerSwinging ? "#22c55e" : "#3b82f6";
  ctx.fillRect(snap.playerX, playerY - PADDLE_H / 2, PADDLE_W, PADDLE_H);
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(snap.playerX, playerY - PADDLE_H / 2, PADDLE_W, PADDLE_H);

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
  ctx.fillText("YOU", 4, playerY + 14);

  ctx.restore();
}
