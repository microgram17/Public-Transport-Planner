from app.gtfs.validation import _has_system_errors


def test_empty_system_error_report_is_not_an_error() -> None:
    assert not _has_system_errors({"notices": []})
    assert not _has_system_errors([])
    assert _has_system_errors({"notices": [{"message": "boom"}]})
