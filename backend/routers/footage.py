from fastapi import APIRouter

router = APIRouter()


@router.post("/upload")
async def upload_footage():
    return {
        "status": "uploaded",
        "file_id": "abc123",
        "message": "Footage uploaded. Processing will begin shortly.",
    }


@router.get("/analysis/{file_id}")
async def get_analysis(file_id: str):
    return {
        "file_id": file_id,
        "status": "complete",
        "stats": {
            "total_shots": 142,
            "distribution": {
                "forehand": 42,
                "backhand": 28,
                "volley": 38,
                "slice": 34,
            },
            "avg_rally_length": 6.3,
            "error_rate": 18,
            "winner_rate": 24,
        },
        "zones": [
            {"id": "tl", "label": "Back Left", "shots": 18},
            {"id": "tc", "label": "Back Center", "shots": 12},
            {"id": "ml", "label": "Mid Left", "shots": 28},
            {"id": "mc", "label": "Mid Center", "shots": 35},
            {"id": "bl", "label": "Kitchen Left", "shots": 32},
            {"id": "bc", "label": "Kitchen Right", "shots": 17},
        ],
        "timeline": [
            {"id": "1", "time": "0:12", "type": "Forehand", "zone": "mc", "result": "rally"},
            {"id": "2", "time": "0:18", "type": "Backhand", "zone": "ml", "result": "rally"},
            {"id": "3", "time": "0:24", "type": "Volley", "zone": "bl", "result": "winner"},
            {"id": "4", "time": "0:41", "type": "Forehand", "zone": "tl", "result": "rally"},
            {"id": "5", "time": "0:55", "type": "Slice", "zone": "tc", "result": "error"},
        ],
    }


@router.get("/history")
async def get_footage_history():
    return {
        "videos": [
            {
                "id": "abc123",
                "filename": "match_2025_04_17.mp4",
                "uploaded_at": "2025-04-17T10:30:00Z",
                "status": "analyzed",
                "total_shots": 142,
            },
            {
                "id": "def456",
                "filename": "practice_2025_04_15.mov",
                "uploaded_at": "2025-04-15T14:00:00Z",
                "status": "analyzed",
                "total_shots": 87,
            },
        ]
    }
