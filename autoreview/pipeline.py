"""AutoReview pipeline — question to manuscript in one call."""
import time
import hashlib
import json
from autoreview.models import PICOQuery, AutoReviewResult
from autoreview.search import search_ctgov
from autoreview.screen import screen_trials
from autoreview.extract import extract_effects
from autoreview.pool import pool_dl, build_forest_data
from autoreview.grade import assess_grade
from autoreview.manuscript import generate_manuscript, generate_prisma_flow


def run_autoreview(query, use_kb=True, max_search=100):
    """End-to-end autonomous systematic review.

    query: PICOQuery
    use_kb: if True, use curated cardiology knowledge base for extraction
    max_search: max CT.gov results to retrieve

    Returns AutoReviewResult with full manuscript, PRISMA flow, forest data.
    """
    t0 = time.time()

    # Phase 1: SEARCH
    print(f"[AutoReview] Searching CT.gov for: {query.question}")
    records = search_ctgov(query, max_results=max_search)
    print(f"[AutoReview] Found {len(records)} records")

    # Phase 2: SCREEN
    screening = screen_trials(records, query)
    print(f"[AutoReview] Screened: {screening.n_included} included, "
          f"{len(screening.excluded)} excluded")

    # Phase 3: EXTRACT
    extracted, unextracted = extract_effects(screening.included, use_kb=use_kb)
    print(f"[AutoReview] Extracted effects: {len(extracted)} with data, "
          f"{len(unextracted)} without")

    # Phase 4: POOL
    pooled = pool_dl(extracted)
    print(f"[AutoReview] Pooled: k={pooled.k}, theta={pooled.theta:.4f}, "
          f"p={pooled.p_value:.6f}, I2={pooled.i2:.0f}%")

    # Phase 5: GRADE
    grade = assess_grade(pooled, extracted, screening)
    print(f"[AutoReview] GRADE: {grade.overall}")

    # Phase 6: ASSEMBLE
    elapsed = time.time() - t0

    # Certification
    input_data = {
        "query": query.question,
        "k": pooled.k,
        "theta": pooled.theta,
        "n_searched": len(records),
    }
    input_hash = hashlib.sha256(
        json.dumps(input_data, sort_keys=True).encode()
    ).hexdigest()[:16]

    if pooled.k == 0:
        cert = "REJECT"
    elif pooled.k < 3:
        cert = "WARN"
    else:
        cert = "PASS"

    result = AutoReviewResult(
        query=query,
        screening=screening,
        pooled=pooled,
        grade=grade,
        forest_data=build_forest_data(extracted, pooled),
        elapsed_seconds=elapsed,
        certification=cert,
    )

    result.prisma_flow = generate_prisma_flow(result)
    result.manuscript = generate_manuscript(result)

    print(f"[AutoReview] Complete in {elapsed:.1f}s — {cert}")
    return result
