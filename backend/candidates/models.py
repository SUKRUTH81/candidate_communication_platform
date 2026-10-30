import secrets
import uuid

from django.db import models

# No 0/O/1/I so IDs are easy to read out loud.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_code():
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not Candidate.objects.filter(code=code).exists():
            return code


class Candidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=6, unique=True, editable=False)   # human-friendly "Candidate ID"
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)                 # normalised E.164
    email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
