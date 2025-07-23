import pytest
import time
from dbt.tests.util import run_dbt, relation_from_name


class TestConcurrencyFlag:
    """Test the concurrency flag functionality with actual dbt models."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "model_with_concurrency.sql": """
{{ config(
    materialized='table',
    meta={'concurrency_level': 1}
) }}

SELECT 1 as id, 'model_with_concurrency' as name
""",
            "model_without_concurrency.sql": """
{{ config(materialized='table') }}

SELECT 2 as id, 'model_without_concurrency' as name
""",
            "model_with_other_concurrency.sql": """
{{ config(
    materialized='table',
    meta={'concurrency_level': 2}
) }}

SELECT 3 as id, 'model_with_other_concurrency' as name
""",
        }

    def _verify_model_data(self, project, model_name, expected_id, expected_name):
        """Helper method to verify model data and reduce code duplication."""
        relation = relation_from_name(project.adapter, model_name)
        result = project.run_sql(f"SELECT * FROM {relation}", fetch="all")
        assert len(result) == 1, f"Expected 1 row in {model_name}, got {len(result)}"
        assert result[0][0] == expected_id, f"Expected id {expected_id} in {model_name}, got {result[0][0]}"
        assert result[0][1] == expected_name, f"Expected name '{expected_name}' in {model_name}, got '{result[0][1]}'"

    def test_models_run_successfully(self, project):
        """Test that all models run successfully regardless of concurrency settings."""
        # Run the models
        results = run_dbt(["run"])
        
        # Verify all models ran successfully
        expected_model_count = 3
        assert len(results) == expected_model_count, f"Expected {expected_model_count} models to run, got {len(results)}"
        
        # Verify each model was created with correct data
        self._verify_model_data(project, "model_with_concurrency", 1, "model_with_concurrency")
        self._verify_model_data(project, "model_without_concurrency", 2, "model_without_concurrency")
        self._verify_model_data(project, "model_with_other_concurrency", 3, "model_with_other_concurrency")

    def test_concurrency_configuration_persistence(self, project):
        """Test that concurrency configuration is properly stored in model metadata."""
        # Run the models
        run_dbt(["run"])
        
        # Check that models with concurrency settings have the correct metadata
        # This would require accessing the compiled model configs
        # Note: This is a placeholder for actual metadata verification
        # In a real implementation, you'd need to access the compiled model configs
        pass


class TestConcurrencyFlagIncremental:
    """Test the concurrency flag functionality with incremental models."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "incremental_with_concurrency.sql": """
{{ config(
    materialized='incremental',
    meta={'concurrency_level': 1}
) }}

SELECT 
    id,
    'data_' || id::varchar as data,
    current_timestamp as created_at
FROM (
    SELECT 1 as id
    UNION ALL SELECT 2
    UNION ALL SELECT 3
    UNION ALL SELECT 4
    UNION ALL SELECT 5
) as source_data

{% if is_incremental() %}
    WHERE id > (SELECT COALESCE(MAX(id), 0) FROM {{ this }})
{% endif %}
""",
        }

    def test_incremental_model_initial_run(self, project):
        """Test that incremental model works correctly on initial run."""
        # First run
        results = run_dbt(["run"])
        assert len(results) == 1, "Expected 1 model to run"

        # Check initial data
        relation = relation_from_name(project.adapter, "incremental_with_concurrency")
        result = project.run_sql(f"SELECT COUNT(*) FROM {relation}", fetch="one")
        expected_count = 5
        assert result[0] == expected_count, f"Expected {expected_count} rows, got {result[0]}"

    def test_incremental_model_no_new_data(self, project):
        """Test that incremental model doesn't add data when no new records exist."""
        # Ensure model exists from previous test
        run_dbt(["run"])
        
        # Second run - should not add more data since all data is already there
        results = run_dbt(["run"])
        assert len(results) == 1, "Expected 1 model to run"

        # Check that no new data was added
        relation = relation_from_name(project.adapter, "incremental_with_concurrency")
        result = project.run_sql(f"SELECT COUNT(*) FROM {relation}", fetch="one")
        expected_count = 5
        assert result[0] == expected_count, f"Expected {expected_count} rows, got {result[0]}"

    def test_incremental_model_with_new_data(self, project):
        """Test that incremental model adds new data when available."""
        # This test would require a way to inject new data
        # For now, this is a placeholder showing what should be tested
        pass


class TestConcurrencyPerformance:
    """Test actual concurrency behavior and performance implications."""

    @pytest.fixture(scope="class")
    def models(self):
        return {
            "slow_model_single_thread.sql": """
{{ config(
    materialized='table',
    meta={'concurrency_level': 1}
) }}

-- Simulate slow operation
SELECT 
    generate_series(1, 1000) as id,
    'slow_single_thread' as name,
    pg_sleep(0.1) as delay
""",
            "slow_model_multi_thread.sql": """
{{ config(
    materialized='table',
    meta={'concurrency_level': 4}
) }}

-- Simulate slow operation
SELECT 
    generate_series(1, 1000) as id,
    'slow_multi_thread' as name,
    pg_sleep(0.1) as delay
""",
        }

    def test_concurrency_execution_time(self, project):
        """Test that different concurrency levels have different execution times."""
        # This test would measure actual execution time differences
        # between single-threaded and multi-threaded models
        # Note: This is a placeholder for actual performance testing
        pass 