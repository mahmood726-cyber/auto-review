"""PILOT 1: Cardiology-focused AutoReview — SGLT2i in Heart Failure

Uses curated cardiology knowledge base for effect extraction.
Searches CT.gov, screens, extracts from KB, pools, grades, generates manuscript.

Expected result: should reproduce the known SGLT2i HF meta-analysis
(HR ~0.74-0.79, significant, GRADE High/Moderate).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoreview.models import PICOQuery
from autoreview.pipeline import run_autoreview


def main():
    print("=" * 60)
    print("PILOT 1: SGLT2i in Heart Failure (Cardiology KB)")
    print("=" * 60)
    print()

    query = PICOQuery(
        population="heart failure",
        intervention="SGLT2 inhibitor",
        comparator="placebo",
        outcome="cardiovascular death or heart failure hospitalization",
        study_design="RCT",
    )

    result = run_autoreview(query, use_kb=True, max_search=100)

    # Output
    print()
    print(result.prisma_flow)
    print()
    print(result.manuscript)

    # Save outputs
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "pilot1_manuscript.txt"), "w", encoding="utf-8") as f:
        f.write(result.manuscript)

    with open(os.path.join(output_dir, "pilot1_prisma.txt"), "w", encoding="utf-8") as f:
        f.write(result.prisma_flow)

    import json
    with open(os.path.join(output_dir, "pilot1_forest.json"), "w", encoding="utf-8") as f:
        json.dump(result.forest_data, f, indent=2)

    print()
    print("=" * 60)
    print("PILOT 1 VERDICT")
    print("=" * 60)
    print(f"  Question:      {query.question}")
    print(f"  Trials found:  {result.screening.n_identified}")
    print(f"  Trials pooled: {result.pooled.k}")

    import math
    if result.pooled.k > 0:
        hr = math.exp(result.pooled.theta)
        ci_lo = math.exp(result.pooled.ci_lo)
        ci_hi = math.exp(result.pooled.ci_hi)
        print(f"  Pooled HR:     {hr:.2f} ({ci_lo:.2f} to {ci_hi:.2f})")
        print(f"  p-value:       {result.pooled.p_value:.6f}")
        print(f"  I-squared:     {result.pooled.i2:.0f}%")
        print(f"  GRADE:         {result.grade.overall}")
        print(f"  Significant:   {'YES' if result.pooled.significant else 'NO'}")

        # Validate against known result
        known_hr = 0.77  # approximate from published MA
        deviation = abs(hr - known_hr) / known_hr * 100
        print(f"  Known HR:      ~{known_hr}")
        print(f"  Deviation:     {deviation:.1f}%")
        if deviation < 10:
            print(f"  VALIDATION:    PASS (within 10% of published)")
        else:
            print(f"  VALIDATION:    CHECK (>{deviation:.0f}% from published)")
    else:
        print("  NO TRIALS WITH EFFECT DATA — KB match failed")

    print(f"  Certification: {result.certification}")
    print(f"  Time:          {result.elapsed_seconds:.1f}s")
    print(f"  Output saved:  output/pilot1_*.txt")
    print()


if __name__ == "__main__":
    main()
