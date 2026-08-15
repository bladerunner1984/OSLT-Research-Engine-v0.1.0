from __future__ import annotations

from datetime import date

import pytest

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.admission import admit_entity, admit_relation
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    InstitutionalRelation,
    RelationType,
    SystemDomain,
)
from oslt_research.persistence.sqlite import SQLiteStore


@pytest.fixture
def store(tmp_path) -> SQLiteStore:
    instance = SQLiteStore(tmp_path / "ontology.db")
    instance.initialise()
    return instance


def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id="SRC",
        source_uri="https://example.org/x",
        checksum_sha256="a" * 64,
        access_class=AccessClass.OPEN,
    )


def entity(entity_id: str, *, admitted: bool = True) -> InstitutionalEntity:
    return admit_entity(
        InstitutionalEntity(
            entity_id=entity_id,
            canonical_name=f"Body {entity_id}",
            roles=[EntityRole.COMMISSIONER],
            system_domain=SystemDomain.POLICY,
            jurisdiction="UK",
            identifiers={"companies_house": "01234567"},
            provenance=provenance(),
            source_status=SourceStatus.VERIFIED if admitted else SourceStatus.UNVERIFIED,
            dependency_family="register:test",
        )
    )


def relation(relation_id: str, *, admitted: bool = True) -> InstitutionalRelation:
    return admit_relation(
        InstitutionalRelation(
            relation_id=relation_id,
            source_entity_id="A",
            target_entity_id="B",
            relation_type=RelationType.CONTRACTS_WITH,
            valid_from=date(2020, 1, 1) if admitted else None,
            valid_to=date(2024, 1, 1),
            amount_gbp=1234.5,
            provenance=provenance(),
            source_status=SourceStatus.VERIFIED,
            dependency_family="register:test",
        )
    )


def test_entity_round_trips_without_loss(store):
    original = entity("A")
    store.save_entity(original)
    assert store.list_entities() == [original]


def test_relation_round_trips_without_loss(store):
    original = relation("R1")
    store.save_relation(original)
    [restored] = store.list_relations()
    assert restored == original
    assert restored.valid_from == date(2020, 1, 1)
    assert restored.amount_gbp == 1234.5


def test_saving_twice_updates_rather_than_duplicating(store):
    store.save_entity(entity("A"))
    store.save_entity(entity("A"))
    assert len(store.list_entities()) == 1

    store.save_relation(relation("R1"))
    store.save_relation(relation("R1"))
    assert len(store.list_relations()) == 1


def test_admitted_only_filters_both_tables(store):
    store.save_entities([entity("A"), entity("B", admitted=False)])
    store.save_relations([relation("R1"), relation("R2", admitted=False)])
    assert len(store.list_entities()) == 2
    assert len(store.list_entities(admitted_only=True)) == 1
    assert len(store.list_relations()) == 2
    assert len(store.list_relations(admitted_only=True)) == 1


def test_undated_relation_persists_with_a_null_date(store):
    store.save_relation(relation("R1", admitted=False))
    [restored] = store.list_relations()
    assert restored.valid_from is None
    assert restored.admitted is False


def test_empty_store_returns_empty_lists(store):
    assert store.list_entities() == []
    assert store.list_relations() == []


def test_bulk_save_is_equivalent_to_individual_saves(store):
    store.save_entities([entity("A"), entity("B")])
    store.save_relations([relation("R1"), relation("R2")])
    assert len(store.list_entities()) == 2
    assert len(store.list_relations()) == 2
