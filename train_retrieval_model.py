import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

import joblib
from pathlib import Path


# ==================================================
# CONFIGURATION
# ==================================================

DATASET_PATH = Path(
    "Dataset/AKLM_FINAL_v3_FINAL/splits"
)

MODEL_DIR = Path("models")

MODEL_DIR.mkdir(
    exist_ok=True
)


# ==================================================
# LOAD DATA
# ==================================================

print("=" * 60)
print("AKLM RETRIEVAL DECISION MODEL")
print("=" * 60)


print("\nLoading datasets...")


train_df = pd.read_csv(
    DATASET_PATH / "train.csv"
)

validation_df = pd.read_csv(
    DATASET_PATH / "validation.csv"
)

test_df = pd.read_csv(
    DATASET_PATH / "test.csv"
)


print("✅ Datasets loaded")

print("\nDataset sizes:")

print(
    f"Training   : {len(train_df)}"
)

print(
    f"Validation : {len(validation_df)}"
)

print(
    f"Test       : {len(test_df)}"
)


# ==================================================
# PREPARE FEATURES AND LABELS
# ==================================================

X_train = train_df["question"]

y_train = train_df["retrieval_label"]


X_validation = validation_df["question"]

y_validation = validation_df["retrieval_label"]


X_test = test_df["question"]

y_test = test_df["retrieval_label"]


# ==================================================
# CREATE MACHINE LEARNING PIPELINE
# ==================================================

print("\nCreating ML pipeline...")


model = Pipeline(

    [

        (
            "tfidf",

            TfidfVectorizer(

                max_features=10000,

                ngram_range=(1, 2),

                stop_words="english"

            )

        ),

        (

            "classifier",

            LogisticRegression(

                max_iter=2000,

                class_weight="balanced",

                random_state=42

            )

        )

    ]

)


print("✅ Pipeline created")


# ==================================================
# TRAIN MODEL
# ==================================================

print("\nTraining model...")


model.fit(
    X_train,
    y_train
)


print("✅ Training completed")


# ==================================================
# VALIDATION EVALUATION
# ==================================================

print("\n" + "=" * 60)

print("VALIDATION RESULTS")

print("=" * 60)


validation_predictions = model.predict(
    X_validation
)


validation_accuracy = accuracy_score(

    y_validation,

    validation_predictions

)


print(

    f"\nValidation Accuracy: "

    f"{validation_accuracy:.4f}"

)


print(

    "\nClassification Report:\n"

)


print(

    classification_report(

        y_validation,

        validation_predictions

    )

)


print(

    "\nConfusion Matrix:\n"

)


print(

    confusion_matrix(

        y_validation,

        validation_predictions

    )

)


# ==================================================
# TEST EVALUATION
# ==================================================

print("\n" + "=" * 60)

print("TEST RESULTS")

print("=" * 60)


test_predictions = model.predict(
    X_test
)


test_accuracy = accuracy_score(

    y_test,

    test_predictions

)


print(

    f"\nTest Accuracy: "

    f"{test_accuracy:.4f}"

)


print(

    "\nClassification Report:\n"

)


print(

    classification_report(

        y_test,

        test_predictions

    )

)


print(

    "\nConfusion Matrix:\n"

)


print(

    confusion_matrix(

        y_test,

        test_predictions

    )

)


# ==================================================
# SAVE MODEL
# ==================================================

model_path = MODEL_DIR / "aklm_retrieval_model.joblib"


joblib.dump(

    model,

    model_path

)


print("\n" + "=" * 60)

print("MODEL SAVED")

print("=" * 60)


print(

    f"\nModel saved to:\n{model_path}"

)


# ==================================================
# TEST CUSTOM QUESTIONS
# ==================================================

print("\n" + "=" * 60)

print("CUSTOM QUESTION TEST")

print("=" * 60)


while True:

    question = input(

        "\nAsk a question "

        "(or type 'exit'):\n> "

    )


    if question.lower() == "exit":

        break


    prediction = model.predict(

        [question]

    )[0]


    probabilities = model.predict_proba(

        [question]

    )[0]


    classes = model.classes_


    print(

        "\nAKLM DECISION:"

    )


    print(

        f"Prediction: {prediction}"

    )


    print(

        "\nConfidence:"

    )


    for label, probability in zip(

        classes,

        probabilities

    ):

        print(

            f"{label}: "

            f"{probability:.4f}"

        )


print("\nAKLM model testing finished.")
