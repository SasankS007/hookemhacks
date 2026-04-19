import { NextRequest, NextResponse } from "next/server";

/**
 * Proxies ElevenLabs TTS (server-side key only).
 * Returns 501 if ELEVENLABS_API_KEY is not set — clients should fall back to beeps.
 */
export async function POST(req: NextRequest) {
  const apiKey = process.env.ELEVENLABS_API_KEY;
  const voiceId =
    process.env.ELEVENLABS_VOICE_ID ?? "21m00Tcm4TlvDq8ikWAM";

  if (!apiKey) {
    return NextResponse.json(
      { ok: false, error: "elevenlabs_not_configured" },
      { status: 501 }
    );
  }

  let body: { text?: string };
  try {
    body = (await req.json()) as { text?: string };
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const text = String(body.text ?? "").trim().slice(0, 500);
  if (!text) {
    return NextResponse.json({ error: "missing_text" }, { status: 400 });
  }

  const upstream = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
    {
      method: "POST",
      headers: {
        "xi-api-key": apiKey,
        "Content-Type": "application/json",
        Accept: "audio/mpeg",
      },
      body: JSON.stringify({
        model_id: "eleven_turbo_v2_5",
        text,
      }),
    }
  );

  if (!upstream.ok) {
    const err = await upstream.text();
    return NextResponse.json(
      { error: "upstream", detail: err.slice(0, 200) },
      { status: 502 }
    );
  }

  const buf = await upstream.arrayBuffer();
  return new NextResponse(buf, {
    status: 200,
    headers: {
      "Content-Type": "audio/mpeg",
      "Cache-Control": "private, max-age=3600",
    },
  });
}
