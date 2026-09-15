"""
decision_support/apps.py
"""

from django.apps import AppConfig


class DecisionSupportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "decision_support"
    verbose_name       = "Decision Support System"

    def ready(self):
        """
        يُشغَّل مرة واحدة عند بدء Django.
        يحمّل نماذج ML مسبقاً لتفادي التأخير عند أول طلب.
        Pre-load ML models at startup to avoid cold-start on first request.
        """
        try:
            from . import ml_loader  # noqa: F401  — triggers module-level loading
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Could not pre-load ML models: %s", exc
            )
