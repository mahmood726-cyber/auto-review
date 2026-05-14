"""Fuzzy trial matching — ported from MetaSprint Cardio Universe identity engine.

Uses Jaccard token-set similarity + trial acronym alias dictionary to match
CT.gov records to the knowledge base when NCT IDs don't match directly.

Source pattern: metasprint-cardio-universe identity similarity engine
"""
import re
from autoreview.models import TrialRecord


def normalize_text(value):
    """Normalize text for matching: lowercase, strip non-alphanumeric, collapse whitespace."""
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(value):
    """Convert text to set of tokens (min 3 chars)."""
    return set(t for t in normalize_text(value).split() if len(t) >= 3)


def jaccard(set_a, set_b):
    """Jaccard similarity coefficient between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


# Trial acronym aliases — maps common acronyms to words that appear in CT.gov titles
# Pattern from: metasprint-cardio-universe/src/ontology/intervention-dictionary.js
TRIAL_ALIASES = {
    # SGLT2i
    "DAPA-HF": ["dapagliflozin", "heart failure", "reduced ejection"],
    "EMPEROR-Reduced": ["empagliflozin", "heart failure", "reduced ejection"],
    "EMPEROR-Preserved": ["empagliflozin", "heart failure", "preserved ejection"],
    "DELIVER": ["dapagliflozin", "heart failure", "preserved"],
    "SOLOIST-WHF": ["sotagliflozin", "heart failure", "worsening"],
    "EMPA-REG OUTCOME": ["empagliflozin", "cardiovascular outcome", "type 2 diabetes"],
    "CANVAS": ["canagliflozin", "cardiovascular", "assessment"],
    "DECLARE-TIMI 58": ["dapagliflozin", "cardiovascular", "thrombolysis"],
    "SCORED": ["sotagliflozin", "diabetes", "chronic kidney"],
    # Beta-blockers
    "MERIT-HF": ["metoprolol", "heart failure"],
    "CIBIS-II": ["bisoprolol", "heart failure", "cardiac insufficiency"],
    "COPERNICUS": ["carvedilol", "heart failure", "severe"],
    # ACEi/ARB/ARNI
    "CONSENSUS": ["enalapril", "severe heart failure", "cooperative"],
    "SOLVD-Treatment": ["enalapril", "left ventricular dysfunction"],
    "Val-HeFT": ["valsartan", "heart failure"],
    "CHARM-Alternative": ["candesartan", "heart failure"],
    "PARADIGM-HF": ["sacubitril", "valsartan", "heart failure"],
    # NOACs
    "RE-LY": ["dabigatran", "atrial fibrillation"],
    "ROCKET-AF": ["rivaroxaban", "atrial fibrillation"],
    "ARISTOTLE": ["apixaban", "atrial fibrillation"],
    "ENGAGE AF-TIMI 48": ["edoxaban", "atrial fibrillation"],
    # Lipids
    "4S": ["simvastatin", "scandinavian", "survival"],
    "WOSCOPS": ["pravastatin", "scotland", "coronary prevention"],
    "IMPROVE-IT": ["ezetimibe", "simvastatin", "acute coronary"],
    "FOURIER": ["evolocumab", "cardiovascular outcomes"],
    "ODYSSEY OUTCOMES": ["alirocumab", "acute coronary"],
    # Antiplatelets
    "PLATO": ["ticagrelor", "acute coronary", "platelet inhibition"],
    "PEGASUS-TIMI 54": ["ticagrelor", "myocardial infarction", "prevention"],
    "TRITON-TIMI 38": ["prasugrel", "acute coronary", "thrombolysis"],
    # MRAs
    "RALES": ["spironolactone", "heart failure"],
    "EMPHASIS-HF": ["eplerenone", "heart failure", "mild"],
    # GLP-1 RAs
    "LEADER": ["liraglutide", "cardiovascular", "diabetes"],
    "SUSTAIN-6": ["semaglutide", "cardiovascular", "diabetes"],
    "EXSCEL": ["exenatide", "cardiovascular", "diabetes"],
    "HARMONY": ["albiglutide", "cardiovascular", "diabetes"],
    "SELECT": ["semaglutide", "cardiovascular", "obesity"],
    # Interventional
    "ISCHEMIA": ["ischemia", "invasive", "conservative"],
    # Statins
    "JUPITER": ["rosuvastatin", "prevention", "jupiter"],
    "HOPE-3": ["rosuvastatin", "intermediate risk", "hope"],
}


def _score_trial_match(trial_title, kb_name, kb_aliases):
    """Score how well a CT.gov trial title matches a KB entry.

    Returns score 0.0-1.0 using multi-signal approach from
    MetaSprint Cardio Universe identity engine.
    """
    title_tokens = token_set(trial_title)
    if not title_tokens:
        return 0.0

    # Signal 1: Direct acronym in title (highest confidence)
    title_lower = normalize_text(trial_title)
    acronym_lower = normalize_text(kb_name)
    if acronym_lower and len(acronym_lower) >= 3 and acronym_lower in title_lower:
        return 0.95

    # Signal 2: Alias keyword matching — how many alias keywords appear in title?
    aliases = kb_aliases or []
    if aliases:
        alias_tokens = set()
        for alias in aliases:
            alias_tokens |= token_set(alias)
        if alias_tokens:
            # Fraction of alias tokens found in title
            found = len(alias_tokens & title_tokens)
            total = len(alias_tokens)
            alias_score = found / total if total > 0 else 0
            if alias_score >= 0.6:
                return 0.50 + alias_score * 0.40  # 0.74-0.90

    # Signal 3: Jaccard similarity on full title vs KB name
    name_tokens = token_set(kb_name)
    jacc = jaccard(title_tokens, name_tokens)
    if jacc >= 0.5:
        return 0.40 + jacc * 0.40

    return 0.0


def match_trial_to_kb(trial, cardio_kb):
    """Try to match a TrialRecord to a KB entry.

    Strategy (from MetaSprint identity engine):
    1. Exact NCT ID match (score 0.99)
    2. Fuzzy title match using Jaccard + aliases (score 0.50-0.95)
    3. Best match above threshold 0.60 wins

    Returns (kb_key, score) or (None, 0) if no match.
    """
    # 1. Exact NCT ID
    if trial.nct_id in cardio_kb:
        return trial.nct_id, 0.99

    # 2. Fuzzy title match against all KB entries
    best_key = None
    best_score = 0.0

    for kb_key, kb_entry in cardio_kb.items():
        kb_name = kb_entry["name"]
        aliases = TRIAL_ALIASES.get(kb_name, [])
        score = _score_trial_match(trial.title, kb_name, aliases)

        # Enrollment sanity check — if KB has enrollment data, check ratio
        if score > 0.5 and trial.enrollment > 0:
            kb_n = kb_entry.get("n_int", 0) + kb_entry.get("n_ctrl", 0)
            if kb_n > 0:
                ratio = max(trial.enrollment, kb_n) / max(min(trial.enrollment, kb_n), 1)
                if ratio > 5:  # More than 5x difference = probably wrong match
                    score *= 0.5

        if score > best_score:
            best_score = score
            best_key = kb_key

    threshold = 0.60
    if best_score >= threshold:
        return best_key, best_score

    return None, 0.0


def match_all_trials(trials, cardio_kb):
    """Match all trials to KB entries. Returns dict of trial_nct_id -> (kb_key, score).

    Prevents duplicate matches: each KB entry can only match one trial (best score wins).
    """
    # Score all candidates
    candidates = []
    for trial in trials:
        kb_key, score = match_trial_to_kb(trial, cardio_kb)
        if kb_key is not None:
            candidates.append((trial, kb_key, score))

    # Sort by score descending — best matches first
    candidates.sort(key=lambda x: -x[2])

    # Assign: each KB entry matched at most once (greedy)
    used_kb_keys = set()
    matches = {}
    for trial, kb_key, score in candidates:
        if kb_key not in used_kb_keys:
            matches[trial.nct_id] = (kb_key, score)
            used_kb_keys.add(kb_key)

    return matches
