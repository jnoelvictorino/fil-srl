import json
import requests
import dspy
from typing import List, Literal, Dict, Any
from pydantic import BaseModel, Field

# =====================================================================
# DIVISION 1: CONFIGURATION & UNIFIED DATA LOADER
# =====================================================================
DATASAUR_FILE_PATH = "/workspaces/fil-srl/data/sample.json"  # Update with your path
OLLAMA_MODEL_TAG = "qwen3.6:35b"
OLLAMA_URL = "http://localhost:11434"


def load_and_parse_datasaur(filepath: str) -> Dict[str, Any]:
  """Parses JSON, extracts the dynamic taxonomy, and maps verb->argument arrows."""
  with open(filepath, "r", encoding="utf-8") as file:
    raw_data = json.load(file)

  payload = raw_data["data"]

  # Extract complete dynamic taxonomy from codebook
  fil_srl_labels = [
    label["labelName"] for label in payload["labelSets"][0]["labelItems"]
  ]

  verb_tags = [
    l
    for l in fil_srl_labels
    if l.startswith("REL-VRB-")
    or l in ["REL-ADJ", "REL-NOM", "REL-EXT", "REL-MOD", "REL-PREP"]
  ]
  arg_tags = [l for l in fil_srl_labels if l not in verb_tags]

  tasks = []

  # Loop through all rows/sentences dynamically
  for row_id, row_data in enumerate(payload.get("rows", [])):
    row_zero_object = row_data[0]
    sentence_text = row_zero_object["content"]
    row_tokens = row_zero_object["tokens"]

    all_spans_by_id = {}
    row_predicates = []

    for span in payload.get("spanLabels", []):
      if span["textPosition"]["start"]["row"] == row_id:
        span_id = span["id"]
        all_spans_by_id[span_id] = span
        role_label = span["labelItem"]["labelName"]

        start_idx = span["textPosition"]["start"]["tokenIndex"]
        end_idx = span["textPosition"]["end"]["tokenIndex"]
        raw_token_string = " ".join(row_tokens[start_idx : end_idx + 1]).strip()

        if role_label in verb_tags:
          row_predicates.append({
            "span_id": span_id,
            "verb_text": raw_token_string,
            "tag": role_label,
          })

    for pred in row_predicates:
      valid_argument_ids = {
        arrow["originId"]
        for arrow in payload.get("arrowLabels", [])
        if str(arrow["destinationId"]) == str(pred["span_id"])
      }

      ground_truth = []
      for arg_id in valid_argument_ids:
        if span := all_spans_by_id.get(arg_id):
          arg_start = span["textPosition"]["start"]["tokenIndex"]
          arg_end = span["textPosition"]["end"]["tokenIndex"]
          arg_text = " ".join(row_tokens[arg_start : arg_end + 1])
          ground_truth.append({
            "role": span["labelItem"]["labelName"],
            "text": arg_text,
            "start_idx": arg_start,
          })

      tasks.append({
        "sentence": sentence_text,
        "target_verb": pred["verb_text"],
        "verb_tag": pred["tag"],
        "ground_truth": sorted(ground_truth, key=lambda x: x["start_idx"]),
      })

  return {"verb_tags": verb_tags, "arg_tags": arg_tags, "tasks": tasks}


dataset_info = load_and_parse_datasaur(DATASAUR_FILE_PATH)
EVALUATION_TASKS = dataset_info["tasks"]
VALID_ARG_ROLES = dataset_info["arg_tags"]
FilSrlRoles = Literal[tuple(VALID_ARG_ROLES)]

print(f"✅ Data Loaded. Found {len(EVALUATION_TASKS)} predicate tasks.")


# =====================================================================
# DIVISION 2: DSPY PIPELINE SETUP
# =====================================================================
class SemanticArgument(BaseModel):
  role: FilSrlRoles = Field(
    description="The exact categorical semantic role from your codebook."
  )
  text: str = Field(
    description="The exact phrase copied character-for-character from the sentence."
  )


class TagalogSRL(dspy.Signature):
  """Suriin ang buong pangungusap at kunin (extract) ang mga semantic argument role na nakadepende LAMANG sa ibinigay na Target na Pandiwa (Target Verb)."""

  sentence: str = dspy.InputField()
  target_verb: str = dspy.InputField()
  extracted_arguments: List[SemanticArgument] = dspy.OutputField()


lm = dspy.LM(
  f"ollama_chat/{OLLAMA_MODEL_TAG}",
  api_base=OLLAMA_URL,
  api_key="",
  temperature=0.0,
  cache=False,
)
dspy.settings.configure(lm=lm)
dspy_predictor = dspy.ChainOfThought(TagalogSRL)

# =====================================================================
# DIVISION 3: PURE ZERO-SHOT PIPELINE SETUP
# =====================================================================
ZERO_SHOT_PROMPT = f"""Ikaw ay isang linguistic parser para sa Filipino SRL.
Tungkulin mo: Tukuyin ang mga arguments na nakadepende LAMANG sa Target na Pandiwa.

PATAKARAN:
1. BAWAL MAG-IMBENTO NG ROLES. Gamitin lamang ang mga ito: {VALID_ARG_ROLES}
2. I-extract ang eksaktong text nang walang dagdag na bantas.

Ibalik ang sagot STRICTLY bilang raw JSON list tulad nito:
[
  {{"role": "ARG1", "text": "eksaktong salita"}}
]
"""


def run_pure_zero_shot(sentence: str, target_verb: str) -> List[Dict]:
  payload = {
    "model": OLLAMA_MODEL_TAG,
    "prompt": f"{ZERO_SHOT_PROMPT}\n\nPangungusap: {sentence}\nTarget na Pandiwa: {target_verb}",
    "stream": False,
    "options": {"temperature": 0.0},
  }
  response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload).json()
  raw_text = response.get("response", "").strip()

  # Strip markdown logic
  if raw_text.startswith("```"):
    raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
  if raw_text.lower().startswith("json"):
    raw_text = raw_text[4:].strip()

  try:
    return json.loads(raw_text)
  except json.JSONDecodeError:
    return []


# =====================================================================
# DIVISION 4: TWIN CHRONOLOGICAL TABLES EVALUATION MATRIX
# =====================================================================
def normalize_text(text: str) -> str:
  """Removes all spaces and standardizes case to prevent tokenization spacing mismatches."""
  if not text:
    return ""
  return text.replace(" ", "").lower()


def evaluate_pipeline(pipeline_name: str, get_predictions_func):
  print(f"\n\n{'=' * 125}\n🚀 RUNNING PIPELINE: {pipeline_name}\n{'=' * 125}")

  for task in EVALUATION_TASKS:
    sentence = task["sentence"]
    target_action = task["target_verb"]
    verb_tag = task["verb_tag"]
    datasaur_ground_truth = task["ground_truth"]

    print(
      f"\n{'-' * 125}\n🔹 SENTENCE: {sentence}\n🔹 TARGET VERB: {target_action} ({verb_tag})\n{'-' * 125}"
    )

    print(
      f"\n🎯 EXECUTING TASK: Evaluating arguments for Predicate -> '{target_action}'"
    )

    # 1. Get Predictions from the requested pipeline
    predictions = get_predictions_func(sentence, target_action)

    def get_token_start_index(text_span: str) -> int:
      norm_span = normalize_text(text_span)
      norm_sentence = normalize_text(sentence)
      if norm_span and norm_span in norm_sentence:
        return norm_sentence.index(norm_span)
      return 999

    # Sort predicted outputs from left-to-right linearly
    ordered_predictions = sorted(
      predictions, key=lambda x: get_token_start_index(x.get("text", ""))
    )

    # -----------------------------------------------------------------
    # TABLE 1: DATASAUR GROUND TRUTH BASELINE
    # -----------------------------------------------------------------
    chronological_baseline = list(datasaur_ground_truth)
    chronological_baseline.append({
      "role": f"⭐ {verb_tag} (TARGET)",
      "text": target_action,
      "is_predicate": True,
    })

    # Sort the combined list chronologically
    chronological_baseline = sorted(
      chronological_baseline, key=lambda x: get_token_start_index(x["text"])
    )

    print("\n" + "=" * 125)
    print(f"📋 TABLE 1: ARROW-FILTERED DATASAUR BASELINE (Chronological Sentence Flow)")
    print("=" * 125)
    print(
      f"{'Actual SRL Role':<25} | {'Ground Truth Text Span':<60} | Prediction Alignment Status"
    )
    print("-" * 125)

    for item in chronological_baseline:
      role = item["role"]
      actual_text = item["text"]

      if item.get("is_predicate"):
        print(f"{role:<25} | {actual_text:<60} | 🔵 TARGET PREDICATE ANCHOR")
        continue

      match_found = False
      matched_text = ""
      for pred in ordered_predictions:
        if pred.get("role") == role and normalize_text(
          pred.get("text", "")
        ) == normalize_text(actual_text):
          match_found = True
          break
        elif pred.get("role") == role:
          matched_text = pred.get("text", "")

      if match_found:
        status = "✅ EXACT MATCH"
      elif matched_text:
        status = f"⚠️ SPAN SHIFT (LLM got: '{matched_text[:25]}...')"
      else:
        status = "❌ OMITTED / MISSED BY LLM"

      print(f"{role:<25} | {actual_text:<60} | {status}")
    print("=" * 125)

    # -----------------------------------------------------------------
    # TABLE 2: LLM OUTPUT PROFILE
    # -----------------------------------------------------------------
    print("\n" + "=" * 125)
    print(f"🤖 TABLE 2: LOCAL OLLAMA INTERPRETATION PROFILE ({pipeline_name})")
    print("=" * 125)
    print(
      f"{'Predicted Role':<25} | {'LLM Extracted Verbatim Text Span':<60} | Ground Truth Validity"
    )
    print("-" * 125)

    for pred in ordered_predictions:
      p_role = pred.get("role", "UNKNOWN")
      p_text = pred.get("text", "[No text extracted]")

      exact_match_valid = any(
        item["role"] == p_role
        and normalize_text(item["text"]) == normalize_text(p_text)
        for item in datasaur_ground_truth
      )
      role_exists_elsewhere = any(
        item["role"] == p_role for item in datasaur_ground_truth
      )

      if exact_match_valid:
        validity = "✅ VALID MATCH WITH GROUND TRUTH"
      elif role_exists_elsewhere:
        validity = "⚠️ VARIANT SPAN BOUNDARY (Expected different textual coverage slice)"
      else:
        validity = "❌ MISPLACED/EXTRA SPAN (Not attached to this target)"

      print(f"{p_role:<25} | {p_text:<60} | {validity}")
    print("=" * 125)


# =====================================================================
# EXECUTION COMMANDS
# =====================================================================
# Wrapper for DSPy to match the unified format
def dspy_wrapper(sentence, target_verb):
  try:
    # We will also print raw output if possible, but catching the exact error is priority 1
    res = dspy_predictor(sentence=sentence, target_verb=target_verb)
    return [{"role": r.role, "text": r.text} for r in res.extracted_arguments]
  except Exception as e:
    # Expose the silent failure!
    print(f"\n🚨 [DSPY VALIDATION REJECTION]: The LLM output failed Pydantic parsing.")
    print(f"Error Details: {str(e)}\n")
    return []


# Run the benchmarks!
evaluate_pipeline("PURE ZERO-SHOT (Requests API)", run_pure_zero_shot)
evaluate_pipeline("DSPY ENGINE (Zero-Shot CoT)", dspy_wrapper)
