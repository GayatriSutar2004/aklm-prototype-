import os
import subprocess
import sys
from pathlib import Path

# ==================================================
# CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parent

DATASET_CHECK = ROOT / (
    "Dataset/AKLM_FINAL_v3_FINAL/rag/chunks.csv"
)

# ==================================================
# HELPERS
# ==================================================

def run_step(script_name):

    print("\n" + "=" * 60)

    print(f"STEP: {script_name}")

    print("=" * 60)

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, str(ROOT / script_name)],
        cwd=str(ROOT),
        env=env
    )

    if result.returncode != 0:

        print(
            f"\nFAILED at {script_name}"
            f" (exit code {result.returncode})"
        )

        sys.exit(result.returncode)

    print(f"\nPASSED: {script_name}")


# ==================================================
# BUILD
# ==================================================

print("=" * 60)

print("AKLM INDEX BUILD")

print("=" * 60)

if not DATASET_CHECK.exists():

    print(
        "\nERROR: benchmark dataset not found at:\n"
        f"{DATASET_CHECK}"
    )

    print(
        "\nMake sure 'Dataset/AKLM_FINAL_v3_FINAL' is "
        "present before building the index."
    )

    sys.exit(1)

if not (ROOT / "chunks.json").exists():

    print(
        "\nSKIP create_embeddings: "
        "chunks.json (production scrape) not present"
    )

else:

    run_step("create_embeddings.py")

run_step("store_embeddings.py")

run_step("apply_replacements.py")

print("\n" + "=" * 60)

print("INDEX BUILD COMPLETE")

print("=" * 60)

print(
    "\nThe local Qdrant index is ready."
)

print(
    "\nRun 'retrieve.py' or 'generate_answer.py' "
    "to try it."
)

print("=" * 60)