import pytest
from pydantic import ValidationError

from carbon_preaudit.domain.models import ClaimedValue


def test_claimed_value_with_both_or_neither_is_valid() -> None:
    assert ClaimedValue[float]().value is None
    assert ClaimedValue[float](value=1.5, quote="1.5 ha").value == 1.5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"value": 1.0},
        {"quote": "1 ha"},
        {"value": 1.0, "quote": ""},
        {"value": float("nan"), "quote": "nan ha"},
    ],
)
def test_claimed_value_one_sided_or_not_finite_is_invalid(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ClaimedValue[float].model_validate(kwargs)
