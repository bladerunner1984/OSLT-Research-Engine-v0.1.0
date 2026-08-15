import csv

from oslt_research.domain.enums import ClaimTier, EpistemicStatus
from oslt_research.domain.models import ReleasedClaim
from oslt_research.evidence.provenance import sha256_text
from oslt_research.pipelines.film import build_scene_records, write_claim_scene_register


def test_film_scene_register_is_claim_bound(tmp_path, certainty_factory):
    claim = ReleasedClaim(
        claim_id="CLM-1",
        proposition_id="MD11",
        wording="The available evidence is consistent with a partial association.",
        epistemic_status=EpistemicStatus.ASSOCIATION,
        claim_tier=ClaimTier.ASSOCIATION_ONLY,
        evidence_ids=["EV-1"],
        counterevidence_ids=["EV-2"],
        dependency_families=["F1"],
        certainty=certainty_factory(0.6),
        permitted_phrases=["is consistent with"],
        prohibited_phrases=["proves"],
        uncertainty_disclosure="Causal identification remains limited.",
        human_review_reference="HR-1",
        release_manifest_hash=sha256_text("release"),
    )
    scenes = build_scene_records([claim])
    assert scenes[0].released_claim_id == "CLM-1"
    assert "proves" in scenes[0].prohibited_wording

    path = write_claim_scene_register([claim], tmp_path / "scenes.csv")
    rows = list(csv.DictReader(path.open()))
    assert rows[0]["released_claim_id"] == "CLM-1"
    assert rows[0]["counterevidence_ids"] == "EV-2"
