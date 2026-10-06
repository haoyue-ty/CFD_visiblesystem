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
    deepseek_model: str = "deepseek-flash"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    deepseek_max_retries: int = Field(default=1, ge=0, le=2)
    ai_max_output_tokens: int = Field(default=2048, ge=512, le=4096)
    ai_daily_token_budget: int = Field(default=500000, ge=4096, le=2000000)
    ai_max_input_chars: int = Field(default=32000, ge=4096, le=32000)
    max_concurrent_runs: int = Field(default=1, ge=1, le=1)
    max_queued_runs: int = Field(default=3, ge=1, le=10)
    max_run_seconds: float = Field(default=1800, gt=0, le=1800)
    max_run_output_bytes: int = Field(default=67108864, ge=1048576, le=67108864)
    waitress_threads: int = Field(default=12, ge=8, le=64)
    max_sse_connections: int = Field(default=4, ge=1, le=4)

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
            deepseek_model=os.getenv("DEEPSEEK_MODEL") or "deepseek-flash",
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
            deepseek_timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS") or "30"),
            deepseek_max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES") or "1"),
            ai_max_output_tokens=int(os.getenv("AI_MAX_OUTPUT_TOKENS") or "2048"),
            ai_daily_token_budget=int(os.getenv("AI_DAILY_TOKEN_BUDGET") or "500000"),
            ai_max_input_chars=int(os.getenv("AI_MAX_INPUT_CHARS") or "32000"),
            max_concurrent_runs=int(os.getenv("MAX_CONCURRENT_RUNS") or "1"),
            max_queued_runs=int(os.getenv("MAX_QUEUED_RUNS") or "3"),
            max_run_seconds=float(os.getenv("MAX_RUN_SECONDS") or "1800"),
            max_run_output_bytes=int(os.getenv("MAX_RUN_OUTPUT_BYTES") or "67108864"),
            waitress_threads=int(os.getenv("WAITRESS_THREADS") or "12"),
            max_sse_connections=int(os.getenv("MAX_SSE_CONNECTIONS") or "4"),
        )
