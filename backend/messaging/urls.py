from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("messages", views.MessageViewSet, basename="message")
router.register("templates", views.TemplateViewSet, basename="template")

urlpatterns = [
    path("meta/", views.MetaView.as_view()),
    path("provider/health/", views.HealthView.as_view()),
    path("webhooks/provider/", views.provider_webhook),
    path("batches/<uuid:pk>/", views.BatchView.as_view()),
    path("candidates/<uuid:pk>/messages/", views.CandidateHistoryView.as_view()),
    *router.urls,
]
