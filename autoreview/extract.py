"""Extract effect sizes from trial records.

For Pilot 1 (cardiology): uses a curated knowledge base of published results.
For Pilot 3 (registry-first): derives from registry data when possible.
"""
import math
from autoreview.models import TrialRecord

# Curated cardiology knowledge base — published primary results
# These are the actual published effect sizes from landmark trials
CARDIO_KB = {
    # =========================================================================
    # SGLT2 inhibitors
    # =========================================================================
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
    "NCT01986881": {"name": "EMPA-REG OUTCOME", "measure": "HR", "effect": 0.86, "ci_lo": 0.74, "ci_hi": 0.99,
                     "events_int": 490, "events_ctrl": 282, "n_int": 4687, "n_ctrl": 2333},
    "NCT01730534": {"name": "CANVAS", "measure": "HR", "effect": 0.86, "ci_lo": 0.75, "ci_hi": 0.97,
                     "events_int": 585, "events_ctrl": 426, "n_int": 5795, "n_ctrl": 4347},
    "NCT01989754": {"name": "DECLARE-TIMI 58", "measure": "HR", "effect": 0.83, "ci_lo": 0.73, "ci_hi": 0.95,
                     "events_int": 417, "events_ctrl": 496, "n_int": 8582, "n_ctrl": 8578},
    "NCT03982381": {"name": "SCORED", "measure": "HR", "effect": 0.74, "ci_lo": 0.63, "ci_hi": 0.88,
                     "events_int": 243, "events_ctrl": 319, "n_int": 5292, "n_ctrl": 5292},

    # =========================================================================
    # Statins — primary prevention
    # =========================================================================
    "NCT00738725": {"name": "JUPITER", "measure": "HR", "effect": 0.56, "ci_lo": 0.46, "ci_hi": 0.69,
                     "events_int": 142, "events_ctrl": 251, "n_int": 8901, "n_ctrl": 8901},
    "NCT01738828": {"name": "HOPE-3", "measure": "HR", "effect": 0.76, "ci_lo": 0.64, "ci_hi": 0.91,
                     "events_int": 235, "events_ctrl": 304, "n_int": 6361, "n_ctrl": 6344},

    # =========================================================================
    # Beta-blockers in heart failure
    # Pre-registration-era trials — no NCT IDs available
    # =========================================================================
    "MERIT-HF": {"name": "MERIT-HF", "measure": "HR", "effect": 0.66, "ci_lo": 0.53, "ci_hi": 0.81,
                  "events_int": 145, "events_ctrl": 217, "n_int": 1990, "n_ctrl": 2001},
    "CIBIS-II": {"name": "CIBIS-II", "measure": "HR", "effect": 0.66, "ci_lo": 0.54, "ci_hi": 0.81,
                  "events_int": 156, "events_ctrl": 228, "n_int": 1327, "n_ctrl": 1320},
    "COPERNICUS": {"name": "COPERNICUS", "measure": "HR", "effect": 0.65, "ci_lo": 0.52, "ci_hi": 0.81,
                    "events_int": 130, "events_ctrl": 190, "n_int": 1156, "n_ctrl": 1133},

    # =========================================================================
    # ACE inhibitors / ARBs / ARNI in heart failure
    # CONSENSUS and SOLVD-Treatment are pre-registration-era (no NCT IDs)
    # =========================================================================
    "CONSENSUS": {"name": "CONSENSUS", "measure": "RR", "effect": 0.56, "ci_lo": 0.34, "ci_hi": 0.91,
                   "events_int": 50, "events_ctrl": 68, "n_int": 127, "n_ctrl": 126},
    "SOLVD-Treatment": {"name": "SOLVD-Treatment", "measure": "RR", "effect": 0.82, "ci_lo": 0.70, "ci_hi": 0.97,
                         "events_int": 452, "events_ctrl": 510, "n_int": 1285, "n_ctrl": 1284},
    "NCT00381511": {"name": "Val-HeFT", "measure": "HR", "effect": 0.87, "ci_lo": 0.77, "ci_hi": 0.97,
                     "events_int": 723, "events_ctrl": 801, "n_int": 2511, "n_ctrl": 2499},
    "CHARM-Alternative": {"name": "CHARM-Alternative", "measure": "HR", "effect": 0.77, "ci_lo": 0.67, "ci_hi": 0.89,
                           "events_int": 334, "events_ctrl": 406, "n_int": 1013, "n_ctrl": 1015},
    "NCT01035255": {"name": "PARADIGM-HF", "measure": "HR", "effect": 0.80, "ci_lo": 0.73, "ci_hi": 0.87,
                     "events_int": 711, "events_ctrl": 835, "n_int": 4187, "n_ctrl": 4212},

    # =========================================================================
    # Anticoagulants in atrial fibrillation (NOACs vs warfarin)
    # =========================================================================
    "NCT00262600": {"name": "RE-LY", "measure": "RR", "effect": 0.91, "ci_lo": 0.74, "ci_hi": 1.11,
                     "events_int": 134, "events_ctrl": 199, "n_int": 6076, "n_ctrl": 6022},
    "NCT00412984": {"name": "ROCKET-AF", "measure": "HR", "effect": 0.88, "ci_lo": 0.75, "ci_hi": 1.03,
                     "events_int": 188, "events_ctrl": 241, "n_int": 7131, "n_ctrl": 7133},
    "NCT00496769": {"name": "ARISTOTLE", "measure": "HR", "effect": 0.79, "ci_lo": 0.66, "ci_hi": 0.95,
                     "events_int": 212, "events_ctrl": 265, "n_int": 9120, "n_ctrl": 9081},
    "NCT00781391": {"name": "ENGAGE AF-TIMI 48", "measure": "HR", "effect": 0.79, "ci_lo": 0.63, "ci_hi": 0.99,
                     "events_int": 296, "events_ctrl": 337, "n_int": 7035, "n_ctrl": 7036},

    # =========================================================================
    # Lipid-lowering therapies
    # 4S and WOSCOPS are pre-registration-era (no NCT IDs)
    # =========================================================================
    "4S": {"name": "4S", "measure": "RR", "effect": 0.70, "ci_lo": 0.58, "ci_hi": 0.85,
            "events_int": 182, "events_ctrl": 256, "n_int": 2221, "n_ctrl": 2223},
    "WOSCOPS": {"name": "WOSCOPS", "measure": "RR", "effect": 0.69, "ci_lo": 0.52, "ci_hi": 0.93,
                 "events_int": 50, "events_ctrl": 73, "n_int": 3302, "n_ctrl": 3293},
    "NCT00153062": {"name": "IMPROVE-IT", "measure": "HR", "effect": 0.94, "ci_lo": 0.89, "ci_hi": 0.99,
                     "events_int": 2572, "events_ctrl": 2742, "n_int": 9067, "n_ctrl": 9077},
    "NCT01764633": {"name": "FOURIER", "measure": "HR", "effect": 0.85, "ci_lo": 0.79, "ci_hi": 0.92,
                     "events_int": 1344, "events_ctrl": 1563, "n_int": 13784, "n_ctrl": 13780},
    "NCT01663402": {"name": "ODYSSEY OUTCOMES", "measure": "HR", "effect": 0.85, "ci_lo": 0.78, "ci_hi": 0.93,
                     "events_int": 903, "events_ctrl": 1052, "n_int": 9462, "n_ctrl": 9462},

    # =========================================================================
    # Antiplatelet therapies
    # =========================================================================
    "NCT00496938": {"name": "PLATO", "measure": "HR", "effect": 0.84, "ci_lo": 0.77, "ci_hi": 0.92,
                     "events_int": 864, "events_ctrl": 1014, "n_int": 9333, "n_ctrl": 9291},
    "NCT01767507": {"name": "PEGASUS-TIMI 54", "measure": "HR", "effect": 0.85, "ci_lo": 0.75, "ci_hi": 0.96,
                     "events_int": 487, "events_ctrl": 578, "n_int": 7050, "n_ctrl": 7067},
    "NCT00050817": {"name": "TRITON-TIMI 38", "measure": "HR", "effect": 0.81, "ci_lo": 0.73, "ci_hi": 0.90,
                     "events_int": 643, "events_ctrl": 781, "n_int": 6813, "n_ctrl": 6795},

    # =========================================================================
    # Mineralocorticoid receptor antagonists in heart failure
    # RALES is a pre-registration-era trial (no NCT ID)
    # =========================================================================
    "RALES": {"name": "RALES", "measure": "RR", "effect": 0.70, "ci_lo": 0.60, "ci_hi": 0.82,
               "events_int": 284, "events_ctrl": 386, "n_int": 822, "n_ctrl": 841},
    "NCT00232544": {"name": "EMPHASIS-HF", "measure": "HR", "effect": 0.63, "ci_lo": 0.54, "ci_hi": 0.74,
                     "events_int": 249, "events_ctrl": 356, "n_int": 1364, "n_ctrl": 1373},

    # =========================================================================
    # GLP-1 receptor agonists — CV outcomes
    # =========================================================================
    "NCT01144338": {"name": "LEADER", "measure": "HR", "effect": 0.87, "ci_lo": 0.78, "ci_hi": 0.97,
                     "events_int": 608, "events_ctrl": 694, "n_int": 4668, "n_ctrl": 4672},
    "NCT01720446": {"name": "SUSTAIN-6", "measure": "HR", "effect": 0.74, "ci_lo": 0.58, "ci_hi": 0.95,
                     "events_int": 108, "events_ctrl": 146, "n_int": 1648, "n_ctrl": 1649},
    "NCT01394952": {"name": "EXSCEL", "measure": "HR", "effect": 0.91, "ci_lo": 0.83, "ci_hi": 1.00,
                     "events_int": 839, "events_ctrl": 905, "n_int": 7356, "n_ctrl": 7396},
    "NCT01147250": {"name": "HARMONY", "measure": "HR", "effect": 0.78, "ci_lo": 0.68, "ci_hi": 0.90,
                     "events_int": 338, "events_ctrl": 428, "n_int": 4731, "n_ctrl": 4732},
    "NCT03985384": {"name": "SELECT", "measure": "HR", "effect": 0.80, "ci_lo": 0.72, "ci_hi": 0.90,
                     "events_int": 569, "events_ctrl": 701, "n_int": 8803, "n_ctrl": 8801},

    # =========================================================================
    # Interventional cardiology
    # =========================================================================
    "NCT01561651": {"name": "ISCHEMIA", "measure": "HR", "effect": 1.00, "ci_lo": 0.93, "ci_hi": 1.07,
                     "events_int": 318, "events_ctrl": 352, "n_int": 2588, "n_ctrl": 2591},
}


def extract_from_kb(trial, fuzzy_matches=None):
    """Try to extract effect size from curated knowledge base.

    First tries exact NCT ID match, then falls back to fuzzy title match
    using the MetaSprint Cardio Universe identity engine pattern.
    """
    entry = CARDIO_KB.get(trial.nct_id)
    if entry is None and fuzzy_matches and trial.nct_id in fuzzy_matches:
        kb_key, score = fuzzy_matches[trial.nct_id]
        entry = CARDIO_KB.get(kb_key)
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

    Uses exact NCT ID match first, then fuzzy title matching (Jaccard + aliases)
    ported from MetaSprint Cardio Universe identity engine.

    Returns (extracted, unextracted) — trials with/without effect data.
    """
    # Build fuzzy matches for all trials at once (prevents duplicate KB assignments)
    fuzzy_matches = {}
    if use_kb:
        from autoreview.matcher import match_all_trials
        fuzzy_matches = match_all_trials(trials, CARDIO_KB)

    extracted = []
    unextracted = []

    for trial in trials:
        if use_kb:
            trial = extract_from_kb(trial, fuzzy_matches=fuzzy_matches)

        if trial.effect_size is not None and trial.se is not None and trial.se > 0:
            extracted.append(trial)
        else:
            trial = extract_from_registry(trial)
            if trial.effect_size is not None and trial.se is not None and trial.se > 0:
                extracted.append(trial)
            else:
                unextracted.append(trial)

    return extracted, unextracted
