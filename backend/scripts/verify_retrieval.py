#!/usr/bin/env python3
# python scripts/verify_retrieval.py --video-id 1

import argparse
import json
import sys
import time

# edit these to match whatever lecture we want to eval
GOLDEN_QUERIES: list[str] = []


def run_query(service, video_id, query, top_k=5):
    start = time.monotonic()
    results = service.search(video_id, query, top_k=top_k)
    elapsed = time.monotonic() - start
    return results, elapsed


def main():
    parser = argparse.ArgumentParser(description="Verify retrieval pipeline on a processed lecture")
    parser.add_argument("--video-id", type=int, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--runs", type=int, default=3, help="repeat each query this many times to check stability"
    )
    parser.add_argument(
        "--json", action="store_true", help="output raw JSON instead of human-readable"
    )
    args = parser.parse_args()

    # import here so the script can be called from repo root
    sys.path.insert(0, ".")
    from app.services.retrieval import RetrievalService

    service = RetrievalService()
    all_results = {}
    passed = 0
    failed = 0

    for query in GOLDEN_QUERIES:
        run_outputs = []
        for _ in range(args.runs):
            results, elapsed = run_query(service, args.video_id, query, args.top_k)
            run_outputs.append({"results": results, "latency_ms": round(elapsed * 1000, 1)})

        # top result should be the same across all runs
        top_ids = []
        for r in run_outputs:
            if r["results"]:
                top_ids.append(r["results"][0].get("start_time"))
            else:
                top_ids.append(None)

        stable = len(set(top_ids)) == 1
        has_results = bool(run_outputs[0]["results"])
        avg_latency = sum(r["latency_ms"] for r in run_outputs) / len(run_outputs)

        if has_results and stable:
            passed += 1
            status = "PASS"
        elif not has_results:
            failed += 1
            status = "NO RESULTS"
        else:
            # within-tolerance instability is acceptable per acceptance criteria
            status = "UNSTABLE"
            failed += 1

        all_results[query] = {
            "status": status,
            "stable": stable,
            "has_results": has_results,
            "avg_latency_ms": avg_latency,
            "runs": run_outputs,
        }

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        print(f"\nRetrieval verification — video_id={args.video_id}, runs={args.runs}\n")
        print(f"{'Query':<45} {'Status':<12} {'Avg latency':>12}  {'Top result'}")
        print("-" * 100)
        for query, data in all_results.items():
            top = ""
            if data["runs"][0]["results"]:
                r = data["runs"][0]["results"][0]
                top = f"{r['start_time']:.1f}s — {r['text'][:50]}"
            print(f"{query:<45} {data['status']:<12} {data['avg_latency_ms']:>10.0f}ms  {top}")

        print(f"\n{passed}/{len(GOLDEN_QUERIES)} queries passed")
        if failed:
            print(f"{failed} queries failed — check logs above")
            sys.exit(1)


if __name__ == "__main__":
    main()
