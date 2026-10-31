import pytest
from pydantic import ValidationError

from carbon_preaudit.domain.models import ClaimedValue, ClaimedValues, Finding, Severity


def test_claimed_value_both_none_is_valid() -> None:
    cv = ClaimedValue[float]()
    assert cv.value is None
    assert cv.quote is None


def test_claimed_value_both_set_is_valid() -> None:
    cv = ClaimedValue[float](value=1.5, quote="1.5 ha")
    assert cv.value == 1.5


@pytest.mark.parametrize("kwargs", [{"value": 1.0}, {"quote": "1 ha"}, {"value": 1.0, "quote": ""}])
def test_claimed_value_one_sided_is_invalid(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ClaimedValue[float].model_validate(kwargs)


def test_claimed_value_rejects_nan() -> None:
    with pytest.raises(ValidationError):
        ClaimedValue[float](value=float("nan"), quote="nan ha")


def test_claimed_values_default_to_empty_and_are_frozen() -> None:
    claimed = ClaimedValues()
    assert claimed.methodology.value is None
    with pytest.raises(ValidationError):
        claimed.methodology = ClaimedValue[str](value="VM0047", quote="VM0047")  # type: ignore[misc]


def test_finding_field_is_restricted() -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate(
            {
                "field": "vintage",
                "severity": Severity.INFO,
                "claimed": None,
                "computed": 1.0,
                "quote": None,
                "message": "x",
            }
        )
