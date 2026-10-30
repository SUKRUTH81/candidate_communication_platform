import pytest

from candidates.models import Candidate
from messaging.models import Message


@pytest.mark.django_db
class TestCandidateAPI:
    def test_create_normalises_phone_and_generates_code(self, api):
        r = api.post("/api/candidates/", {"name": "  Priya   Shah ", "phone": "98765 43210", "email": "Priya@Example.com"}, format="json")
        assert r.status_code == 201
        assert r.data["phone"] == "+919876543210"
        assert r.data["name"] == "Priya Shah"
        assert r.data["email"] == "priya@example.com"
        assert len(r.data["code"]) == 6

    def test_validation_errors_are_field_level_and_friendly(self, api):
        r = api.post("/api/candidates/", {"name": "A", "phone": "12345", "email": "nope"}, format="json")
        assert r.status_code == 400
        err = r.data["error"]
        assert err["code"] == "validation_error"
        assert set(err["fields"]) == {"name", "phone", "email"}

    def test_duplicate_phone_rejected_even_if_formatted_differently(self, api, make_candidate):
        make_candidate(name="Existing", phone="+919876543210")
        r = api.post("/api/candidates/", {"name": "New", "phone": "09876543210"}, format="json")
        assert r.status_code == 400
        assert "Existing" in r.data["error"]["fields"]["phone"]

    def test_email_optional(self, api):
        r = api.post("/api/candidates/", {"name": "No Email", "phone": "+919123456789"}, format="json")
        assert r.status_code == 201 and r.data["email"] == ""

    def test_search_by_name_phone_digits_and_code(self, api, make_candidate):
        a = make_candidate("Aditya Kumar", "+919012345678")
        make_candidate("Priya Shah", "+919123456789")
        assert [c["name"] for c in api.get("/api/candidates/?search=adit").data["results"]] == ["Aditya Kumar"]
        assert [c["name"] for c in api.get("/api/candidates/?search=+91 91234").data["results"]] == ["Priya Shah"]
        assert api.get(f"/api/candidates/?search={a.code.lower()}").data["count"] == 1
        assert api.get("/api/candidates/?search=zzz").data["count"] == 0

    def test_pagination(self, api, make_candidate):
        for i in range(12):
            make_candidate(f"Person {i:02d}")
        r = api.get("/api/candidates/?page_size=5&page=3")
        assert r.data["count"] == 12 and len(r.data["results"]) == 2

    def test_delete_removes_history(self, api, make_candidate):
        c = make_candidate()
        Message.objects.create(candidate=c, body="hi", channel="sms", status="sent")
        assert api.delete(f"/api/candidates/{c.id}/").status_code == 204
        assert Message.objects.count() == 0

    def test_bulk_delete(self, api, make_candidate):
        cs = [make_candidate(f"C{i}") for i in range(3)]
        r = api.post("/api/candidates/bulk-delete/", {"ids": [str(c.id) for c in cs[:2]]}, format="json")
        assert r.data == {"deleted": 2} and Candidate.objects.count() == 1

    def test_unknown_candidate_is_404_with_envelope(self, api):
        r = api.get("/api/candidates/00000000-0000-0000-0000-000000000000/")
        assert r.status_code == 404 and "message" in r.data["error"]

    def test_last_message_annotation_ignores_scheduled(self, api, make_candidate):
        c = make_candidate()
        Message.objects.create(candidate=c, body="a", channel="sms", status="delivered")
        Message.objects.create(candidate=c, body="b", channel="sms", status="scheduled")
        row = api.get("/api/candidates/").data["results"][0]
        assert row["last_message_status"] == "delivered"
