from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from candidates.views import CandidateViewSet

router = DefaultRouter(trailing_slash=True)
router.register("candidates", CandidateViewSet, basename="candidate")

urlpatterns = [
    path("healthz", lambda request: JsonResponse({"ok": True})),
    path("api/", include(router.urls)),
    path("api/", include("messaging.urls")),
]
