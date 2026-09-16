"""
Greenroom — Full API end-to-end test.

Run with: python test_api.py
Requires: server running at http://localhost:8000
"""

import time
import requests
import json

BASE = "http://localhost:8000"
EMAIL = f"test_{int(time.time())}@greenroom.ai"
PASSWORD = "testpass123"


def step(name):
    print(f"\n{'─'*60}")
    print(f"  {name}")
    print(f"{'─'*60}")


def main():
    print("\n" + "="*60)
    print("  GREENROOM — Full API Test")
    print("="*60)

    # ── Step 1: Register ──
    step("1. Register new user")
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": EMAIL,
        "password": PASSWORD,
        "name": "Sarah Chen",
    })
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"  Registered: {EMAIL}")
    print(f"  Token: {token[:30]}...")

    # ── Step 2: Verify auth ──
    step("2. Verify auth (GET /me)")
    r = requests.get(f"{BASE}/api/auth/me", headers=headers)
    assert r.status_code == 200, f"Auth failed: {r.text}"
    user = r.json()
    print(f"  User: {user['name']} ({user['email']})")

    # ── Step 3: Upload resume ──
    step("3. Upload resume")
    resume_text = open("test_data/sample_resume.txt").read()
    start = time.time()
    r = requests.post(f"{BASE}/api/resumes", headers=headers, json={
        "raw_text": resume_text,
        "filename": "sarah_chen.txt",
    })
    elapsed = time.time() - start
    assert r.status_code == 201, f"Resume upload failed: {r.text}"
    resume = r.json()
    parsed = resume.get("parsed_data", {})
    print(f"  Parsed in {elapsed:.1f}s")
    print(f"  Name: {parsed.get('name', 'EMPTY')}")
    print(f"  Skills: {len(parsed.get('skills', []))} found")
    print(f"  Experience: {len(parsed.get('experience', []))} roles")
    if not parsed.get("name"):
        print("  ⚠ Warning: Parse returned empty — Gemini may be rate-limited")

    # ── Step 4: Set preferences ──
    step("4. Set job preferences")
    r = requests.put(f"{BASE}/api/preferences", headers=headers, json={
        "target_roles": ["Senior Backend Engineer"],
        "locations": ["Remote"],
        "salary_min": 150000,
        "salary_max": 300000,
        "remote_preference": "any",
    })
    assert r.status_code == 200, f"Preferences failed: {r.text}"
    prefs = r.json()
    print(f"  Roles: {prefs['target_roles']}")
    print(f"  Locations: {prefs['locations']}")
    print(f"  Salary: ${prefs['salary_min']:,} - ${prefs['salary_max']:,}")

    # ── Step 5: Scan for jobs (no scoring — fast) ──
    step("5. Scan for jobs (discovery only)")
    start = time.time()
    r = requests.post(f"{BASE}/api/jobs/scan", headers=headers, json={
        "score_results": False,
    }, timeout=120)
    elapsed = time.time() - start
    assert r.status_code == 200, f"Scan failed: {r.text}"
    scan = r.json()
    print(f"  Scanned in {elapsed:.1f}s")
    print(f"  New jobs: {scan['new_jobs']}")
    print(f"  Duplicates: {scan['duplicates']}")

    # ── Step 6: List discovered jobs ──
    step("6. List discovered jobs")
    r = requests.get(f"{BASE}/api/jobs?limit=5", headers=headers)
    assert r.status_code == 200, f"List jobs failed: {r.text}"
    jobs = r.json()
    print(f"  Found {len(jobs)} jobs:")
    for j in jobs[:5]:
        score_str = f" ({j['overall_score']}/100)" if j.get("overall_score") else ""
        print(f"    {j['id'][:12]}.. | {j['title'][:35]} @ {j['company'][:20]}{score_str}")

    if not jobs:
        print("  No jobs found — cannot test application creation.")
        return

    # ── Step 7: Create application (FULL PIPELINE) ──
    target_job = jobs[0]
    step(f"7. Create application — FULL PIPELINE")
    print(f"  Job: {target_job['title']} @ {target_job['company']}")
    print(f"  Running pipeline (research → tailor → cover letter → interview prep)...")
    print(f"  This takes ~90 seconds...")

    start = time.time()
    r = requests.post(f"{BASE}/api/applications", headers=headers, json={
        "job_id": target_job["id"],
        "run_pipeline": True,
    }, timeout=300)
    elapsed = time.time() - start

    assert r.status_code == 201, f"Application failed: {r.status_code} {r.text}"
    app = r.json()
    print(f"  Pipeline completed in {elapsed:.1f}s")
    print(f"  Status: {app['status']}")

    # Show outputs
    if app.get("cover_letter"):
        print(f"\n  COVER LETTER (first 300 chars):")
        print(f"  {app['cover_letter'][:300]}...")
    else:
        print(f"  ⚠ Cover letter empty — check server logs")

    if app.get("interview_prep"):
        print(f"\n  INTERVIEW PREP (first 300 chars):")
        print(f"  {app['interview_prep'][:300]}...")
    else:
        print(f"  ⚠ Interview prep empty — check server logs")

    if app.get("tailored_resume"):
        print(f"\n  TAILORED RESUME: {len(app['tailored_resume'])} chars")

    # ── Step 8: Check application stats ──
    step("8. Application stats")
    r = requests.get(f"{BASE}/api/applications/stats", headers=headers)
    assert r.status_code == 200
    stats = r.json()
    print(f"  Total: {stats['total']}")
    print(f"  Ready for review: {stats['ready']}")
    print(f"  Applied: {stats['applied']}")

    # ── Step 9: Update status to "applied" ──
    step("9. Mark as applied")
    r = requests.patch(f"{BASE}/api/applications/{app['id']}", headers=headers, json={
        "status": "applied",
        "notes": "Submitted via company website",
    })
    assert r.status_code == 200
    updated = r.json()
    print(f"  Status: {updated['status']}")
    print(f"  Notes: {updated['notes']}")

    # ── Done ──
    print(f"\n{'='*60}")
    print(f"  ALL TESTS PASSED")
    print(f"  Greenroom end-to-end flow verified.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()