"""
Application settings configuration using Pydantic Settings.
Loads configuration from environment variables or .env file with sensible defaults.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    APP_NAME: str = "Faculty Workload Intelligence Assistant"
    APP_VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./storage/database/faculty_workload.db"

    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # "ollama", "offline", "mock"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    LLM_TIMEOUT_SECONDS: int = 30

    # Embeddings & Vector Store
    EMBEDDING_PROVIDER: str = "sentence-transformers"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    VECTOR_STORE_PATH: str = "./storage/vector_store"

    # Dataset & Paths
    DATASET_PATH: str = "./data/faculty_workload_dummy_dataset.xlsx"
    DOCUMENTS_DIR: str = "./storage/documents"
    LOGS_DIR: str = "./logs"
    REPORTS_DIR: str = "./reports"

    # Security & Demo Auth
    DEMO_AUTH_ENABLED: bool = True
    JWT_SECRET_KEY: str = "insecure-demo-secret-key-do-not-use-in-production-12345"
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRE_MINUTES: int = 480

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()

