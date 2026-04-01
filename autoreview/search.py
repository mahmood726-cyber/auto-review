"""Search ClinicalTrials.gov API v2 for relevant trials."""
import json
import urllib.request
import urllib.parse
from autoreview.models import TrialRecord

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


DRUG_CLASS_EXPANSIONS = {
    "sglt2 inhibitor": ["dapagliflozin", "empagliflozin", "canagliflozin",
                         "sotagliflozin", "ertugliflozin"],
    "gliflozin": ["dapagliflozin", "empagliflozin", "canagliflozin",
                   "sotagliflozin", "ertugliflozin"],
    "glp-1 receptor agonist": ["semaglutide", "liraglutide", "dulaglutide",
                                "exenatide", "tirzepatide"],
    "glp1": ["semaglutide", "liraglutide", "dulaglutide", "tirzepatide"],
    "pcsk9 inhibitor": ["evolocumab", "alirocumab", "inclisiran"],
    "statin": ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin"],
    "ace inhibitor": ["enalapril", "ramipril", "lisinopril", "perindopril"],
    "arb": ["losartan", "valsartan", "candesartan", "irbesartan"],
    "beta blocker": ["metoprolol", "bisoprolol", "carvedilol", "atenolol"],
}


def _expand_intervention(intervention):
    """Expand drug class name to individual drug names for CT.gov search."""
    intervention_lower = intervention.lower()
    for class_name, drugs in DRUG_CLASS_EXPANSIONS.items():
        if class_name in intervention_lower:
            return drugs
    return [intervention]


def search_ctgov(query, max_results=100):
    """Search CT.gov for trials matching the PICO query.

    Expands drug class names to individual drugs and searches with OR logic.
    Returns list of TrialRecord from structured registry data.
    """
    drug_names = _expand_intervention(query.intervention)

    # Search: population AND (drug1 OR drug2 OR ...)
    drug_expr = " OR ".join(drug_names)
    search_expr = f"{query.population} AND ({drug_expr})"

    params = {
        "query.term": search_expr,
        "filter.overallStatus": "COMPLETED,ACTIVE_NOT_RECRUITING,TERMINATED",
        "pageSize": str(min(max_results, 100)),
        "fields": (
            "NCTId,BriefTitle,OverallStatus,Phase,EnrollmentCount,"
            "StartDate,CompletionDate,LeadSponsorName,Condition,"
            "InterventionName,PrimaryOutcomeMeasure,ResultsFirstPostDate,"
            "StudyType"
        ),
    }

    url = f"{CTGOV_API}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"CT.gov API error: {e}")
        return []

    studies = data.get("studies", [])
    records = []

    for study in studies:
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsors = proto.get("sponsorCollaboratorsModule", {})
        conditions_mod = proto.get("conditionsModule", {})
        arms_mod = proto.get("armsInterventionsModule", {})
        outcomes_mod = proto.get("outcomesModule", {})

        nct_id = ident.get("nctId", "")
        title = ident.get("briefTitle", "")
        status = status_mod.get("overallStatus", "")
        phases = design.get("phases", [])
        phase = phases[0] if phases else ""
        enrollment_info = design.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count", 0) if isinstance(enrollment_info, dict) else 0
        start_info = status_mod.get("startDateStruct", {})
        start_date = start_info.get("date", "") if isinstance(start_info, dict) else ""
        comp_info = status_mod.get("completionDateStruct", {})
        completion_date = comp_info.get("date", "") if isinstance(comp_info, dict) else ""
        lead = sponsors.get("leadSponsor", {})
        sponsor = lead.get("name", "") if isinstance(lead, dict) else ""
        conditions = conditions_mod.get("conditions", [])
        interventions_raw = arms_mod.get("interventions", [])
        interventions = [iv.get("name", "") for iv in interventions_raw if isinstance(iv, dict)]
        primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
        primary_outcome = primary_outcomes[0].get("measure", "") if primary_outcomes else ""

        has_results = study.get("hasResults", False)

        # Filter: must be interventional
        study_type = design.get("studyType", proto.get("designModule", {}).get("studyType", ""))
        if isinstance(study_type, str) and "OBSERVATIONAL" in study_type.upper():
            continue

        records.append(TrialRecord(
            nct_id=nct_id,
            title=title,
            status=status,
            phase=phase,
            enrollment=enrollment if isinstance(enrollment, int) else 0,
            start_date=start_date,
            completion_date=completion_date,
            sponsor=sponsor,
            conditions=conditions if isinstance(conditions, list) else [],
            interventions=interventions,
            primary_outcome=primary_outcome,
            results_posted=has_results,
        ))

    return records
