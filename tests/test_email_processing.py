
import json
from datetime import date

import pytest

from app import (
    clean_email_text,
    parse_ai_json,
    validate_ai_result,
    guess_category,
    countdown,
)


def test_clean_email_text_removes_extra_whitespace():
    result = clean_email_text("  Hello   world \n\n  ")

    assert isinstance(result, str)
    assert "Hello" in result
    assert "world" in result


def test_parse_ai_json_accepts_valid_json():
    raw = json.dumps({
        "summary": "Assignment due Friday",
        "priority": "High",
    })

    result = parse_ai_json(raw)

    assert isinstance(result, dict)
    assert result["summary"] == "Assignment due Friday"


def test_parse_ai_json_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_ai_json("this is not valid JSON {{{")


def test_validate_ai_result_handles_dictionary():
    data = {
        "summary": "Submit assignment",
        "priority": "High",
    }

    result = validate_ai_result(data)

    assert result is not None


def test_guess_category_returns_a_value():
    result = guess_category("Assignment submission")

    assert isinstance(result, str)
    assert result.strip() != ""


def test_countdown_returns_a_result():
    result = countdown("2026-10-20", date(2026, 10, 13))

    assert result is not None
    assert isinstance(result, tuple)
    assert len(result) == 2
