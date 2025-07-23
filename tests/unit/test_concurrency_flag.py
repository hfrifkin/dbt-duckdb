import pytest
from unittest.mock import Mock, patch
from argparse import Namespace
from dbt.flags import set_from_args
from dbt.adapters.duckdb.impl import DuckDBAdapter
from dbt.adapters.duckdb.constants import CONCURRENCY_LEVEL
from tests.unit.utils import config_from_parts_or_dicts


class TestConcurrencyFlag:
    """Test the concurrency flag functionality in the DuckDB adapter."""

    def setup_method(self):
        """Set up test fixtures."""
        set_from_args(Namespace(STRICT_MODE=True), {})

        profile_cfg = {
            "outputs": {
                "test": {
                    "type": "duckdb",
                    "path": ":memory:",
                    "threads": 4,
                }
            },
            "target": "test",
        }

        project_cfg = {
            "name": "X",
            "version": "0.1",
            "profile": "test",
            "project-root": "/tmp/dbt/does-not-exist",
            "quoting": {
                "identifier": False,
                "schema": True,
            },
            "config-version": 2,
        }

        self.config = config_from_parts_or_dicts(project_cfg, profile_cfg, cli_vars={})
        self.mock_mp_context = Mock()
        self.adapter = DuckDBAdapter(self.config, self.mock_mp_context)
        self.adapter._original_threads = None

    def test_concurrency_level_set_to_1(self):
        """Test that concurrency level is set to 1 when specified in model config."""
        # Create a mock config with concurrency_level = 1
        mock_config = Mock()
        mock_config.model = Mock()
        mock_config.model.name = "test_model"
        mock_config.model.config = Mock()
        mock_config.model.config.meta = {CONCURRENCY_LEVEL: 1}

        # Call the method
        self.adapter._set_concurrency_level(mock_config)

        # Verify original threads was stored
        assert self.adapter._original_threads == 4
        
        # Verify threads was set to 1
        assert getattr(self.adapter.config, 'threads') == 1

    def test_concurrency_level_not_set(self):
        """Test that concurrency level is not changed when not specified."""
        # Create a mock config without concurrency_level
        mock_config = Mock()
        mock_config.model = Mock()
        mock_config.model.config = Mock()
        mock_config.model.config.meta = {}

        # Call the method
        self.adapter._set_concurrency_level(mock_config)

        # Verify nothing was changed
        assert self.adapter._original_threads is None
        assert getattr(self.adapter.config, 'threads', 4) == 4

    def test_concurrency_level_other_value(self):
        """Test that concurrency level is not changed when set to other values."""
        # Create a mock config with concurrency_level = 2
        mock_config = Mock()
        mock_config.model = Mock()
        mock_config.model.config = Mock()
        mock_config.model.config.meta = {CONCURRENCY_LEVEL: 2}

        # Call the method
        self.adapter._set_concurrency_level(mock_config)

        # Verify nothing was changed
        assert self.adapter._original_threads is None
        assert getattr(self.adapter.config, 'threads', 4) == 4

    def test_restore_concurrency_level(self):
        """Test that original thread count is restored."""
        # Set up the adapter as if concurrency was changed
        self.adapter._original_threads = 4
        setattr(self.adapter.config, 'threads', 1)

        # Call the restore method
        self.adapter._restore_concurrency_level()

        # Verify threads was restored
        assert getattr(self.adapter.config, 'threads') == 4
        assert self.adapter._original_threads is None

    def test_restore_concurrency_level_no_change(self):
        """Test that restore does nothing when no change was made."""
        # Don't set _original_threads
        self.adapter._original_threads = None
        original_threads = getattr(self.adapter.config, 'threads', 4)

        # Call the restore method
        self.adapter._restore_concurrency_level()

        # Verify nothing was changed
        assert getattr(self.adapter.config, 'threads', 4) == original_threads
        assert self.adapter._original_threads is None

    def test_pre_model_hook_with_concurrency(self):
        """Test that pre_model_hook calls _set_concurrency_level."""
        mock_config = Mock()
        mock_config.model = Mock()
        mock_config.model.config = Mock()
        mock_config.model.config.meta = {CONCURRENCY_LEVEL: 1}

        # Patch the parent class method
        with patch('dbt.adapters.duckdb.impl.SQLAdapter.pre_model_hook') as mock_parent:
            self.adapter.pre_model_hook(mock_config)

            # Verify the parent method was called
            mock_parent.assert_called_once_with(mock_config)

            # Verify concurrency was set
            assert getattr(self.adapter.config, 'threads') == 1

    def test_post_model_hook_with_concurrency(self):
        """Test that post_model_hook calls _restore_concurrency_level."""
        # Set up the adapter as if concurrency was changed
        self.adapter._original_threads = 4
        setattr(self.adapter.config, 'threads', 1)

        mock_config = Mock()
        mock_context = Mock()

        # Patch the parent class method
        with patch('dbt.adapters.duckdb.impl.SQLAdapter.post_model_hook') as mock_parent:
            self.adapter.post_model_hook(mock_config, mock_context)

            # Verify the parent method was called
            mock_parent.assert_called_once_with(mock_config, mock_context)

            # Verify concurrency was restored
            assert getattr(self.adapter.config, 'threads') == 4
            assert self.adapter._original_threads is None 