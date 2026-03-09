"""Anonymous telemetry for tracking global cleanup impact."""

import os
import json
import uuid
import platform
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import urllib.request
import urllib.error
from urllib.parse import urlparse
import hmac
import hashlib

# No baked-in URL. Must be provided via env or config.
DEFAULT_TELEMETRY_URL = ""

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Handles anonymous telemetry reporting."""

    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("telemetry", {}).get("enabled", True)
        # Precedence: env TELEMETRY_URL -> config -> default (empty)
        self.url = os.getenv("TELEMETRY_URL") or config.get("telemetry", {}).get("url", DEFAULT_TELEMETRY_URL)
        self.user_id = self._get_or_create_user_id()

    def _get_or_create_user_id(self) -> str:
        """Get existing user ID or generate a new anonymous UUID."""
        config_dir = os.path.dirname(self.config.get("logging", {}).get("log_file", ""))
        # Fallback to home if config_dir is empty/invalid
        if not config_dir:
            config_dir = os.path.expanduser("~/.jhadoo")
            
        id_file = os.path.join(config_dir, "telemetry_id.json")
        
        try:
            if os.path.exists(id_file):
                with open(id_file, 'r') as f:
                    data = json.load(f)
                    return data.get("user_id", str(uuid.uuid4()))
            
            # Create new ID
            new_id = str(uuid.uuid4())
            os.makedirs(os.path.dirname(id_file), exist_ok=True)
            with open(id_file, 'w') as f:
                json.dump({"user_id": new_id, "created": datetime.now().isoformat()}, f)
            return new_id
            
        except Exception:
            return "unknown-user"

    def send_stats(self, bytes_saved: int, duration_seconds: float):
        """Send cleanup statistics asynchronously."""
        if not self.enabled:
            return

        from . import __version__ as pkg_version

        payload = {
            "event_type": "cleanup_completed",
            "device_id": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "version": pkg_version,
            "platform": {
                "system": platform.system(),
                "python_version": platform.python_version(),
            },
            "data": {
                "bytes_saved": bytes_saved,
                "total_size_mb": round(bytes_saved / (1024 * 1024), 2),
                "duration_seconds": round(duration_seconds, 2),
            },
        }

        # Run in a separate thread to not block CLI
        thread = threading.Thread(target=self._send_request, args=(payload,))
        thread.daemon = True
        thread.start()

    def _send_request(self, payload: Dict[str, Any]):
        """Internal method to send HTTP request."""
        try:
            # Check if URL is configured and secure
            if not self.url:
                return  # Silently skip if not configured
            parsed = urlparse(self.url)
            if parsed.scheme not in ("https", "http"):
                return
            if parsed.scheme == "http":
                host = parsed.hostname or ""
                # Allow localhost, 127.0.0.1, and local/test hosts without dots (e.g., 'mock-url')
                if host not in ("127.0.0.1", "localhost") and "." in host:
                    return

            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json'}

            # Optional API key header
            api_key = os.getenv("TELEMETRY_TOKEN")
            if api_key:
                headers['X-API-Key'] = api_key

            # Optional HMAC signing with timestamp
            signing_key = os.getenv("TELEMETRY_SIGNING_KEY")
            if signing_key:
                ts = datetime.utcnow().isoformat()
                headers['X-Timestamp'] = ts
                to_sign = (ts + "\n").encode("utf-8") + data
                sig = hmac.new(signing_key.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
                headers['X-Signature'] = sig

            req = urllib.request.Request(self.url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    logger.debug(f"Telemetry failed with status {response.status}")
        except Exception as e:
            # Fail silently, never annoy user with network errors for telemetry
            logger.debug(f"Telemetry failed: {e}")
