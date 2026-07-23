# Quick test in a python shell or temporary script
import time
from app.services.config_sync import ConfigSyncClient

sync = ConfigSyncClient()
time.sleep(2) # Give the background thread a moment to hit the API
print(sync.get_zones())
sync.close()