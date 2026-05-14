from pathlib import Path

from autoreview.models import PICOQuery, TrialRecord
from autoreview.pipeline import run_autoreview


ROOT = Path(__file__).resolve().parents[1]


def test_package_artifacts_present():
    required = [
        "autoreview/__init__.py",
        "autoreview/pipeline.py",
        "autoreview/search.py",
        "autoreview/extract.py",
        "autoreview/manuscript.py",
        "e156-submission/index.html",
        "output/pilot_battery_results.json",
    ]
    for rel_path in required:
        assert (ROOT / rel_path).exists(), rel_path


def test_generated_artifacts_and_local_paths_are_excluded():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    matcher_source = (ROOT / "autoreview" / "matcher.py").read_text(encoding="utf-8")

    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert "C:/Projects" not in matcher_source
    assert "C:\\Projects" not in matcher_source


def test_pipeline_smoke(monkeypatch):
    query = PICOQuery(
        population="heart failure",
        intervention="sglt2 inhibitor",
        comparator="placebo",
        outcome="cardiovascular death or heart failure hospitalization",
    )

    trials = [
        TrialRecord(
            nct_id="NCT03036124",
            title="DAPA-HF",
            phase="Phase 3",
            enrollment=4744,
            sponsor="AstraZeneca",
            conditions=["heart failure"],
            interventions=["dapagliflozin", "placebo"],
            primary_outcome="cardiovascular death or heart failure hospitalization",
            results_posted=True,
        ),
        TrialRecord(
            nct_id="NCT03057977",
            title="EMPEROR-Reduced",
            phase="Phase 3",
            enrollment=3730,
            sponsor="Boehringer Ingelheim",
            conditions=["heart failure"],
            interventions=["empagliflozin", "placebo"],
            primary_outcome="cardiovascular death or heart failure hospitalization",
            results_posted=True,
        ),
        TrialRecord(
            nct_id="NCT03619213",
            title="DELIVER",
            phase="Phase 3",
            enrollment=6263,
            sponsor="AstraZeneca",
            conditions=["heart failure"],
            interventions=["dapagliflozin", "placebo"],
            primary_outcome="worsening heart failure or cardiovascular death",
            results_posted=True,
        ),
    ]

    monkeypatch.setattr("autoreview.pipeline.search_ctgov", lambda q, max_results=100: trials)

    result = run_autoreview(query, use_kb=True, max_search=25)

    assert result.certification == "PASS"
    assert result.pooled.k == 3
    assert result.pooled.measure == "logHR"
    assert result.grade.overall in {"Moderate", "Low", "Very Low", "High"}
    assert "PRISMA Flow Diagram" in result.prisma_flow
    assert "Autonomous Systematic Review" in result.manuscript
    assert len(result.forest_data) == 4


def test_forest_data_summary_row(monkeypatch):
    query = PICOQuery(
        population="heart failure",
        intervention="sglt2 inhibitor",
        comparator="placebo",
        outcome="heart failure hospitalization",
    )

    trials = [
        TrialRecord(
            nct_id="NCT03036124",
            title="DAPA-HF",
            phase="Phase 3",
            enrollment=4744,
            sponsor="AstraZeneca",
            conditions=["heart failure"],
            interventions=["dapagliflozin"],
            primary_outcome="heart failure hospitalization",
            results_posted=True,
        ),
        TrialRecord(
            nct_id="NCT03057977",
            title="EMPEROR-Reduced",
            phase="Phase 3",
            enrollment=3730,
            sponsor="Boehringer Ingelheim",
            conditions=["heart failure"],
            interventions=["empagliflozin"],
            primary_outcome="heart failure hospitalization",
            results_posted=True,
        ),
        TrialRecord(
            nct_id="NCT03619213",
            title="DELIVER",
            phase="Phase 3",
            enrollment=6263,
            sponsor="AstraZeneca",
            conditions=["heart failure"],
            interventions=["dapagliflozin"],
            primary_outcome="heart failure hospitalization",
            results_posted=True,
        ),
    ]

    monkeypatch.setattr("autoreview.pipeline.search_ctgov", lambda q, max_results=100: trials)
    result = run_autoreview(query, use_kb=True, max_search=10)

    summary = result.forest_data[-1]
    assert summary["label"] == "Summary"
    assert summary["title"].startswith("RE Model")
    assert summary["n"] > 0
