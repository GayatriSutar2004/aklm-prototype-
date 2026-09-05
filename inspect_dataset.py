from pathlib import Path
import pandas as pd
import json


DATASET_PATH = Path(
    "Dataset/AKLM_FINAL_v3_FINAL"
)


def inspect_csv(file_path):

    print("\n" + "=" * 70)
    print(f"FILE: {file_path}")
    print("=" * 70)

    df = pd.read_csv(file_path)

    print(f"\nRows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    print("\nCOLUMN NAMES:")

    for column in df.columns:
        print(f" - {column}")

    print("\nDATA TYPES:")
    print(df.dtypes)

    print("\nFIRST 5 ROWS:")
    print(df.head().to_string())

    print("\nMISSING VALUES:")
    print(df.isnull().sum())

    print("\nUNIQUE VALUES (small columns):")

    for column in df.columns:

        unique_count = df[column].nunique()

        if unique_count <= 20:

            print(f"\n{column}:")
            print(df[column].value_counts(dropna=False))


files_to_check = [

    DATASET_PATH / "splits" / "train.csv",
    DATASET_PATH / "splits" / "validation.csv",
    DATASET_PATH / "splits" / "test.csv",

    DATASET_PATH / "lifecycle" / "changes.csv",
    DATASET_PATH / "lifecycle" / "version_lineage.csv",

    DATASET_PATH / "evaluation" / "stale_cases.csv",
    DATASET_PATH / "evaluation" / "conflict_cases.csv",
    DATASET_PATH / "evaluation" / "questions.csv",
]


print("\n")
print("=" * 70)
print("AKLM DATASET INSPECTION")
print("=" * 70)


for file_path in files_to_check:

    if file_path.exists():

        inspect_csv(file_path)

    else:

        print(f"\n❌ FILE NOT FOUND: {file_path}")


# ==========================================
# Inspect dataset manifest
# ==========================================

manifest_path = (
    DATASET_PATH / "dataset_manifest.json"
)


if manifest_path.exists():

    print("\n" + "=" * 70)
    print("DATASET MANIFEST")
    print("=" * 70)

    with open(
        manifest_path,
        "r",
        encoding="utf-8"
    ) as f:

        manifest = json.load(f)

    print(
        json.dumps(
            manifest,
            indent=2
        )
    )


print("\n")
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)
