import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

import joblib
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

LIFECYCLE_PATH = Path(
    "Dataset/AKLM_FINAL_v3_FINAL/lifecycle"
)

MODEL_DIR = Path("models")

MODEL_DIR.mkdir(
    exist_ok=True
)


# ==================================================
# LOAD DATA
# ==================================================

print("=" * 60)
print("AKLM STALE-KNOWLEDGE / SELECTIVE REPLACEMENT MODEL")
print("=" * 60)

changes_df = pd.read_csv(
    LIFECYCLE_PATH / "changes.csv",
    dtype=str
)

chunks_df = pd.read_csv(
    LIFECYCLE_PATH / "chunk_changes.csv",
    dtype=str
)

print("\nLoaded datasets")
print(
    f"Page-level change events: {len(changes_df)}"
)
print(
    f"Chunk-level change records: {len(chunks_df)}"
)


# ==================================================
# DERIVED FEATURES
# ==================================================

def version_delta(v_from, v_to):
    return int(v_to[1:]) - int(v_from[1:])


changes_df["version_delta"] = [
    version_delta(a, b)
    for a, b in zip(
        changes_df["from_version"],
        changes_df["to_version"]
    )
]

chunks_df["version_delta"] = [
    version_delta(a, b)
    for a, b in zip(
        chunks_df["from_version"],
        chunks_df["to_version"]
    )
]

chunks_df = chunks_df.merge(
    changes_df[
        [
            "change_id",
            "pct_content_changed",
            "min_chunk_text_similarity"
        ]
    ],
    on="change_id",
    how="left"
)


# ==================================================
# MODEL 1 — PAGE LEVEL
# Does this page update require embedding refresh?
# ==================================================

print("\n" + "=" * 60)
print("PAGE-LEVEL MODEL")
print("=" * 60)

page_features = [
    "pct_content_changed",
    "min_chunk_text_similarity",
    "version_delta"
]

train_page = changes_df[
    changes_df["split"] == "train"
]

validation_page = changes_df[
    changes_df["split"] == "validation"
]

test_page = changes_df[
    changes_df["split"] == "test"
]

X_page_train = train_page[page_features].astype(float)
y_page_train = (train_page["embedding_affected"] == "yes").astype(int)

X_page_validation = validation_page[page_features].astype(float)
y_page_validation = (validation_page["embedding_affected"] == "yes").astype(int)

X_page_test = test_page[page_features].astype(float)
y_page_test = (test_page["embedding_affected"] == "yes").astype(int)

page_model = Pipeline(
    [
        ("scale", StandardScaler()),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced"
            )
        )
    ]
)

page_model.fit(
    X_page_train,
    y_page_train
)

page_pred_validation = page_model.predict(
    X_page_validation
)

print(
    f"\nValidation Accuracy: "
    f"{accuracy_score(y_page_validation, page_pred_validation):.4f}"
)

print(
    "\nClassification Report:\n"
)

print(
    classification_report(
        y_page_validation,
        page_pred_validation
    )
)

page_pred_test = page_model.predict(
    X_page_test
)

print(
    f"\nTest Accuracy: "
    f"{accuracy_score(y_page_test, page_pred_test):.4f}"
)

print(
    "\nClassification Report:\n"
)

print(
    classification_report(
        y_page_test,
        page_pred_test
    )
)

print(
    "\nConfusion Matrix (test):\n"
)

print(
    confusion_matrix(
        y_page_test,
        page_pred_test
    )
)

page_model_path = MODEL_DIR / "aklm_stale_detection_model.joblib"

joblib.dump(
    page_model,
    page_model_path
)

print(
    f"\nPage-level model saved to:\n{page_model_path}"
)


# ==================================================
# MODEL 2 — CHUNK LEVEL
# Should this specific chunk embedding be replaced?
# ==================================================

print("\n" + "=" * 60)
print("CHUNK-LEVEL MODEL")
print("=" * 60)

chunk_features = [
    "text_similarity",
    "status",
    "pct_content_changed",
    "min_chunk_text_similarity",
    "version_delta"
]

chunk_numeric_keys = [
    "text_similarity",
    "pct_content_changed",
    "min_chunk_text_similarity",
    "version_delta"
]

chunk_categorical_keys = [
    "status"
]

train_chunk = chunks_df[
    chunks_df["split"] == "train"
]

validation_chunk = chunks_df[
    chunks_df["split"] == "validation"
]

test_chunk = chunks_df[
    chunks_df["split"] == "test"
]

for frame in (
    train_chunk,
    validation_chunk,
    test_chunk
):

    for key in chunk_numeric_keys:

        frame[key] = pd.to_numeric(
            frame[key],
            errors="coerce"
        )

X_chunk_train = train_chunk[chunk_features]
y_chunk_train = (train_chunk["embedding_affected"] == "yes").astype(int)

X_chunk_validation = validation_chunk[chunk_features]
y_chunk_validation = (
    validation_chunk["embedding_affected"] == "yes"
).astype(int)

X_chunk_test = test_chunk[chunk_features]
y_chunk_test = (
    test_chunk["embedding_affected"] == "yes"
).astype(int)

chunk_preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            StandardScaler(),
            chunk_numeric_keys
        ),
        (
            "cat",
            OneHotEncoder(
                handle_unknown="ignore"
            ),
            chunk_categorical_keys
        )
    ]
)

chunk_model = Pipeline(
    [
        ("preprocess", chunk_preprocessor),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=200,
                random_state=42,
                class_weight="balanced"
            )
        )
    ]
)

chunk_model.fit(
    X_chunk_train,
    y_chunk_train
)

chunk_pred_validation = chunk_model.predict(
    X_chunk_validation
)

print(
    f"\nValidation Accuracy: "
    f"{accuracy_score(y_chunk_validation, chunk_pred_validation):.4f}"
)

print(
    "\nClassification Report:\n"
)

print(
    classification_report(
        y_chunk_validation,
        chunk_pred_validation
    )
)

chunk_pred_test = chunk_model.predict(
    X_chunk_test
)

print(
    f"\nTest Accuracy: "
    f"{accuracy_score(y_chunk_test, chunk_pred_test):.4f}"
)

print(
    "\nClassification Report:\n"
)

print(
    classification_report(
        y_chunk_test,
        chunk_pred_test
    )
)

print(
    "\nConfusion Matrix (test):\n"
)

print(
    confusion_matrix(
        y_chunk_test,
        chunk_pred_test
    )
)

chunk_model_path = MODEL_DIR / "aklm_chunk_replacement_model.joblib"

joblib.dump(
    chunk_model,
    chunk_model_path
)

print(
    f"\nChunk-level model saved to:\n{chunk_model_path}"
)


# ==================================================
# FEATURE IMPORTANCE
# ==================================================

print("\n" + "=" * 60)
print("FEATURE IMPORTANCE (CHUNK MODEL)")
print("=" * 60)

preprocessed_names = (
    chunk_numeric_keys
    + list(
        chunk_model.named_steps["preprocess"]
        .named_transformers_["cat"]
        .get_feature_names_out(chunk_categorical_keys)
    )
)

importances = chunk_model.named_steps[
    "classifier"
].feature_importances_

for name, importance in sorted(
    zip(preprocessed_names, importances),
    key=lambda item: item[1],
    reverse=True
):

    print(
        f"{name:<40} {importance:.4f}"
    )


# ==================================================
# RUNTIME DEMO
# ==================================================

print("\n" + "=" * 60)
print("RUNTIME DEMO — CHUNK REPLACEMENT DECISION")
print("=" * 60)

demo = pd.DataFrame(
    [
        {
            "text_similarity": 0.42,
            "status": "modified",
            "pct_content_changed": 60.0,
            "min_chunk_text_similarity": 0.31,
            "version_delta": 2
        }
    ]
)

demo_prediction = chunk_model.predict(demo)[0]
demo_probability = chunk_model.predict_proba(demo)[0]

print(
    f"\nDemo chunk (similarity=0.42, modified, page changed 60%):"
)

print(
    f"Prediction: "
    f"{'replacement needed' if demo_prediction == 1 else 'no replacement'}"
)

print(
    "\nConfidence:"
)

for cls, probability in zip(
    chunk_model.classes_,
    demo_probability
):

    print(
        f"class {cls} ("
        f"{'replace' if cls == 1 else 'keep'}): "
        f"{probability:.4f}"
    )

print("\nAKLM stale-detection training finished.")