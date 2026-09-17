"""
Greenroom Phase 4 — Background worker test.

Tests: async scan, async application, batch processing, task polling.
Run with: python test_phase4.py (while server is running)
"""

import time
import requests

BASE = "http://localhost:8000"
EMAIL = f"phase4_{int(time.time())}@greenroom.ai"
PASSWORD = "testpass123"


def step(name):
    print(f"\n{'─'*60}")
    print(f"  {name}")
    print(f"{'─'*60}")


def poll_task(task_id, headers, timeout=300):
    """Poll a task until it completes or fails."""
    start = time.time()
    last_progress = ""
    while time.time() - start < timeout:
        r = requests.get(f"{BASE}/api/events/{task_id}/status")
        status = r.json()
        progress = status.get("progress", "")
        state = status.get("status", "")

        if progress != last_progress:
            print(f"    [{state}] {progress}")
            last_progress = progress

        if state == "completed":
            return status.get("result")
        if state == "failed":
            print(f"    ERROR: {status.get('error', 'Unknown')[:200]}")
            return None

        time.sleep(2)

    print("    TIMEOUT")
    return None


def main():
    print("\n" + "="*60)
    print("  GREENROOM — Phase 4 Background Worker Test")
    print("="*60)

    # ── Register + setup ──
    step("1. Register + upload resume + preferences")
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": EMAIL, "password": PASSWORD, "name": "Sarah Chen",
    })
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resume_text = open("test_data/sample_resume.txt").read()
    r = requests.post(f"{BASE}/api/resumes", headers=h, json={
        "raw_text": resume_text, "filename": "sarah.txt",
    })
    parsed = r.json().get("parsed_data", {})
    print(f"  Resume parsed: {parsed.get('name', 'EMPTY')} | {len(parsed.get('skills', []))} skills")

    requests.put(f"{BASE}/api/preferences", headers=h, json={
        "target_roles": ["Senior Backend Engineer"],
        "locations": ["Remote"],
        "salary_min": 150000, "salary_max": 300000,
        "remote_preference": "any",
    })
    print("  Preferences saved.")

    # ── Test 1: Async scan ──
    step("2. Async scan (should return instantly)")
    start = time.time()
    r = requests.post(f"{BASE}/api/jobs/scan", headers=h, json={"score_results": False})
    elapsed = time.time() - start
    data = r.json()
    task_id = data.get("task_id", "")
    print(f"  Returned in {elapsed:.2f}s (should be < 1s)")
    print(f"  Task ID: {task_id}")
    assert elapsed < 5, f"Scan should return instantly, took {elapsed:.1f}s"

    # Poll for completion
    print("  Polling for completion...")
    result = poll_task(task_id, h, timeout=120)
    if result:
        print(f"  Scan result: {result}")
    else:
        print("  Scan task didn't complete — check server logs")

    # ── List jobs ──
    step("3. Check discovered jobs")
    r = requests.get(f"{BASE}/api/jobs?limit=5", headers=h)
    jobs = r.json()
    print(f"  Found {len(jobs)} jobs:")
    for j in jobs[:5]:
        print(f"    {j['id'][:12]}.. | {j['title'][:35]} @ {j['company'][:20]}")

    if not jobs:
        print("  No jobs found — can't test applications")
        return

    # ── Test 2: Async application ──
    target = jobs[0]
    step(f"4. Async application (background pipeline)")
    print(f"  Job: {target['title']} @ {target['company']}")
    start = time.time()
    r = requests.post(f"{BASE}/api/applications", headers=h, json={
        "job_id": target["id"], "run_pipeline": True,
    })
    elapsed = time.time() - start
    data = r.json()
    task_id = data.get("task_id", "")
    print(f"  Returned in {elapsed:.2f}s (should be < 1s)")
    print(f"  Task ID: {task_id}")

    if task_id:
        print("  Polling pipeline progress...")
        result = poll_task(task_id, h, timeout=300)
        if result:
            print(f"  Pipeline result: app_id={result.get('application_id')}, status={result.get('status')}")
        else:
            print("  Pipeline didn't complete — may be rate limited")

    # ── Test 3: Check applications ──
    step("5. Check applications")
    r = requests.get(f"{BASE}/api/applications", headers=h)
    apps = r.json()
    print(f"  Applications: {len(apps)}")
    for a in apps:
        has_letter = "yes" if a.get("cover_letter") else "no"
        print(f"    {a['status']} | {a.get('job_title','')} @ {a.get('job_company','')} | cover_letter: {has_letter}")

    # ── Test 4: Batch (if enough jobs) ──
    if len(jobs) >= 2:
        step("6. Batch processing (2 jobs)")
        batch_ids = [j["id"] for j in jobs[1:3]]
        r = requests.post(f"{BASE}/api/applications/batch", headers=h, json={
            "job_ids": batch_ids,
        })
        data = r.json()
        task_id = data.get("task_id", "")
        print(f"  Batch task: {task_id}")
        print(f"  Jobs queued: {data.get('job_count')}")
        print("  Polling batch progress...")
        result = poll_task(task_id, h, timeout=600)
        if result:
            print(f"  Batch result: {result.get('processed')} processed")
        else:
            print("  Batch didn't complete — may be rate limited")

    # ── Stats ──
    step("7. Final stats")
    r = requests.get(f"{BASE}/api/applications/stats", headers=h)
    stats = r.json()
    print(f"  Total: {stats['total']} | Ready: {stats['ready']} | Applied: {stats['applied']}")

    print(f"\n{'='*60}")
    print(f"  PHASE 4 TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
