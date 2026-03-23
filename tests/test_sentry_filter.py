"""Unit tests for Sentry sensitive data filtering."""

from cashpilot.core.sentry import _filter_sensitive_data


def test_filter_sensitive_data_skips_filtering_in_test_environment(monkeypatch) -> None:
    """Do not filter payloads in test/testing environments."""
    monkeypatch.setenv("ENVIRONMENT", "testing")

    event = {
        "extra": {"sql_query": "SELECT * FROM users"},
        "breadcrumbs": [{"message": "SELECT 1"}],
    }

    result = _filter_sensitive_data(event, hint={})

    assert result is event
    assert result["extra"]["sql_query"] == "SELECT * FROM users"
    assert result["breadcrumbs"][0]["message"] == "SELECT 1"


def test_filter_sensitive_data_removes_sql_from_extra_in_non_test_environment(monkeypatch) -> None:
    """Remove entries in extra where key or value appears to contain SQL data."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    event = {
        "extra": {
            "query": "regular query text",
            "sql_statement": "UPDATE users SET active=true",
            "safe_key": "safe value",
            "metadata": {"note": "no sql here"},
        }
    }

    result = _filter_sensitive_data(event, hint={})

    assert result["extra"] == {
        "query": "regular query text",
        "safe_key": "safe value",
    }


def test_filter_sensitive_data_removes_sql_breadcrumbs_in_non_test_environment(monkeypatch) -> None:
    """Keep non-SQL breadcrumbs and drop SQL-looking breadcrumb entries."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    event = {
        "breadcrumbs": [
            {"message": "User opened dashboard"},
            {"message": "sql debug trace"},
            "raw breadcrumb entry",
            "sql adapter message",
        ]
    }

    result = _filter_sensitive_data(event, hint={})

    assert result["breadcrumbs"] == [
        {"message": "User opened dashboard"},
        "raw breadcrumb entry",
    ]


def test_filter_sensitive_data_tolerates_non_mapping_extra_and_non_list_breadcrumbs(monkeypatch) -> None:
    """Ignore malformed payload sections without crashing or altering other keys."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    event = {
        "extra": "not-a-dict",
        "breadcrumbs": "not-a-list",
        "tags": {"service": "cashpilot"},
    }

    result = _filter_sensitive_data(event, hint={})

    assert result["extra"] == "not-a-dict"
    assert result["breadcrumbs"] == "not-a-list"
    assert result["tags"] == {"service": "cashpilot"}
