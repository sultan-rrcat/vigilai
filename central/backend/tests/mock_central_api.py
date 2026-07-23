# mock_central_api.py
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/edge/{camera_id}/config")
def get_config(camera_id: str):
    # This schema matches the config-pull response contract
    return {
        "config_version": "v1",
        "min_dwell_seconds": 2.0,
        "track_ttl_seconds": 5.0,
        "zones": [
            {
                "id": "zone_mock_1",
                "name": "Main Entrance",
                "polygon": [[0.2, 0.4], [0.8, 0.4], [0.8, 0.9], [0.2, 0.9]],
                "min_dwell_seconds": 2.0
            }
        ],
        "tripwires": []
    }

if __name__ == "__main__":
    # Run on port 8000 to match the CENTRAL_API_URL in your .env
    uvicorn.run(app, host="0.0.0.0", port=8000)