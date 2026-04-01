"""Auto-generate a structured mini-manuscript from review results."""
import math
from autoreview.models import AutoReviewResult


def generate_prisma_flow(result):
    """Generate PRISMA flow diagram as text."""
    s = result.screening
    lines = [
        "PRISMA Flow Diagram",
        "=" * 40,
        f"Records identified (CT.gov):  {s.n_identified}",
        f"Records screened:             {s.n_screened}",
        f"Records excluded:             {len(s.excluded)}",
    ]

    # Exclusion reasons
    reasons = {}
    for _, reason in s.excluded:
        reasons[reason] = reasons.get(reason, 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"  - {reason}: {count}")

    lines.extend([
        f"Studies eligible:             {s.n_eligible}",
        f"Studies with effect data:     {result.pooled.k}",
        f"Studies included in MA:       {result.pooled.k}",
    ])
    return "\n".join(lines)


def generate_manuscript(result):
    """Generate a structured mini-manuscript."""
    q = result.query
    p = result.pooled
    g = result.grade
    s = result.screening

    # Convert log effect to original scale for reporting
    if "log" in p.measure.lower():
        orig_measure = p.measure.replace("log", "").upper()
        effect_orig = math.exp(p.theta)
        ci_lo_orig = math.exp(p.ci_lo)
        ci_hi_orig = math.exp(p.ci_hi)
        effect_str = f"{orig_measure} {effect_orig:.2f} (95% CI {ci_lo_orig:.2f} to {ci_hi_orig:.2f})"
    else:
        effect_str = f"{p.measure} {p.theta:.2f} (95% CI {p.ci_lo:.2f} to {p.ci_hi:.2f})"

    sig_str = "statistically significant" if p.significant else "not statistically significant"
    direction_str = {
        "favors_intervention": f"favoring {q.intervention}",
        "favors_control": f"favoring {q.comparator}",
        "no_difference": "showing no difference",
    }.get(p.direction, "")

    sections = []

    # Title
    title = (f"Autonomous Systematic Review: {q.intervention} vs {q.comparator} "
             f"for {q.outcome} in {q.population}")
    sections.append(f"TITLE: {title}")
    sections.append("")

    # Abstract
    sections.append("ABSTRACT")
    sections.append("-" * 40)
    sections.append(
        f"Background: This autonomous systematic review evaluated the effect of "
        f"{q.intervention} compared with {q.comparator} on {q.outcome} in {q.population}."
    )
    sections.append(
        f"Methods: ClinicalTrials.gov was searched systematically. {s.n_identified} records "
        f"were identified, {s.n_screened} screened, and {p.k} RCTs included in "
        f"DerSimonian-Laird random-effects meta-analysis."
    )
    sections.append(
        f"Results: The pooled {effect_str}, p={p.p_value:.4f}, was {sig_str} "
        f"{direction_str}. Heterogeneity was {'substantial' if p.i2 > 50 else 'low'} "
        f"(I2={p.i2:.0f}%, tau2={p.tau2:.4f}). "
        f"GRADE certainty: {g.overall}."
    )
    sections.append(
        f"Conclusion: {'Strong' if g.overall in ('High', 'Moderate') else 'Limited'} "
        f"evidence {'supports' if p.significant else 'does not support'} "
        f"{q.intervention} for {q.outcome} in {q.population}. "
        f"{g.explanation}."
    )
    sections.append("")

    # Methods
    sections.append("METHODS")
    sections.append("-" * 40)
    sections.append(f"Search: ClinicalTrials.gov API v2 (automated, {result.elapsed_seconds:.1f}s)")
    sections.append(f"Population: {q.population}")
    sections.append(f"Intervention: {q.intervention}")
    sections.append(f"Comparator: {q.comparator}")
    sections.append(f"Outcome: {q.outcome}")
    sections.append(f"Study design: {q.study_design}")
    sections.append(f"Analysis: DerSimonian-Laird random-effects, log scale")
    sections.append(f"Software: AutoReview v0.1.0 (autonomous pipeline)")
    sections.append("")

    # Results
    sections.append("RESULTS")
    sections.append("-" * 40)
    sections.append(f"Trials included: {p.k}")
    total_n = sum((t.n_intervention or 0) + (t.n_control or 0) for t in s.included[:p.k])
    sections.append(f"Total participants: {total_n}")
    sections.append(f"Pooled effect: {effect_str}")
    sections.append(f"p-value: {p.p_value:.6f}")
    sections.append(f"Heterogeneity: I2={p.i2:.0f}%, tau2={p.tau2:.4f}")
    sections.append("")

    # Included trials
    sections.append("INCLUDED TRIALS")
    sections.append("-" * 40)
    for t in s.included:
        if t.effect_size is not None:
            orig_effect = math.exp(t.effect_size) if "log" in (t.measure or "").lower() else t.effect_size
            sections.append(
                f"  {t.nct_id} | {t.title[:50]} | N={t.enrollment} | "
                f"Effect={orig_effect:.2f}"
            )

    sections.append("")

    # GRADE
    sections.append("GRADE ASSESSMENT")
    sections.append("-" * 40)
    sections.append(f"Risk of bias:      {g.risk_of_bias}")
    sections.append(f"Inconsistency:     {g.inconsistency}")
    sections.append(f"Indirectness:      {g.indirectness}")
    sections.append(f"Imprecision:       {g.imprecision}")
    sections.append(f"Publication bias:  {g.publication_bias}")
    sections.append(f"Overall certainty: {g.overall}")
    sections.append(f"Explanation: {g.explanation}")
    sections.append("")

    # Certification
    sections.append("CERTIFICATION")
    sections.append("-" * 40)
    sections.append(f"Pipeline: AutoReview v0.1.0")
    sections.append(f"Mode: {'Cardiology KB' if any(t.nct_id in _kb_ids() for t in s.included) else 'Registry-first'}")
    sections.append(f"Status: {result.certification}")
    sections.append(f"Elapsed: {result.elapsed_seconds:.1f}s")

    return "\n".join(sections)


def _kb_ids():
    from autoreview.extract import CARDIO_KB
    return set(CARDIO_KB.keys())
