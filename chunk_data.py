"""
Step 2 - Chunk.

Thin wrapper around aklm_lib.build_chunks. The actual implementation lives in
aklm_lib (shared with run_pipeline.py).
"""

import aklm_lib


print("=" * 40)
print("AKLM STEP 2: CHUNK")
print("=" * 40)

chunks = aklm_lib.build_chunks()

if not chunks:
    raise SystemExit("No chunks were produced.")

print("\nFirst chunk preview:")
print("-" * 40)
print(chunks[0]["text"])
print("-" * 40)
