"""Meta-analysis pooling — DerSimonian-Laird random effects."""
import math
from autoreview.models import PooledResult


def pool_dl(trials):
    """DerSimonian-Laird random-effects meta-analysis.

    Expects trials with effect_size (log scale) and se.
    Returns PooledResult.
    """
    k = len(trials)
    if k == 0:
        return PooledResult(k=0)

    # SE floor guards against division-by-zero from a zero/None standard error
    # (e.g. a trial with effect data but no usable variance). The pipeline
    # already filters se>0 before pooling, but pool_dl is also a public entry
    # point and must not raise on a degenerate input.
    SE_FLOOR = 1e-6
    yi = [t.effect_size for t in trials]
    vi = [max(t.se or 0.0, SE_FLOOR) ** 2 for t in trials]

    # Fixed-effect estimate
    w_fe = [1.0 / v for v in vi]
    sum_w = sum(w_fe)
    theta_fe = sum(w * y for w, y in zip(w_fe, yi)) / sum_w

    # Cochran's Q
    q = sum(w * (y - theta_fe) ** 2 for w, y in zip(w_fe, yi))

    # DL tau-squared
    c = sum_w - sum(w ** 2 for w in w_fe) / sum_w
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 and k > 1 else 0.0

    # Random-effects weights
    w_re = [1.0 / (v + tau2) for v in vi]
    sum_w_re = sum(w_re)
    theta_re = sum(w * y for w, y in zip(w_re, yi)) / sum_w_re
    se_re = 1.0 / math.sqrt(sum_w_re)

    # CI
    ci_lo = theta_re - 1.96 * se_re
    ci_hi = theta_re + 1.96 * se_re

    # p-value (two-sided z-test)
    z = abs(theta_re / se_re) if se_re > 0 else 0
    # Approximate p from z using normal CDF
    p_value = 2 * _normal_sf(z)

    # I-squared
    i2 = max(0.0, (q - (k - 1)) / q * 100) if q > 0 and k > 1 else 0.0

    # Direction
    if theta_re < 0:
        direction = "favors_intervention"
    elif theta_re > 0:
        direction = "favors_control"
    else:
        direction = "no_difference"

    measure = trials[0].measure if trials else ""

    return PooledResult(
        theta=round(theta_re, 4),
        se=round(se_re, 4),
        ci_lo=round(ci_lo, 4),
        ci_hi=round(ci_hi, 4),
        p_value=round(p_value, 6),
        tau2=round(tau2, 4),
        i2=round(i2, 1),
        k=k,
        measure=measure,
        method="DL",
        significant=p_value < 0.05,
        direction=direction,
    )


def _normal_sf(z):
    """Survival function of standard normal (1 - CDF) via Abramowitz & Stegun."""
    if z < 0:
        return 1.0 - _normal_sf(-z)
    t = 1.0 / (1.0 + 0.2316419 * z)
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
                t * (-1.821255978 + t * 1.330274429))))
    return poly * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def build_forest_data(trials, pooled):
    """Build forest plot data structure."""
    rows = []
    for t in trials:
        rows.append({
            "label": t.nct_id,
            "title": t.title[:60],
            "yi": round(t.effect_size, 4),
            "ci_lo": round(t.effect_size - 1.96 * t.se, 4),
            "ci_hi": round(t.effect_size + 1.96 * t.se, 4),
            "weight": round(1.0 / (t.se ** 2 + pooled.tau2), 2) if pooled.tau2 >= 0 else 0,
            "n": (t.n_intervention or 0) + (t.n_control or 0),
        })
    # Summary
    rows.append({
        "label": "Summary",
        "title": f"RE Model (k={pooled.k})",
        "yi": pooled.theta,
        "ci_lo": pooled.ci_lo,
        "ci_hi": pooled.ci_hi,
        "weight": None,
        "n": sum(r["n"] for r in rows),
    })
    return rows
