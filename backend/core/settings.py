import os
from pathlib import Path

from pydantic import Field

from backend.models.core import CanonicalModel

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


class Settings(CanonicalModel):
    scientific_data_root: str = ""
    inventory_path: str = ""
    canonical_registry_path: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=5000, ge=1, le=65535)
    enable_accounts: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        accounts = os.getenv("ENABLE_ACCOUNTS", "false").lower()
        if accounts not in ("true", "false"):
            raise ValueError("ENABLE_ACCOUNTS must be true or false")
        return cls(
            scientific_data_root=os.getenv("SCIENTIFIC_DATA_ROOT", ""),
            inventory_path=os.getenv("INVENTORY_PATH", ""),
            canonical_registry_path=os.getenv("CANONICAL_REGISTRY_PATH", ""),
            api_host=os.getenv("API_HOST") or "127.0.0.1",
            api_port=int(os.getenv("API_PORT") or "5000"),
            enable_accounts=accounts == "true",
        )
