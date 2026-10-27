from __future__ import annotations

# dev-only script to submit the 49 eval videos through pipeline.
# requires DISABLE_AUTH=true (or equivalent) since endpoint is protected in production.
import argparse
import sys
import time

import httpx

VIDEOS = [
    ("1WpujO13Wrz5W8GzYEVJp_jzXxR431yTd", "https://www.youtube.com/watch?v=oeYBdghaIjc"),
    ("1TOouFepc6ZpPMBAsDEnOOohfSCfFkDhI", "https://www.youtube.com/watch?v=JHZFc4hMGhk"),
    ("1AIPvwmdc7M4gKAUFme-F1WxAkWkjudqf", "https://www.youtube.com/watch?v=ZA-tUyM_y7s"),
    ("1P83yEZ8wOcWVyrnZ0QR603zpT6mZt6_U", "https://www.youtube.com/watch?v=CHhwJjR0mZA"),
    ("1Dvf1PAPsH3WAWf8ZiHxQClgKjOu9VWx8", "https://www.youtube.com/watch?v=oS9aPzUNG-s"),
    ("1nxYI5h-svzW64_swHCWMqp92R0gQwOuS", "https://www.youtube.com/watch?v=Nu8YGneFCWE"),
    ("1stUh4rpUlfJkXuFyUhLUPYNPYSzpOcBr", "https://www.youtube.com/watch?v=yndgIDO0zQQ"),
    ("1UtL9COxasiZGIs4Wlp-1yBeQU-qfblYP", "https://www.youtube.com/watch?v=76dhtgZt38A"),
    ("1GdpeRiVW4UIgn-1zVlQc9hc5b4dciww_", "https://www.youtube.com/watch?v=U1JYwHcFfso"),
    ("169HMm2i8YlevWTyx1taAiTcDwOXOraEz", "https://www.youtube.com/watch?v=Xnpo1atN-Iw"),
    ("15ozJ6qG_vSGwala0ZqbV-zKXM4TYY2-V", "https://www.youtube.com/watch?v=oFVYVzlvk9c"),
    ("1kXfjxfaliDNa3GdvcVvkUUp1P7vpqYPB", "https://www.youtube.com/watch?v=IBfWDYSffUU"),
    ("1m9cLrMpYkDqwlsp4tvEeHRaURsx5pkw0", "https://www.youtube.com/watch?v=5cF5Bgv59Sc"),
    ("1CjCuxH23SC9zLrLgKYXmRqZ7cjaK6upC", "https://www.youtube.com/watch?v=f9cVS_URPc0"),
    ("1PuRiJ8hswxAUlWVa1EEuV6m-ROaNjENy", "https://www.youtube.com/watch?v=NSHizBK9JD8"),
    ("1Mu9IIUownfyQhfQULtZ4sVSjGgHAjEUz", "https://www.youtube.com/watch?v=EmSmaW-ud6A"),
    ("1cXRF7gJnO3HaKrL7rGt5omxL9TKXunra", "https://www.youtube.com/watch?v=r4-cftqTcdI"),
    ("1vGQLVd7llr12mTbh401iQAjbKBwsXZAy", "https://www.youtube.com/watch?v=KLBCUx1is2c"),
    ("1JiL4htAnW0sjGr64LMrOWW0AJ8xS8Jqf", "https://www.youtube.com/watch?v=TDo3r5M1LNo"),
    ("1Yw2N5z3lLdz3ZECMIDrldEBPq3OkaEFu", "https://www.youtube.com/watch?v=i9OAOk0CUQE"),
    ("1ly0X8OJg4BSj8nhTjdaMrVWNSYiyFo4R", "https://www.youtube.com/watch?v=JbafQJx1CIA"),
    ("1h23keRriJtzP5muXYjplvG52KWC1Lkd2", "https://www.youtube.com/watch?v=IPSaG9RRc-k"),
    ("1y2mtIXKkpO5ht3kSz-Y_y0o0hHrIVK8b", "https://www.youtube.com/watch?v=KlQiwkhLBg0"),
    ("1a21aAUeQh_1r1mahcI5FIi3hIsbtDv_1", "https://www.youtube.com/watch?v=g0bXSXuLVb0"),
    ("18pFjo4nTpreEByi04geESLn9mLy6gQXv", "https://www.youtube.com/watch?v=MAyraVVYB64"),
    ("1t-2PlgctX5XQR-klvG-GRZgWh6UbQgEP", "https://www.youtube.com/watch?v=ZLdooNwP7Pw"),
    ("1n3_RwADFI49alM06Qo2gtbEqTocZ103h", "https://www.youtube.com/watch?v=UuxR0NCkg0k"),
    ("1DefcVWV2EXpplRbokUghWq55n-J7E3vu", "https://www.youtube.com/watch?v=KPkOkiwAlbY"),
    ("1q1RHOVn8Fo_vsHwV27vo2GVeEwWeazs9", "https://www.youtube.com/watch?v=e98MPnMHLxE"),
    ("1Ru_SR18FBF9v8PvStDtzQvqR6AdZmttJ", "https://www.youtube.com/watch?v=vCIa2h1C9UQ"),
    ("1sgvYnwP_JjoH8JxOukiKVsvTDxafANLb", "https://www.youtube.com/watch?v=C1lhuz6pZC0"),
    ("1MB_xGHFVFRNIJh-C4nmJ1a4Wlv8K-HPu", "https://www.youtube.com/watch?v=lUUte2o2Sn8"),
    ("1kN6QqW1kRM08WfCVSUTxuHII8q_65sfP", "https://www.youtube.com/watch?v=vT1JzLTH4G4"),
    ("1Uv5B1FyibbuU4KneqG4stFb2KMLHTMAK", "https://www.youtube.com/watch?v=DAOcjicFr1Y"),
    ("1mzkwhXgBaH7aUZTRXZSH2a9blNQV1xRX", "https://www.youtube.com/watch?v=5WoItGTWV54"),
    ("1ZDMQtSocIdAFux25W3UaXqVs86AFNjFY", "https://www.youtube.com/watch?v=rmVRLeJRkl4"),
    ("1oQiUue1XhXF3Ri99cq9W2Ebd2aeLBUVU", "https://www.youtube.com/watch?v=jGwO_UgTS7I"),
    ("1eQWpyfx0-HKOOOcYErkmXipkxaYMJmaU", "https://www.youtube.com/watch?v=Md9QOXomxFs"),
    ("1SGUrWnjYtZIoyLM1HiB3S6QH-_MyFm1Q", "https://www.youtube.com/watch?v=bNb2fEVKeEo"),
    ("1ucpHm_ZIyV922qx3pkhoirurO4GGBnwq", "https://www.youtube.com/watch?v=0LixFSa7yts"),
    ("1N5RiggT4LYo3aoiv5sHLX-d4wGtvX1S4", "https://www.youtube.com/watch?v=nykOeWgQcHM"),
    ("1gCK5Tgv7lxjbS7v69W5sSg3ipm-HXd1l", "https://www.youtube.com/watch?v=2NMtS1ecb3o"),
    ("1fKtICvqBAkRF5ut41PpsI-mJEcxwmuiP", "https://www.youtube.com/watch?v=4nXw-f6NJ9s"),
    ("1Ym1Q1WjvGe4AtBOhcUJO-7Fc7n4UDI9M", "https://www.youtube.com/watch?v=wEKFGdo4Sck"),
    ("1zOy6icZjZU80GhX5chd5A9CkdaFDdSgH", "https://www.youtube.com/watch?v=ANCN7vr9FVk"),
    ("1QKBhH3luH0C85-2HcFDfbjlmQ-k-or17", "https://www.youtube.com/watch?v=9YtmGy-wfE4"),
    ("18NbWggaDS_E0t4zdiB14BVzOyxwfHUE2", "https://www.youtube.com/watch?v=f9XFM8YLccg"),
    ("1CFUje9XVZhP-YWK2Fn46jyu_s5nv9I7l", "https://www.youtube.com/watch?v=l1kLCrxL9Hk"),
    ("1DDY3jd0hZPqyGqE-F1c8hmuS8XX659Xa", "https://www.youtube.com/watch?v=92WaNz9mPeY"),
]


def submit(base_url: str, drive_id: str, youtube_url: str) -> tuple[bool, str]:
    endpoint = f"{base_url.rstrip('/')}/api/videos/link"
    try:
        r = httpx.post(endpoint, json={"url": youtube_url, "title": drive_id}, timeout=30)
        if r.status_code in (200, 201):
            vid = r.json().get("id", "?")
            cached = r.status_code == 200
            return True, f"video_id={vid}" + (" (already processed)" if cached else "")
        return False, f"http {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bulk_submit")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between submissions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    ok = 0
    failed = []

    for i, (drive_id, url) in enumerate(VIDEOS, 1):
        print(f"[{i:02d}/{len(VIDEOS)}] {drive_id[:20]}... ", end="", flush=True)
        if args.dry_run:
            print("dry-run, skipped")
            continue
        success, msg = submit(args.base_url, drive_id, url)
        if success:
            ok += 1
            print(f"ok — {msg}")
        else:
            failed.append((drive_id, url, msg))
            print(f"FAILED — {msg}")
        if i < len(VIDEOS):
            time.sleep(args.delay)

    print(f"\n{ok}/{len(VIDEOS)} submitted successfully")
    if failed:
        print(f"\nfailed ({len(failed)}):")
        for drive_id, url, msg in failed:
            print(f"  {drive_id}  {url}  {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
