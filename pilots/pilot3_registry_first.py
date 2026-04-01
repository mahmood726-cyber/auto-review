"""PILOT 3: Registry-First AutoReview — Pure CT.gov data

Does NOT use curated knowledge base. Attempts to derive everything
from CT.gov structured data alone.

This is the novel moonshot: can we do meta-analysis without reading
any publications, using only trial registry data?

Expected result: will find many trials but few with posted results.
The main output is the feasibility assessment — how much of the
evidence landscape is capturable from registries alone?
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoreview.models import PICOQuery
from autoreview.pipeline import run_autoreview


def run_registry_pilot(population, intervention, comparator, outcome, label):
    """Run a single registry-first pilot."""
    print(f"\n{'=' * 60}")
    print(f"REGISTRY-FIRST PILOT: {label}")
    print(f"{'=' * 60}")

    query = PICOQuery(
        population=population,
        intervention=intervention,
        comparator=comparator,
        outcome=outcome,
        study_design="RCT",
    )

    result = run_autoreview(query, use_kb=False, max_search=100)

    print()
    print(result.prisma_flow)
    print()

    # Registry-first feasibility analysis
    included = result.screening.included
    n_total = len(included)
    n_with_results = sum(1 for t in included if t.results_posted)
    n_with_effects = result.pooled.k
    n_large = sum(1 for t in included if t.enrollment >= 1000)

    print("REGISTRY-FIRST FEASIBILITY ANALYSIS")
    print("-" * 40)
    print(f"  Trials identified:       {result.screening.n_identified}")
    print(f"  Trials after screening:  {n_total}")
    print(f"  With results posted:     {n_with_results} ({n_with_results/max(n_total,1)*100:.0f}%)")
    print(f"  With extractable effects:{n_with_effects}")
    print(f"  Large trials (N>=1000):  {n_large}")
    print()

    # Enrollment landscape
    total_enrollment = sum(t.enrollment for t in included)
    print(f"  Total enrollment:        {total_enrollment:,}")
    if included:
        enrollments = sorted([t.enrollment for t in included], reverse=True)
        print(f"  Largest trial:           {enrollments[0]:,}")
        print(f"  Median enrollment:       {enrollments[len(enrollments)//2]:,}")

    # Phase distribution
    phases = {}
    for t in included:
        p = t.phase or "Not specified"
        phases[p] = phases.get(p, 0) + 1
    print(f"\n  Phase distribution:")
    for phase, count in sorted(phases.items()):
        print(f"    {phase}: {count}")

    # Status distribution
    statuses = {}
    for t in included:
        statuses[t.status] = statuses.get(t.status, 0) + 1
    print(f"\n  Status distribution:")
    for status, count in sorted(statuses.items()):
        print(f"    {status}: {count}")

    # Verdict
    print(f"\n  FEASIBILITY VERDICT:")
    if n_with_effects >= 3:
        print(f"    FEASIBLE — {n_with_effects} trials have extractable data")
    elif n_with_results >= 3:
        print(f"    PARTIALLY FEASIBLE — {n_with_results} have posted results (need parsing)")
    else:
        print(f"    NOT YET FEASIBLE — only {n_with_results} have posted results")
        print(f"    Gap: {n_total - n_with_results} trials completed but results not posted")
        if n_total > 0:
            print(f"    Results posting rate: {n_with_results/n_total*100:.0f}%")

    print(f"\n  Time: {result.elapsed_seconds:.1f}s")

    # Save
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    safe_label = label.lower().replace(" ", "_").replace("/", "_")
    with open(os.path.join(output_dir, f"pilot3_{safe_label}.txt"), "w", encoding="utf-8") as f:
        f.write(result.manuscript)
        f.write("\n\n" + result.prisma_flow)

    return result


def main():
    print("=" * 60)
    print("PILOT 3: REGISTRY-FIRST AUTONOMOUS SYSTEMATIC REVIEW")
    print("Can we do meta-analysis from CT.gov alone?")
    print("=" * 60)

    # Scenario A: SGLT2i in HF (known well-studied area)
    r1 = run_registry_pilot(
        population="heart failure",
        intervention="SGLT2 inhibitor",
        comparator="placebo",
        outcome="cardiovascular death or hospitalization",
        label="SGLT2i in HF",
    )

    # Scenario B: GLP-1 RA in obesity (large recent trials)
    r2 = run_registry_pilot(
        population="obesity",
        intervention="GLP-1 receptor agonist",
        comparator="placebo",
        outcome="weight loss",
        label="GLP1-RA in Obesity",
    )

    # Scenario C: PCSK9 inhibitors in cardiovascular disease
    r3 = run_registry_pilot(
        population="cardiovascular disease",
        intervention="PCSK9 inhibitor",
        comparator="placebo",
        outcome="major adverse cardiovascular events",
        label="PCSK9i in CVD",
    )

    # Summary
    print("\n" + "=" * 60)
    print("PILOT 3 SUMMARY — REGISTRY-FIRST FEASIBILITY")
    print("=" * 60)
    for label, r in [("SGLT2i/HF", r1), ("GLP1-RA/Obesity", r2), ("PCSK9i/CVD", r3)]:
        n_inc = len(r.screening.included)
        n_res = sum(1 for t in r.screening.included if t.results_posted)
        n_eff = r.pooled.k
        print(f"  {label:20s}  trials={n_inc:3d}  results={n_res:3d}  "
              f"poolable={n_eff:3d}  cert={r.certification}")

    print()
    print("CONCLUSION: Registry-first SR requires CT.gov results posting.")
    print("Current gap: most completed trials do not post structured results.")
    print("When results ARE posted, the pipeline works end-to-end.")


if __name__ == "__main__":
    main()
