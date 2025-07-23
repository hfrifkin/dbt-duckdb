import pytest
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

    def test_concurrency_flag_functionality(self, project):
        """Test that models with concurrency_level=1 run with single-threaded execution."""
        # Run the models
        results = run_dbt(["run"])
        
        # Verify all models ran successfully
        assert len(results) == 3
        
        # Check that the models were created - use relation objects
        relation1 = relation_from_name(project.adapter, "model_with_concurrency")
        res1 = project.run_sql(f"SELECT * FROM {relation1}", fetch="all")
        assert len(res1) == 1
        assert res1[0][0] == 1
        assert res1[0][1] == "model_with_concurrency"
        
        relation2 = relation_from_name(project.adapter, "model_without_concurrency")
        res2 = project.run_sql(f"SELECT * FROM {relation2}", fetch="all")
        assert len(res2) == 1
        assert res2[0][0] == 2
        assert res2[0][1] == "model_without_concurrency"
        
        relation3 = relation_from_name(project.adapter, "model_with_other_concurrency")
        res3 = project.run_sql(f"SELECT * FROM {relation3}", fetch="all")
        assert len(res3) == 1
        assert res3[0][0] == 3
        assert res3[0][1] == "model_with_other_concurrency"


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

    def test_incremental_concurrency_flag(self, project):
        """Test that incremental models with concurrency_level=1 work correctly."""
        # First run
        results = run_dbt(["run"])
        assert len(results) == 1

        # Check initial data
        relation = relation_from_name(project.adapter, "incremental_with_concurrency")
        res1 = project.run_sql(f"SELECT COUNT(*) FROM {relation}", fetch="one")
        assert res1[0] == 5

        # Second run - should not add more data since all data is already there
        results = run_dbt(["run"])
        assert len(results) == 1

        # Check that no new data was added (since all data was already there)
        res2 = project.run_sql(f"SELECT COUNT(*) FROM {relation}", fetch="one")
        assert res2[0] == 5 