"""Automated GRADE assessment from pooled results."""
import math
from autoreview.models import GRADEAssessment


def assess_grade(pooled, trials, screening):
    """Automated GRADE certainty assessment.

    Starts at High (all RCTs) and downgrades based on 5 domains.
    """
    downgrades = 0
    explanations = []

    # 1. Risk of Bias — all RCTs, assume low unless small/industry-only
    rob = "not serious"
    industry_count = sum(1 for t in trials if _is_industry(t.sponsor))
    if industry_count == len(trials) and len(trials) > 0:
        rob = "serious"
        downgrades += 1
        explanations.append("All trials industry-sponsored (potential bias)")
    elif any(t.enrollment < 200 for t in trials):
        rob = "not serious"
        explanations.append("Some small trials but overall adequate")

    # 2. Inconsistency — based on I²
    inconsistency = "not serious"
    if pooled.i2 > 75:
        inconsistency = "serious"
        downgrades += 1
        explanations.append(f"Substantial heterogeneity (I2={pooled.i2:.0f}%)")
    elif pooled.i2 > 50:
        inconsistency = "not serious"
        explanations.append(f"Moderate heterogeneity (I2={pooled.i2:.0f}%)")

    # 3. Indirectness — check if outcome matches query
    indirectness = "not serious"
    if pooled.k < 3:
        indirectness = "serious"
        downgrades += 1
        explanations.append("Limited direct evidence (k<3)")

    # 4. Imprecision — based on CI width and OIS
    imprecision = "not serious"
    total_n = sum((t.n_intervention or 0) + (t.n_control or 0) for t in trials)
    ci_width = pooled.ci_hi - pooled.ci_lo

    if not pooled.significant:
        imprecision = "serious"
        downgrades += 1
        explanations.append(f"CI crosses null (p={pooled.p_value:.4f})")
    elif ci_width > 0.5:
        imprecision = "serious"
        downgrades += 1
        explanations.append(f"Wide confidence interval (width={ci_width:.2f})")
    elif total_n < 2000:
        imprecision = "not serious"
        explanations.append(f"Total N={total_n} (borderline)")

    # 5. Publication bias — assess if enough studies
    pub_bias = "undetected"
    if pooled.k < 10:
        pub_bias = "undetected"
        explanations.append("Too few studies to assess publication bias")
    # Could add Egger's test here with enough studies

    # Overall certainty
    levels = ["High", "Moderate", "Low", "Very Low"]
    idx = min(downgrades, 3)
    overall = levels[idx]

    if not explanations:
        explanations.append("All RCTs with consistent results and adequate precision")

    return GRADEAssessment(
        risk_of_bias=rob,
        inconsistency=inconsistency,
        indirectness=indirectness,
        imprecision=imprecision,
        publication_bias=pub_bias,
        overall=overall,
        explanation="; ".join(explanations),
    )


def _is_industry(sponsor):
    """Heuristic: is sponsor a pharmaceutical company?"""
    pharma_keywords = [
        "pharma", "lilly", "pfizer", "novartis", "astrazeneca", "merck",
        "sanofi", "roche", "bayer", "boehringer", "janssen", "abbvie",
        "glaxo", "gsk", "bristol-myers", "amgen", "gilead", "biogen",
        "takeda", "astellas", "daiichi", "eisai",
    ]
    sponsor_lower = sponsor.lower()
    return any(kw in sponsor_lower for kw in pharma_keywords)
