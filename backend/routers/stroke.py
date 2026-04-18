from fastapi import APIRouter

router = APIRouter()

MOCK_TIPS = {
    "forehand": [
        {"type": "success", "text": "Good continental grip detected — solid foundation."},
        {"type": "warning", "text": "Elbow extending too early on the follow-through."},
        {"type": "tip", "text": "Try rotating your hips more to generate power from the core."},
        {"type": "tip", "text": "Keep your paddle face slightly open at contact point."},
    ],
    "backhand": [
        {"type": "success", "text": "Two-handed grip is well-positioned."},
        {"type": "warning", "text": "Footwork needs adjustment — step into the shot more."},
        {"type": "tip", "text": "Focus on leading with the knuckles for a cleaner contact."},
        {"type": "tip", "text": "Keep your non-dominant hand engaged longer through the swing."},
    ],
    "volley": [
        {"type": "success", "text": "Good net positioning — staying compact."},
        {"type": "warning", "text": "Wrist is too loose on contact — firm it up."},
        {"type": "tip", "text": "Punch the ball, don't swing. Short, decisive movements."},
        {"type": "tip", "text": "Keep the paddle out in front of your body at all times."},
    ],
    "slice": [
        {"type": "success", "text": "Nice beveled grip for the slice approach."},
        {"type": "warning", "text": "Opening the paddle face too much — shots floating high."},
        {"type": "tip", "text": "Brush under the ball with a downward-to-forward motion."},
        {"type": "tip", "text": "Stay low through the shot — bend your knees more."},
    ],
}

MOCK_SCORES = {
    "forehand": {"accuracy": 87, "power": 72, "consistency": 81},
    "backhand": {"accuracy": 74, "power": 65, "consistency": 69},
    "volley": {"accuracy": 91, "power": 58, "consistency": 85},
    "slice": {"accuracy": 68, "power": 61, "consistency": 73},
}


@router.get("/tips/{stroke_type}")
async def get_stroke_tips(stroke_type: str):
    tips = MOCK_TIPS.get(stroke_type, MOCK_TIPS["forehand"])
    return {"stroke_type": stroke_type, "tips": tips}


@router.get("/scores/{stroke_type}")
async def get_stroke_scores(stroke_type: str):
    scores = MOCK_SCORES.get(stroke_type, MOCK_SCORES["forehand"])
    return {"stroke_type": stroke_type, "scores": scores}


@router.post("/analyze")
async def analyze_stroke():
    return {
        "status": "complete",
        "stroke_type": "forehand",
        "scores": MOCK_SCORES["forehand"],
        "tips": MOCK_TIPS["forehand"],
    }
