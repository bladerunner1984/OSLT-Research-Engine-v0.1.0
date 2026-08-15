import pytest
from pydantic import ValidationError

from oslt_research.domain.enums import ModelFamily
from oslt_research.domain.models import CertaintyVector, ScopeContext


def test_certainty_minimum_and_mean(certainty_factory):
    vector = certainty_factory(0.8, causal_identification=0.2)
    assert vector.minimum() == ("causal_identification", 0.2)
    assert 0.7 < vector.mean() < 0.8


def test_scope_comparison_key_is_normalised():
    scope = ScopeContext(
        construct=" Construct ",
        population="POPULATION",
        period=" 2020 ",
        jurisdiction="UK",
        estimand="Risk Difference",
    )
    assert scope.comparison_key() == (
        "construct",
        "population",
        "2020",
        "uk",
        "risk difference",
    )


def test_certainty_bounds_fail():
    payload = {name: 0.5 for name in CertaintyVector.model_fields}
    payload["replication"] = 1.1
    with pytest.raises(ValidationError):
        CertaintyVector(**payload)


def test_model_family_registry_value_is_preserved():
    assert ModelFamily.NULL_OR_ALTERNATIVE.value == "NULL_OR_ALTERNATIVE"
