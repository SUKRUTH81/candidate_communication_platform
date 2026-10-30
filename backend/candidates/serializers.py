import phonenumbers
from rest_framework import serializers

from .models import Candidate

DEFAULT_REGION = "IN"


def normalise_phone(raw: str) -> str:
    raw = (raw or "").strip()
    try:
        parsed = phonenumbers.parse(raw, DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        raise serializers.ValidationError("Enter a valid mobile number, e.g. +91 98765 43210.")
    if not phonenumbers.is_valid_number(parsed):
        raise serializers.ValidationError("This doesn't look like a valid phone number. Include the country code if it's not an Indian number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class CandidateSerializer(serializers.ModelSerializer):
    # annotated in the view (latest non-scheduled message)
    last_message_at = serializers.DateTimeField(read_only=True, default=None)
    last_message_status = serializers.CharField(read_only=True, default=None)

    class Meta:
        model = Candidate
        fields = ["id", "code", "name", "phone", "email", "created_at", "last_message_at", "last_message_status"]
        read_only_fields = ["id", "code", "created_at"]
        extra_kwargs = {"email": {"required": False, "allow_blank": True}}

    def validate_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_phone(self, value):
        phone = normalise_phone(value)
        qs = Candidate.objects.filter(phone=phone)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        existing = qs.first()
        if existing:
            raise serializers.ValidationError(f"A candidate with this number already exists ({existing.name}).")
        return phone

    def validate_email(self, value):
        return value.strip().lower()


class BulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=500)
