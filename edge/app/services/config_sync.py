# edge/app/services/config_sync.py
import time
import json
import logging
import threading
import requests
from pathlib import Path
from app.core.config import settings
import os
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(settings.LOG_DIR, "app.log"), encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("intrusion_detection_config_sync")


class ConfigSyncClient:
    def __init__(self):
        self.camera_id = settings.CAMERA_ID
        self.api_url = f"{settings.CENTRAL_API_URL}/edge/{self.camera_id}/config"
        self.cache_file = Path("last_known_config.json")

        # Load initial config from disk for offline resilience
        self.current_config = self._load_from_disk()
        self.current_version = (
            self.current_config.get("config_version") if self.current_config else None
        )

        self.running = True
        self.sync_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Config Sync Client initialized.")

    def _load_from_disk(self):
        """Loads the last successful config from local storage."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    logger.info("Loaded previous configuration from local disk cache.")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config cache: {e}")
        logger.info("Cache config doesn't exists. Continue for polling.")
        return None

    def _save_to_disk(self, config_data):
        """Persists the latest configuration to local storage."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config cache: {e}")

    def _poll_loop(self):
        """Background loop to poll the central API on a timer."""
        while self.running:
            try:
                response = requests.get(
                    self.api_url,
                    timeout=5,
                    proxies={
                        "http": None,
                        "https": None,
                    },
                )
                response.raise_for_status()
                data = response.json()

                new_version = data.get("config_version")
                # Reload Zone Engine geometry only if the version changes
                if new_version != self.current_version:
                    logger.warning(
                        f"New config version detected: {new_version}. Updating local cache."
                    )
                    self.current_version = new_version
                    self.current_config = data
                    self._save_to_disk(data)
            # except requests.exceptions.RequestException as e:
            # logger.debug(f"Config pull failed (API unreachable). Continuing with cached config. Error: {e}")
            except Exception as e:
                logger.error(f"Error while pollling {self.api_url}. Error: {e}")

            # Poll every 30 seconds as specified in the architecture
            time.sleep(30)

    def get_zones(self):
        """Returns the currently active zone definitions."""
        if not self.current_config:
            return []
        return self.current_config.get("zones", [])

    def get_config_version(self):
        """Returns the active configuration version for heartbeat payloads."""
        return self.current_version or "unknown"

    def close(self):
        self.running = False
