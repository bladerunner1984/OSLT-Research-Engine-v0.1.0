from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.isrctn import NAMESPACE, IsrctnConnector


def trial(
    *,
    number="12491684",
    assigned="2025-12-17T07:25:35.967687Z",
    title="A trial",
    scientific="A scientific title",
    published="true",
) -> str:
    assigned_attr = f' publicIdentifierDateAssigned="{assigned}"' if assigned else ""
    return f"""<fullTrial><trial isPublished="{published}"{assigned_attr}>
    <isrctn>{number}</isrctn>
    <trialDescription><title>{title}</title>
    <scientificTitle>{scientific}</scientificTitle></trialDescription>
    </trial></fullTrial>"""


def feed(*trials: str, total: int | None = None) -> str:
    count = total if total is not None else len(trials)
    return (
        f'<allTrials totalCount="{count}" xmlns="{NAMESPACE}">'
        + "".join(trials)
        + "</allTrials>"
    )


def connector_for(body: str, *, status: int = 200) -> IsrctnConnector:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, text=body, headers={"content-type": "application/xml"})
    )
    return IsrctnConnector(client=httpx.Client(transport=transport))


def test_trial_becomes_a_dated_registration():
    sweep = connector_for(feed(trial())).sweep(concept="x")
    [record] = sweep.registrations
    assert record.registration_id == "ISRCTN12491684"
    assert record.registered_on == date(2025, 12, 17)
    assert record.title == "A scientific title"


def test_scientific_title_is_preferred_over_display_title():
    sweep = connector_for(feed(trial(scientific="Precise title"))).sweep(concept="x")
    assert sweep.registrations[0].title == "Precise title"


def test_display_title_is_used_when_no_scientific_title():
    body = feed(trial(scientific=""))
    assert connector_for(body).sweep(concept="x").registrations[0].title == "A trial"


def test_registration_date_comes_from_the_identifier_assignment():
    """When the identifier entered the public record, not when the study ran."""

    sweep = connector_for(feed(trial(assigned="2020-06-01T00:00:00Z"))).sweep(concept="x")
    assert sweep.registrations[0].registered_on == date(2020, 6, 1)


def test_undated_registration_is_skipped():
    """It cannot anchor a publication window, so it would inflate the numerator."""

    sweep = connector_for(feed(trial(assigned=""))).sweep(concept="x")
    assert sweep.registrations == []
    assert sweep.skip_reasons["REGISTRATION_UNDATED"] == 1


def test_trial_without_a_number_is_skipped():
    body = feed("""<fullTrial><trial publicIdentifierDateAssigned="2024-01-01T00:00:00Z">
        <trialDescription><title>No number</title></trialDescription></trial></fullTrial>""")
    sweep = connector_for(body).sweep(concept="x")
    assert sweep.skip_reasons["NO_REGISTRATION_NUMBER"] == 1


def test_published_flag_is_carried_through():
    assert connector_for(feed(trial(published="true"))).sweep(concept="x").registrations[0].status == "published"
    assert connector_for(feed(trial(published="false"))).sweep(concept="x").registrations[0].status == "unpublished"


def test_total_available_is_reported_separately_from_returned():
    sweep = connector_for(feed(trial(), total=250)).sweep(concept="x")
    assert sweep.total_available == 250
    assert sweep.trials_seen == 1


def test_malformed_xml_does_not_raise():
    sweep = connector_for("<allTrials>not closed").sweep(concept="x")
    assert sweep.registrations == []
    assert sweep.skip_reasons["XML_PARSE_FAILED"] == 1


def test_empty_feed_is_safe():
    assert connector_for(feed()).sweep(concept="x").registrations == []


def test_http_error_propagates():
    with pytest.raises(httpx.HTTPStatusError):
        connector_for("", status=503).sweep(concept="x")
