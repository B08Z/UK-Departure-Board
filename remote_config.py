import os
import requests
import yaml

def load_config(local_path="config.yml"):
    """
    Load configuration from remote URL (if REMOTE_CONFIG_URL set),
    falling back to local config.yml
    """
    remote_url = os.getenv("REMOTE_CONFIG_URL")
    if remote_url:
        try:
            resp = requests.get(remote_url, timeout=5)
            resp.raise_for_status()
            return yaml.safe_load(resp.text)
        except Exception as e:
            print(f"[remote_config] Failed to fetch remote config: {e}")
    # fallback
    with open(local_path, "r") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    cfg = load_config()
    print(cfg)
