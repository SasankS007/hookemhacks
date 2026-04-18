from fastapi import APIRouter

router = APIRouter()


@router.get("/leaderboard")
async def get_leaderboard():
    return {
        "leaderboard": [
            {"rank": 1, "player": "Player1", "wins": 42, "losses": 12},
            {"rank": 2, "player": "Player2", "wins": 38, "losses": 15},
            {"rank": 3, "player": "Player3", "wins": 31, "losses": 20},
        ]
    }


@router.post("/result")
async def submit_result():
    return {
        "status": "recorded",
        "message": "Game result saved successfully.",
    }


@router.get("/stats")
async def get_rally_stats():
    return {
        "total_games": 24,
        "wins": 16,
        "losses": 8,
        "win_rate": 66.7,
        "avg_score": 9.2,
        "best_streak": 5,
    }
