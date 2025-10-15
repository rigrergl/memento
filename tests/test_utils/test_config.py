"""Tests for Config class using Pydantic Settings."""
import os
import pytest
from pydantic import ValidationError
from src.utils.config import Config


class TestConfig:
    """Test Config class loading and validation."""

    def test_load_from_env_vars(self, monkeypatch):
        """Test that Config loads from MEMENTO_ prefixed env vars."""
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "custom")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "custom-model")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", "/custom/cache")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "test-user")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "test-password")

        config = Config()

        assert config.embedding_provider == "custom"
        assert config.embedding_model == "custom-model"
        assert config.embedding_cache_dir == "/custom/cache"
        assert config.neo4j_uri == "neo4j+s://test.databases.neo4j.io"
        assert config.neo4j_user == "test-user"
        assert config.neo4j_password == "test-password"

    def test_env_prefix_required(self, monkeypatch):
        """Test that env vars without MEMENTO_ prefix are ignored."""
        # Set all required env vars with MEMENTO_ prefix
        monkeypatch.setenv("MEMENTO_EMBEDDING_PROVIDER", "local")
        monkeypatch.setenv("MEMENTO_EMBEDDING_MODEL", "correct-model")
        monkeypatch.setenv("MEMENTO_EMBEDDING_CACHE_DIR", ".cache/models")
        monkeypatch.setenv("MEMENTO_NEO4J_URI", "neo4j+s://test.databases.neo4j.io")
        monkeypatch.setenv("MEMENTO_NEO4J_USER", "neo4j")
        monkeypatch.setenv("MEMENTO_NEO4J_PASSWORD", "password")

        # Set env var WITHOUT prefix (should be ignored)
        monkeypatch.setenv("EMBEDDING_MODEL", "should-be-ignored")

        config = Config()

        # Should use the prefixed env var, not the non-prefixed one
        assert config.embedding_model == "correct-model"

    def test_missing_required_fields_raises_validation_error(self, monkeypatch, tmp_path):
        """Test that Config raises ValidationError when required fields are missing."""
        # Clear all MEMENTO_ env vars to ensure no config is set
        for key in list(os.environ.keys()):
            if key.startswith("MEMENTO_"):
                monkeypatch.delenv(key, raising=False)

        # Change to a temp directory so .env file isn't loaded
        monkeypatch.chdir(tmp_path)

        # Attempting to create Config without required env vars should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Config()

        # Verify the error mentions missing fields (at least some of them)
        error_message = str(exc_info.value)
        assert "Field required" in error_message
        # Check that it's a validation error with multiple fields
        assert "validation error" in error_message.lower()
