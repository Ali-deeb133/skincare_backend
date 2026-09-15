
from rest_framework import serializers

class DecisionRequestSerializer(serializers.Serializer):
    """
    يتحقق من صحة حقل 'text' الوارد من المستخدم.
    Validates the incoming { "text": "…" } payload.

    Example:
        {
            "text": "My skin type is dry and I want
                     The Ordinary Hyaluronic Acid 2% + B5 30ml"
        }
    """

    text = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=1000,
        error_messages={
            "required":   "Please provide a 'text' field.",
            "blank":      "The 'text' field cannot be empty.",
            "max_length": "Message is too long (max 1000 characters).",
        },
    )

    def validate_text(self, value: str) -> str:
        return value.strip()



class SkinSuitabilitySerializer(serializers.Serializer):
    """نتيجة الملاءمة لنوع بشرة واحد."""
    skin_type   = serializers.CharField()
    suitability = serializers.ChoiceField(choices=["Suitable", "Not Suitable"])


class RecommendationSerializer(serializers.Serializer):
    """منتج موصى به واحد."""
    product_name = serializers.CharField()
    product_type = serializers.CharField()
    brand        = serializers.CharField()
    price        = serializers.FloatField(allow_null=True)
    url          = serializers.CharField(allow_blank=True)
    similarity   = serializers.FloatField()


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE SERIALIZER  (shape varies by case — used for docs)
# ─────────────────────────────────────────────────────────────────────────────

class DecisionResponseSerializer(serializers.Serializer):
    """
    الاستجابة الكاملة لـ API.
    Full API response schema.

    status  : "suitable" | "not_suitable" | "error" | "info"
    message : رسالة نصية للمستخدم
    """
    status  = serializers.ChoiceField(
        choices=["suitable", "not_suitable", "error", "info"]
    )
    message = serializers.CharField()

    # موجودة فقط عند status == "suitable" أو "not_suitable"
    product_name    = serializers.CharField(required=False)
    product_type    = serializers.CharField(required=False)
    skin_type_user  = serializers.CharField(required=False)
    suitability     = SkinSuitabilitySerializer(many=True, required=False)

    # موجودة فقط عند status == "suitable"
    recommendations = RecommendationSerializer(many=True, required=False)
