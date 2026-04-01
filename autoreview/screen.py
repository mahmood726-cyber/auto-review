"""Screen trials for relevance to the PICO query."""
from autoreview.models import PICOQuery, TrialRecord, ScreeningResult


def _normalize(text):
    return text.lower().strip()


def _matches_any(text, keywords):
    """Check if text contains any of the keywords (case-insensitive)."""
    text_lower = _normalize(text)
    return any(kw.lower() in text_lower for kw in keywords if kw)


def _build_intervention_keywords(intervention_str):
    """Extract searchable keywords from intervention description."""
    keywords = [intervention_str]
    # Common drug class expansions
    expansions = {
        "sglt2": ["sglt2", "dapagliflozin", "empagliflozin", "canagliflozin",
                   "sotagliflozin", "ertugliflozin"],
        "statin": ["statin", "atorvastatin", "rosuvastatin", "simvastatin",
                    "pravastatin", "lovastatin", "fluvastatin", "pitavastatin"],
        "ace inhibitor": ["ace inhibitor", "enalapril", "ramipril", "lisinopril",
                          "perindopril", "captopril"],
        "arb": ["arb", "losartan", "valsartan", "candesartan", "irbesartan",
                 "telmisartan", "olmesartan"],
        "beta blocker": ["beta blocker", "metoprolol", "bisoprolol", "carvedilol",
                         "atenolol", "nebivolol"],
        "anticoagulant": ["anticoagulant", "warfarin", "apixaban", "rivaroxaban",
                          "dabigatran", "edoxaban"],
        "gliflozin": ["gliflozin", "sglt2", "dapagliflozin", "empagliflozin"],
    }
    for key, synonyms in expansions.items():
        if key in _normalize(intervention_str):
            keywords.extend(synonyms)
    return keywords


def _build_population_keywords(population_str):
    """Extract searchable keywords from population description."""
    keywords = [population_str]
    expansions = {
        "heart failure": ["heart failure", "hf", "hfref", "hfpef", "cardiac failure",
                          "ventricular dysfunction"],
        "atrial fibrillation": ["atrial fibrillation", "af", "afib"],
        "coronary": ["coronary", "cad", "acs", "myocardial infarction", "mi",
                      "angina", "pci", "cabg"],
        "hypertension": ["hypertension", "high blood pressure", "htn"],
        "diabetes": ["diabetes", "t2dm", "type 2 diabetes", "diabetic"],
    }
    for key, synonyms in expansions.items():
        if key in _normalize(population_str):
            keywords.extend(synonyms)
    return keywords


def screen_trials(records, query):
    """Screen trials against PICO criteria. Returns ScreeningResult."""
    intervention_kw = _build_intervention_keywords(query.intervention)
    population_kw = _build_population_keywords(query.population)

    included = []
    excluded = []

    for trial in records:
        # Combine all searchable text
        all_text = " ".join([
            trial.title,
            " ".join(trial.conditions),
            " ".join(trial.interventions),
            trial.primary_outcome,
        ])

        # Check intervention match
        if not _matches_any(all_text, intervention_kw):
            excluded.append((trial.nct_id, "intervention_mismatch"))
            continue

        # Check population match
        if not _matches_any(all_text, population_kw):
            excluded.append((trial.nct_id, "population_mismatch"))
            continue

        # Minimum enrollment
        if trial.enrollment < 50:
            excluded.append((trial.nct_id, "too_small"))
            continue

        # Must be RCT (Phase 2-4 or unspecified)
        if query.study_design == "RCT":
            phase_lower = trial.phase.lower() if trial.phase else ""
            if "phase1" in phase_lower.replace(" ", "") and "phase2" not in phase_lower.replace(" ", ""):
                excluded.append((trial.nct_id, "phase1_only"))
                continue

        included.append(trial)

    return ScreeningResult(
        included=included,
        excluded=excluded,
        n_identified=len(records),
        n_screened=len(records),
        n_eligible=len(included),
        n_included=len(included),
    )
