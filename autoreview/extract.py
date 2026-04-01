"""Extract effect sizes from trial records.

For Pilot 1 (cardiology): uses a curated knowledge base of published results.
For Pilot 3 (registry-first): derives from registry data when possible.
"""
import math
from autoreview.models import TrialRecord

# Curated cardiology knowledge base — published primary results
# These are the actual published effect sizes from landmark trials
CARDIO_KB = {
    # SGLT2i in HF
    "NCT03036124": {"name": "DAPA-HF", "measure": "HR", "effect": 0.74, "ci_lo": 0.65, "ci_hi": 0.85,
                     "events_int": 386, "events_ctrl": 502, "n_int": 2373, "n_ctrl": 2371},
    "NCT03057977": {"name": "EMPEROR-Reduced", "measure": "HR", "effect": 0.75, "ci_lo": 0.65, "ci_hi": 0.86,
                     "events_int": 361, "events_ctrl": 462, "n_int": 1863, "n_ctrl": 1867},
    "NCT03619213": {"name": "DELIVER", "measure": "HR", "effect": 0.82, "ci_lo": 0.73, "ci_hi": 0.92,
                     "events_int": 512, "events_ctrl": 610, "n_int": 3131, "n_ctrl": 3132},
    "NCT03521934": {"name": "EMPEROR-Preserved", "measure": "HR", "effect": 0.79, "ci_lo": 0.69, "ci_hi": 0.90,
                     "events_int": 415, "events_ctrl": 511, "n_int": 2997, "n_ctrl": 2991},
    "NCT03242018": {"name": "SOLOIST-WHF", "measure": "HR", "effect": 0.67, "ci_lo": 0.52, "ci_hi": 0.85,
                     "events_int": 51, "events_ctrl": 76, "n_int": 608, "n_ctrl": 614},
    # Statins primary prevention
    "NCT00738725": {"name": "JUPITER", "measure": "HR", "effect": 0.56, "ci_lo": 0.46, "ci_hi": 0.69,
                     "events_int": 142, "events_ctrl": 251, "n_int": 8901, "n_ctrl": 8901},
    "NCT01738828": {"name": "HOPE-3", "measure": "HR", "effect": 0.76, "ci_lo": 0.64, "ci_hi": 0.91,
                     "events_int": 235, "events_ctrl": 304, "n_int": 6361, "n_ctrl": 6344},
}


def extract_from_kb(trial):
    """Try to extract effect size from curated knowledge base."""
    entry = CARDIO_KB.get(trial.nct_id)
    if entry is None:
        return trial

    effect = entry["effect"]
    ci_lo = entry["ci_lo"]
    ci_hi = entry["ci_hi"]

    # Convert to log scale
    log_effect = math.log(effect)
    log_ci_lo = math.log(ci_lo)
    log_ci_hi = math.log(ci_hi)
    se = (log_ci_hi - log_ci_lo) / (2 * 1.96)

    trial.effect_size = log_effect
    trial.ci_lo = log_ci_lo
    trial.ci_hi = log_ci_hi
    trial.se = se
    trial.measure = f"log{entry['measure']}"
    trial.events_intervention = entry.get("events_int")
    trial.events_control = entry.get("events_ctrl")
    trial.n_intervention = entry.get("n_int")
    trial.n_control = entry.get("n_ctrl")
    return trial


def extract_from_registry(trial):
    """Attempt to derive effect estimates from registry data alone.

    This is the novel part of Pilot 3 — can we do meta-analysis
    from registry data without reading publications?

    Strategy:
    - If results are posted on CT.gov, fetch them (future: API v2 results endpoint)
    - If not, use enrollment + status as proxy for feasibility only
    """
    # For now, mark as having no extractable effect
    # In a full implementation, we'd query the CT.gov results API
    if trial.results_posted:
        # Flag for future results extraction
        trial.source = "ctgov_results"
    else:
        trial.source = "ctgov_no_results"
    return trial


def extract_effects(trials, use_kb=True):
    """Extract effect sizes from all trials.

    Returns (extracted, unextracted) — trials with/without effect data.
    """
    extracted = []
    unextracted = []

    for trial in trials:
        if use_kb:
            trial = extract_from_kb(trial)

        if trial.effect_size is not None and trial.se is not None and trial.se > 0:
            extracted.append(trial)
        else:
            trial = extract_from_registry(trial)
            if trial.effect_size is not None and trial.se is not None and trial.se > 0:
                extracted.append(trial)
            else:
                unextracted.append(trial)

    return extracted, unextracted
