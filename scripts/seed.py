"""Seed demo candidates and templates through the public API: python scripts/seed.py [api_base]"""
import sys
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api"

PEOPLE = [
    ("Aditya Kumar", "+919012345678"),
    ("Ajit Srivastava", "+919123456789"),
    ("Amarjeet Kumar", "+919234567890"),
    ("Aniket Sawant", "+919456789012"),
    ("Ira Akbar", "+919876512345"),
    ("Krishna Khandelwal", "+919876543210"),
    ("Urvashi Soni", "+919988766554"),
    # Deterministic numbers that trigger specific provider behavior (see provider/app.py)
    ("Demo Invalid Number", "+919876500000"),
    ("Demo Opted Out", "+919876501111"),
    ("Demo Rate Limited", "+919876502222"),
    ("Demo Flaky Then OK", "+919876503333"),
    ("Demo Phone Off", "+919876504444"),
    ("Demo Never Reads", "+919876505555"),
]

print("--- Seeding Candidates ---")
for name, phone in PEOPLE:
    email = name.split()[0].lower().replace("demo", "candidate") + "@example.com"
    try:
        r = requests.post(f"{BASE}/candidates/", json={"name": name, "phone": phone, "email": email}, timeout=10)
        if r.status_code == 201:
            print(f"{name:24} 201 Created")
        elif r.status_code == 400 and "already exists" in r.text:
            print(f"{name:24} (Already exists in database)")
        else:
            msg = r.json().get("error", {}).get("message") or r.text
            print(f"{name:24} {r.status_code} {msg}")
    except Exception as e:
        print(f"{name:24} Failed: {e}")

TEMPLATES = [
    {
        "name": "Interview Invitation",
        "body": "Hi {{first_name}}, thanks for applying to Hunar.ai! We would love to invite you for an interview. Please let us know if tomorrow 11:00 AM works for you.",
    },
    {
        "name": "Document Verification",
        "body": "Hello {{first_name}}, please share your updated documents for candidate ID {{candidate_id}}. We sent the details to {{email}}.",
    },
    {
        "name": "Offer Confirmation",
        "body": "Congratulations {{name}}! We are thrilled to extend an offer from Hunar.ai. We have sent the detailed offer letter to {{email}}.",
    },
]

print("\n--- Seeding Templates ---")
for t in TEMPLATES:
    try:
        r = requests.post(f"{BASE}/templates/", json=t, timeout=10)
        if r.status_code == 201:
            print(f"{t['name']:24} 201 Created")
        elif r.status_code == 400 and "already exists" in r.text:
            print(f"{t['name']:24} (Already exists in database)")
        else:
            msg = r.json().get("error", {}).get("message") or r.text
            print(f"{t['name']:24} {r.status_code} {msg}")
    except Exception as e:
        print(f"{t['name']:24} Failed: {e}")

