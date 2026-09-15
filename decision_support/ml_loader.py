"""
decision_support/ml_loader.py
──────────────────────────────
يحمّل جميع نماذج ML مرة واحدة عند بدء تشغيل Django.
Loads all ML artefacts once when Django starts (module-level singleton).
 
المسارات تُقرأ من settings.py:
    CLASSIFIER_DIR   — مجلد يحتوي على ملفات نموذج Random Forest
    RECOMMENDER_PATH — المسار الكامل لملف recommender_assets.pkl
"""
 
import json
import logging
import pickle
from pathlib import Path
 
import numpy as np
from scipy.sparse import csr_matrix, hstack
 
from django.conf import settings
import warnings
from sklearn.exceptions import InconsistentVersionWarning

warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
logger = logging.getLogger(__name__)

 
# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
CLASSIFIER_DIR = Path(
    getattr(
        settings,
        "CLASSIFIER_DIR",
        Path(__file__).resolve().parent / "ml_models" / "classifier",
    )
)
 
RECOMMENDER_PATH = Path(
    getattr(
        settings,
        "RECOMMENDER_PATH",
        Path(__file__).resolve().parent / "ml_models" / "recommender" / "recommender_assets.pkl",
    )
)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# FIX: ingredient_tokenizer
# ─────────────────────────────────────────────────────────────────────────────
# الـ TfidfVectorizer تم حفظه في Colab مع tokenizer مُعرَّف في __main__
# عند تحميله في Django لا يجد الدالة → نُعيد تعريفها هنا قبل فك الضغط
# ثم نُحقن الـ tokenizer الصحيح مباشرة داخل الـ vectorizer بعد التحميل
def ingredient_tokenizer(text: str) -> list[str]:
    """
    نفس الدالة المستخدمة أثناء التدريب في Colab.
    تقسّم المكونات بالفاصلة — كل مكوّن = token واحد.
    Same function used during training: splits by comma, one ingredient = one token.
    """
    return [t.strip().lower() for t in text.split(",") if t.strip()]
 
 
class _IngredientTokenizerUnpickler(pickle.Unpickler):
    """
    Custom Unpickler يُحلّ مشكلة:
    "Can't get attribute 'ingredient_tokenizer' on <module '__main__'>"
 
    عند فك ضغط الـ pickle يبحث عن ingredient_tokenizer في __main__
    نُعيد توجيهه ليجدها في هذا الملف بدلاً من __main__
    """
 
    def find_class(self, module: str, name: str):
        # إذا طلب الـ pickle الدالة من __main__ → أعطه إياها من هنا
        if name == "ingredient_tokenizer":
            return ingredient_tokenizer
        return super().find_class(module, name)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# LOAD CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────
def _load_classifier():
    """تحميل نموذج Random Forest + TF-IDF + metadata."""
    try:
        with open(CLASSIFIER_DIR / "best_model_Random_Forest.pkl", "rb") as f:
            model = pickle.load(f)
 
        # استخدام الـ Custom Unpickler لحل مشكلة ingredient_tokenizer
        with open(CLASSIFIER_DIR / "tfidf_vectorizer.pkl", "rb") as f:
            vectorizer = _IngredientTokenizerUnpickler(f).load()
 
        # ضمان: تأكد أن الـ tokenizer المُحمَّل يستخدم نسختنا المحلية
        vectorizer.tokenizer = ingredient_tokenizer
 
        with open(CLASSIFIER_DIR / "product_dummies_cols.json") as f:
            prod_cols = json.load(f)   # ["prod_Cleanser", "prod_Eye cream", ...]
 
        with open(CLASSIFIER_DIR / "label_columns.json") as f:
            skin_types = json.load(f)  # ["Combination", "Dry", "Normal", "Oily", "Sensitive"]
 
        logger.info("✓ Classifier loaded from %s", CLASSIFIER_DIR)
        return model, vectorizer, prod_cols, skin_types
 
    except Exception as exc:
        logger.error("✗ Classifier load failed: %s", exc)
        raise
 
 
# ─────────────────────────────────────────────────────────────────────────────
# LOAD RECOMMENDER
# ─────────────────────────────────────────────────────────────────────────────
def _load_recommender():
    """تحميل بيانات نظام التوصية."""
    try:
        with open(RECOMMENDER_PATH, "rb") as f:
            assets = pickle.load(f)
 
        df            = assets["df"]
        ingred_matrix = assets["ingred_matrix"]
 
        logger.info("✓ Recommender loaded from %s", RECOMMENDER_PATH)
        return df, ingred_matrix
 
    except Exception as exc:
        logger.error("✗ Recommender load failed: %s", exc)
        raise
 
 
# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL SINGLETONS (loaded once on first import)
# ─────────────────────────────────────────────────────────────────────────────
MODEL, VECTORIZER, PROD_COLS, SKIN_TYPES = _load_classifier()
REC_DF, INGRED_MATRIX                   = _load_recommender()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: predict_skin_types()
# ─────────────────────────────────────────────────────────────────────────────
def predict_skin_types(ingredients_str: str, product_label: str = "Moisturizer") -> dict:
    """
    تمرير مكونات المنتج → قاموس {نوع_البشرة: "Suitable" | "Not Suitable"}
 
    Parameters
    ----------
    ingredients_str : str
        مكونات المنتج مفصولة بفاصلة.
    product_label   : str
        نوع المنتج: Moisturizer / Face Mask / Cleanser / Treatment / Eye cream / Sun protect
    """
    # TF-IDF features
    X_ing = VECTORIZER.transform([ingredients_str])
 
    # Product-type one-hot
    prod_vec = np.zeros((1, len(PROD_COLS)))
    col_name = f"prod_{product_label}"
    if col_name in PROD_COLS:
        prod_vec[0, PROD_COLS.index(col_name)] = 1.0
 
    X_combined = hstack([X_ing, csr_matrix(prod_vec)])
    y_hat      = MODEL.predict(X_combined)[0]
 
    return {
        skin: ("Suitable" if pred == 1 else "Not Suitable")
        for skin, pred in zip(SKIN_TYPES, y_hat)
    }
 
 
# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: recommend()
# ─────────────────────────────────────────────────────────────────────────────
def recommend(product_name: str, top_n: int = 5) -> list:
    """
    إرجاع أكثر top_n منتجًا تشابهًا من نفس النوع وبراند مختلف.
 
    Returns list of dicts:
        product_name, product_type, brand, price, url, similarity
    """
    from numpy.linalg import norm
 
    df            = REC_DF
    ingred_matrix = INGRED_MATRIX
 
    if product_name not in df["product_name"].values:
        return []
 
    idx          = df.index[df["product_name"] == product_name][0]
    target_vec   = ingred_matrix.iloc[idx].values
    prod_type    = df.loc[idx, "product_type"]
    brand_target = df.loc[idx, "brand"]
 
    candidates = df[df["product_type"] == prod_type].copy()
    sims = []
    for i in candidates.index:
        vec   = ingred_matrix.iloc[i].values
        denom = norm(target_vec) * norm(vec)
        sim   = float(np.dot(target_vec, vec) / denom) if denom > 0 else 0.0
        sims.append(sim)
 
    candidates = candidates.copy()
    candidates["similarity"] = sims
    candidates = candidates[candidates["product_name"] != product_name]
    candidates = candidates[candidates["brand"]        != brand_target]
    top        = candidates.sort_values("similarity", ascending=False).head(top_n)
 
    return [
        {
            "product_name": row["product_name"],
            "product_type": row["product_type"],
            "brand":        row["brand"],
            "price":        float(row["price"]) if "price" in row else None,
            "url":          str(row.get("url", "")),
            "similarity":   round(float(row["similarity"]), 4),
        }
        for _, row in top.iterrows()
    ]
 