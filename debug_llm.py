"""Standalone diagnostic for the GRADEOPS LLM chain.

Walks every link from OS env → .env file → pydantic settings →
llm.get_llm() → an actual test API call. Prints exactly which step fails.

Run from the gradeops/ folder:
    python debug_llm.py
"""
import os
import sys
from pathlib import Path

print("=" * 60)
print("GRADEOPS LLM DIAGNOSTIC")
print("=" * 60)

# ---------- STEP 1: OS environment ----------
print("\n[1] os.environ check")
print("-" * 60)
key_in_env = "GOOGLE_API_KEY" in os.environ
print(f"  GOOGLE_API_KEY in os.environ : {key_in_env}")
if key_in_env:
    k = os.environ["GOOGLE_API_KEY"]
    print(f"  length                       : {len(k)}")
    print(f"  prefix                       : {k[:6]}")

# ---------- STEP 2: .env file ----------
print("\n[2] .env file check")
print("-" * 60)
env_file = Path(__file__).resolve().parent / ".env"
print(f"  Looking at  : {env_file}")
print(f"  Exists      : {env_file.exists()}")
if env_file.exists():
    try:
        content = env_file.read_text(encoding="utf-8-sig")
        for ln in content.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if "=" in ln:
                k, _, v = ln.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if "API_KEY" in k or k.upper() == "LLM_PROVIDER":
                    shown = (v[:6] + "...") if v else "(empty)"
                    print(f"    {k} = {shown}  (len {len(v)})")
    except Exception as e:
        print(f"  READ FAILED: {e}")

# ---------- STEP 3: backend.config.settings ----------
print("\n[3] backend.config.settings")
print("-" * 60)
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backend.config import settings
    print(f"  settings.llm_provider              : {settings.llm_provider}")
    gk = settings.google_api_key or ""
    print(f"  settings.google_api_key length     : {len(gk)}")
    print(f"  settings.google_api_key prefix     : {(gk[:6] + '...') if gk else '(empty)'}")
    print(f"  settings.grader_model_google       : {settings.grader_model_google}")
except Exception as e:
    print(f"  IMPORT FAILED: {e}")
    sys.exit(1)

# ---------- STEP 4: llm.get_llm() ----------
print("\n[4] backend.grader.llm.get_llm()")
print("-" * 60)
try:
    from backend.grader.llm import get_llm
    llm = get_llm()
    print(f"  LLM loaded : {type(llm).__name__}")
    print(f"  Model      : {getattr(llm, 'model', '?')}")
except Exception as e:
    print(f"  FAILED: {e}")
    print("\n  → fix this before going further.")
    sys.exit(2)

# ---------- STEP 5: actual API call ----------
print("\n[5] live API call (1 token, costs ~nothing)")
print("-" * 60)
try:
    from langchain_core.messages import HumanMessage
    resp = llm.invoke([HumanMessage(content="Reply with exactly the single word OK.")])
    text = resp.content if hasattr(resp, "content") else str(resp)
    print(f"  Response: {text!r}")
    print("\n  ✓ EVERYTHING WORKS. The pipeline should grade correctly.")
    print("  If the Review page still shows the old error, those crops are")
    print("  pre-fix DB rows — upload a new paper to verify.")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    print("\n  This is the actual API error. Common causes:")
    print("    - Invalid key  → regenerate at https://aistudio.google.com/app/apikey")
    print("    - Model name wrong → try gemini-1.5-flash or gemini-2.5-flash")
    print("    - Region restriction on the key")
    sys.exit(3)
