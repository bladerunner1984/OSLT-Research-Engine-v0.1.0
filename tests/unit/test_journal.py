import json

from oslt_research.evidence.journal import ResearchComputationJournal


def test_journal_hash_chain_verifies_and_detects_tampering(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal = ResearchComputationJournal(path)
    journal.append("START", {"run": "R1"})
    journal.append("END", {"status": "ok"})
    assert journal.verify()

    lines = path.read_text().splitlines()
    second = json.loads(lines[1])
    second["payload"]["status"] = "tampered"
    lines[1] = json.dumps(second)
    path.write_text("\n".join(lines) + "\n")
    assert not journal.verify()
