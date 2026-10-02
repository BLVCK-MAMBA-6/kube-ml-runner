import json
import os
import sys

MODEL_PATH = "/models/model.json"
DATA_PATH = "/data/input.jsonl"
OUTPUT_PATH = "/output/predictions.jsonl"

def load_model():
    with open(MODEL_PATH) as f:
        return json.load(f)

def run_inference(model, record):
    # Toy "inference": look up the answer in the model
    question = record["question"]
    return {
        "question": question,
        "prediction": model.get(question, "unknown"),
    }

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: model not found at {MODEL_PATH}", file=sys.stderr)
        sys.exit(1)

    model = load_model()
    print(f"Loaded model with {len(model)} entries")

    with open(DATA_PATH) as f:
        records = [json.loads(line) for line in f if line.strip()]

    print(f"Processing {len(records)} records")

    with open(OUTPUT_PATH, "w") as f:
        for record in records:
            result = run_inference(model, record)
            f.write(json.dumps(result) + "\n")

    print(f"Wrote {len(records)} predictions to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()