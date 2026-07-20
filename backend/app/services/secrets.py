"""Resolve secrets from multiple backends, ordered by security preference.

Priority:
  1. Environment variable      (docker run -e / K8s secrets / CI)
  2. Docker secrets file       (/run/secrets/<key>)
  3. System keyring            (Windows Credential Manager / macOS Keychain / Linux Secret Service)
  4. .env file                 (fallback, prints warning)
  5. Empty string              (graceful degrade — API calls will fail with clear error)
"""

import os
import sys

KEYRING_SERVICE = "jp-vocab"
DOCKER_SECRETS_DIR = "/run/secrets"


def _from_env(key: str) -> str | None:
    val = os.getenv(key)
    if val and val != "":
        return val
    return None


def _from_docker_secrets(key: str) -> str | None:
    path = os.path.join(DOCKER_SECRETS_DIR, key)
    if os.path.isfile(path):
        try:
            return open(path).read().strip()
        except OSError:
            return None
    return None


def _from_keyring(key: str) -> str | None:
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, key)
    except Exception:
        return None


def resolve(key: str) -> str:
    """Return the secret value for `key`, trying each backend in priority order."""
    # 1. Environment variable (highest priority)
    val = _from_env(key)
    if val:
        return val

    # 2. Docker / K8s secrets file
    val = _from_docker_secrets(key)
    if val:
        return val

    # 3. System keyring (no plaintext on disk)
    val = _from_keyring(key)
    if val:
        return val

    # 4. .env file fallback — only for local dev
    from dotenv import dotenv_values

    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_file):
        dotenv_vals = dotenv_values(env_file)
        val = dotenv_vals.get(key)
        if val:
            print(
                f"  [secrets] {key} loaded from .env file — "
                "consider moving it to system keyring:\n"
                "    python -c \"import keyring; "
                f"keyring.set_password('{KEYRING_SERVICE}', '{key}', '<your-key>')\"",
                file=sys.stderr,
            )
            return val

    return ""
