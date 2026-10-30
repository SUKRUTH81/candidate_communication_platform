import pytest
from rest_framework.test import APIClient

from candidates.models import Candidate


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_candidate(db):
    n = {"i": 0}

    def make(name="Rahul Sharma", phone=None, email="rahul@example.com"):
        n["i"] += 1
        return Candidate.objects.create(name=name, phone=phone or f"+9198765{n['i']:05d}", email=email)
    return make
