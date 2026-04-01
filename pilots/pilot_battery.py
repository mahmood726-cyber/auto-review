"""Run 10 cardiology AutoReview pilots and validate against published MAs."""
import sys
import os
import math
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoreview.models import PICOQuery
from autoreview.pipeline import run_autoreview

SCENARIOS = [
    {
        "label": "SGLT2i in HF (all)",
        "query": PICOQuery("heart failure", "SGLT2 inhibitor", "placebo",
                           "cardiovascular death or heart failure hospitalization"),
        "known_hr": 0.77,
        "known_source": "Vaduganathan 2022 pooled",
    },
    {
        "label": "Beta-blockers in HFrEF",
        "query": PICOQuery("heart failure", "beta blocker", "placebo",
                           "all-cause mortality"),
        "known_hr": 0.66,
        "known_source": "Brophy 2001 MA",
    },
    {
        "label": "ACEi/ARB in HF",
        "query": PICOQuery("heart failure", "ACE inhibitor", "placebo",
                           "mortality"),
        "known_hr": 0.77,
        "known_source": "Flather 2000 MA",
    },
    {
        "label": "NOACs vs warfarin in AF",
        "query": PICOQuery("atrial fibrillation", "anticoagulant", "warfarin",
                           "stroke or systemic embolism"),
        "known_hr": 0.81,
        "known_source": "Ruff 2014 MA",
    },
    {
        "label": "Statins CV prevention",
        "query": PICOQuery("cardiovascular disease", "statin", "placebo",
                           "major adverse cardiovascular events"),
        "known_hr": 0.75,
        "known_source": "CTT 2010",
    },
    {
        "label": "PCSK9i in CVD",
        "query": PICOQuery("cardiovascular disease", "PCSK9 inhibitor", "placebo",
                           "major adverse cardiovascular events"),
        "known_hr": 0.85,
        "known_source": "FOURIER + ODYSSEY",
    },
    {
        "label": "Antiplatelets in ACS",
        "query": PICOQuery("acute coronary syndrome", "antiplatelet", "clopidogrel",
                           "major adverse cardiovascular events"),
        "known_hr": 0.83,
        "known_source": "PLATO/TRITON pooled",
    },
    {
        "label": "MRA in HF",
        "query": PICOQuery("heart failure", "mineralocorticoid", "placebo",
                           "all-cause mortality"),
        "known_hr": 0.67,
        "known_source": "RALES/EMPHASIS pooled",
    },
    {
        "label": "GLP-1 RA CV outcomes",
        "query": PICOQuery("type 2 diabetes cardiovascular", "GLP-1 receptor agonist", "placebo",
                           "major adverse cardiovascular events"),
        "known_hr": 0.88,
        "known_source": "Sattar 2021 MA",
    },
    {
        "label": "ARNI vs ACEi in HF",
        "query": PICOQuery("heart failure", "ARNI", "enalapril",
                           "cardiovascular death or heart failure hospitalization"),
        "known_hr": 0.80,
        "known_source": "PARADIGM-HF",
    },
]


def main():
    print("=" * 80)
    print("AUTOREVIEW PILOT BATTERY — 10 Cardiology Questions")
    print("=" * 80)

    results = []
    for i, scenario in enumerate(SCENARIOS, 1):
        label = scenario["label"]
        query = scenario["query"]
        known_hr = scenario["known_hr"]
        known_source = scenario["known_source"]

        print(f"\n{'-' * 80}")
        print(f"[{i}/10] {label}")
        print(f"  Q: {query.question}")
        print(f"  Known: HR ~{known_hr} ({known_source})")
        print(f"{'-' * 80}")

        try:
            result = run_autoreview(query, use_kb=True, max_search=100)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "label": label, "k": 0, "hr": None, "known_hr": known_hr,
                "deviation": None, "grade": "N/A", "verdict": "ERROR",
                "time": 0,
            })
            continue

        k = result.pooled.k
        if k > 0 and result.pooled.theta != 0:
            hr = math.exp(result.pooled.theta)
            ci_lo = math.exp(result.pooled.ci_lo)
            ci_hi = math.exp(result.pooled.ci_hi)
            deviation = abs(hr - known_hr) / known_hr * 100

            if deviation < 10:
                verdict = "PASS"
            elif deviation < 20:
                verdict = "CLOSE"
            else:
                verdict = "CHECK"

            print(f"  Result: HR {hr:.2f} ({ci_lo:.2f}-{ci_hi:.2f}), k={k}")
            print(f"  I2={result.pooled.i2:.0f}%, GRADE={result.grade.overall}")
            print(f"  Deviation: {deviation:.1f}% from known — {verdict}")
        else:
            hr = None
            deviation = None
            verdict = "NO DATA"
            print(f"  Result: No poolable trials (k=0)")

        results.append({
            "label": label,
            "k": k,
            "hr": round(hr, 3) if hr else None,
            "ci_lo": round(ci_lo, 3) if hr else None,
            "ci_hi": round(ci_hi, 3) if hr else None,
            "known_hr": known_hr,
            "deviation": round(deviation, 1) if deviation else None,
            "grade": result.grade.overall,
            "verdict": verdict,
            "time": round(result.elapsed_seconds, 1),
            "significant": result.pooled.significant if k > 0 else None,
            "n_searched": result.screening.n_identified,
        })

    # Summary table
    print("\n" + "=" * 80)
    print("PILOT BATTERY RESULTS")
    print("=" * 80)
    print(f"{'Scenario':<30s} {'k':>3s} {'HR':>6s} {'Known':>6s} {'Dev%':>6s} {'GRADE':>8s} {'Verdict':>8s} {'Time':>5s}")
    print("-" * 80)

    pass_count = 0
    close_count = 0
    check_count = 0
    nodata_count = 0

    for r in results:
        hr_str = f"{r['hr']:.2f}" if r['hr'] else "—"
        dev_str = f"{r['deviation']:.0f}%" if r['deviation'] is not None else "—"
        print(f"{r['label']:<30s} {r['k']:>3d} {hr_str:>6s} {r['known_hr']:>6.2f} "
              f"{dev_str:>6s} {r['grade']:>8s} {r['verdict']:>8s} {r['time']:>4.1f}s")

        if r['verdict'] == 'PASS':
            pass_count += 1
        elif r['verdict'] == 'CLOSE':
            close_count += 1
        elif r['verdict'] == 'CHECK':
            check_count += 1
        else:
            nodata_count += 1

    print("-" * 80)
    print(f"PASS (<10% deviation): {pass_count}/10")
    print(f"CLOSE (10-20%):        {close_count}/10")
    print(f"CHECK (>20%):          {check_count}/10")
    print(f"NO DATA:               {nodata_count}/10")
    accuracy = (pass_count + close_count) / max(pass_count + close_count + check_count, 1) * 100
    print(f"Accuracy (PASS+CLOSE): {accuracy:.0f}% of scenarios with data")

    # Save results
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "pilot_battery_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to output/pilot_battery_results.json")


if __name__ == "__main__":
    main()
