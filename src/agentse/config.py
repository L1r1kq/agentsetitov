from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(default="0.0.0.0", alias="AGENTSE_HOST")
    port: int = Field(default=8080, alias="AGENTSE_PORT")
    log_level: str = Field(default="INFO", alias="AGENTSE_LOG_LEVEL")

    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    model: str = Field(default="gemma2:2b", alias="AGENTSE_MODEL")
    eval_models: str = Field(
        default="llama3.2:1b,qwen2.5:1.5b,gemma2:2b",
        alias="AGENTSE_EVAL_MODELS",
    )
    temperature: float = Field(default=0.2, alias="AGENTSE_TEMPERATURE")
    max_tokens: int = Field(default=512, alias="AGENTSE_MAX_TOKENS")
    timeout_s: float = Field(default=90.0, alias="AGENTSE_TIMEOUT_S")

    routing_mode: str = Field(default="hybrid", alias="AGENTSE_ROUTING_MODE")
    max_steps: int = Field(default=8, alias="AGENTSE_MAX_STEPS")

    workspace: Path = Field(default=Path("./workspace"), alias="AGENTSE_WORKSPACE")
    data_dir: Path = Field(default=Path("./data"), alias="AGENTSE_DATA_DIR")
    embed_model: str = Field(default="nomic-embed-text", alias="AGENTSE_EMBED_MODEL")
    memory_decay: float = Field(default=0.97, alias="AGENTSE_MEMORY_DECAY")

    sandbox_url: str = Field(default="http://127.0.0.1:8090", alias="AGENTSE_SANDBOX_URL")
    sandbox_timeout_s: float = Field(default=8.0, alias="AGENTSE_SANDBOX_TIMEOUT_S")
    sandbox_enabled: bool = Field(default=True, alias="AGENTSE_SANDBOX_ENABLED")

    otel_endpoint: str = Field(default="http://127.0.0.1:4318", alias="AGENTSE_OTEL_ENDPOINT")
    langfuse_host: str = Field(default="http://127.0.0.1:3000", alias="AGENTSE_LANGFUSE_HOST")
    langfuse_public_key: str = Field(default="", alias="AGENTSE_LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="AGENTSE_LANGFUSE_SECRET_KEY")
    prometheus_port: int = Field(default=9108, alias="AGENTSE_PROMETHEUS_PORT")
    enable_langfuse: bool = Field(default=False, alias="AGENTSE_ENABLE_LANGFUSE")

    @property
    def eval_model_list(self) -> list[str]:
        return [m.strip() for m in self.eval_models.split(",") if m.strip()]

    @property
    def runtime_dir(self) -> Path:
        return self.data_dir / "runtime"

    @property
    def traces_dir(self) -> Path:
        return self.data_dir / "traces"

    @property
    def eval_runs_dir(self) -> Path:
        return self.data_dir / "eval-runs"

    @property
    def db_path(self) -> Path:
        return self.runtime_dir / "memory.sqlite"

    def ensure_dirs(self) -> None:
        for path in (
            self.workspace,
            self.workspace / "memory",
            self.runtime_dir,
            self.traces_dir,
            self.eval_runs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
