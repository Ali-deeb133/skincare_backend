import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .ml_loader import predict_skin_types, recommend
from .serializers import DecisionRequestSerializer
from .text_parser import VALID_SKIN_TYPES, is_offtopic, parse_message

logger = logging.getLogger(__name__)


# RESPONSE BUILDERS

def _info(message: str) -> dict:
    return {"status": "info", "message": message}


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


# MAIN VIEW

class DecisionAPIView(APIView):


    def post(self, request, *args, **kwargs):

        serializer = DecisionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                _error(str(first_error)),
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = serializer.validated_data["text"]
        logger.info("[DecisionAPI] Received: %s", text[:120])

        if is_offtopic(text):
            return Response(
                _info(
                    "I'm here to help you make a purchase decision for skincare products. "
                    "Please send me your skin type and the product name you're interested in.\n\n"
                    "📌 Example:\n"
                    "\"My skin type is dry and I want "
                    "The Ordinary Hyaluronic Acid 2% + B5 Hydration Support Formula 30ml\""
                )
            )

        product_name, skin_type = parse_message(text)

        if skin_type is None:
            return Response(
                _error(
                    "I couldn't detect your skin type from your message. "
                    "Please specify one of the following skin types:\n"
                    "👉 Combination, Dry, Normal, Oily, Sensitive\n\n"
                    "📌 Example:\n"
                    "\"My skin type is oily and I want CeraVe Moisturizing Cream\""
                )
            )

       
        if product_name is None:
            return Response(
                _error(
                    "I couldn't detect a product name in your message. "
                    "Please include the full product name.\n\n"
                    "📌 Example:\n"
                    "\"My skin type is dry and I want "
                    "The Ordinary Hyaluronic Acid 2% + B5 Hydration Support Formula 30ml\""
                )
            )

        product = _find_product(product_name)
        if product is None:
            return Response(
                _error(
                    f"Sorry, I couldn't find \"{product_name}\" in our product database. "
                    "Please check the product name and try again."
                )
            )

        if not product.clean_ingreds or not product.clean_ingreds.strip():
            return Response(
                _error(
                    f"The product \"{product.product_name}\" was found, "
                    "but its ingredient list is not available yet. "
                    "Please try another product."
                )
            )

        try:
            suitability_map = predict_skin_types(
                ingredients_str=product.clean_ingreds,
                product_label=product.product_type,
            )
        except Exception as exc:
            logger.exception("[DecisionAPI] Classifier error: %s", exc)
            return Response(
                _error("An error occurred while analysing the product. Please try again later."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        suitability_list = [
            {"skin_type": sk, "suitability": verdict}
            for sk, verdict in suitability_map.items()
        ]

        user_verdict = suitability_map.get(skin_type, "Not Suitable")
        is_suitable  = user_verdict == "Suitable"

        response_data = {
            "status": "suitable" if is_suitable else "not_suitable",
            "message": (
                f"✅ Great news! \"{product.product_name}\" is suitable for your "
                f"{skin_type} skin. Here are some similar products you might also like."
                if is_suitable else
                f"⚠️ We recommend avoiding \"{product.product_name}\" for your "
                f"{skin_type} skin. It may not be the best match based on its ingredients."
            ),
            "product_name":   product.product_name,
            "product_type":   product.product_type,
            "skin_type_user": skin_type,
            "suitability":    suitability_list,
        }

        if is_suitable:
            try:
                recs = recommend(product.product_name, top_n=5)
                response_data["recommendations"] = recs
            except Exception as exc:
                logger.warning("[DecisionAPI] Recommender error (non-fatal): %s", exc)
                response_data["recommendations"] = []

        return Response(response_data, status=status.HTTP_200_OK)


# PRODUCT LOOKUP (fuzzy — 3 levels)

def _find_product(product_name: str):

    # المستوى 1: مطابقة تامة
    qs = Product.objects.filter(product_name__iexact=product_name)
    if qs.exists():
        return qs.first()

    # المستوى 2: contains
    qs = Product.objects.filter(product_name__icontains=product_name)
    if qs.exists():
        return min(qs, key=lambda p: abs(len(p.product_name) - len(product_name)))

    # المستوى 3: كلمة كلمة
    keywords = [w for w in product_name.split() if len(w) > 3]
    if keywords:
        qs = Product.objects.all()
        for kw in keywords:
            qs = qs.filter(product_name__icontains=kw)
        if qs.exists():
            return qs.first()

    return None
