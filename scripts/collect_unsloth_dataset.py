import json
import os
from pathlib import Path


def collect_trading_codebase(root_dir="."):
    """
    Collects code from src/ and strategies/ for fine-tuning.
    Filters out logs, data, and cache files.
    """
    dataset = []
    root = Path(root_dir)

    # Priority directories for specialization
    include_dirs = ["src", "config"]
    # Extensions to include
    include_exts = {".py", ".yaml", ".json", ".md", ".sh"}
    # Ignore patterns
    ignore_patterns = [
        "__pycache__",
        ".venv",
        ".git",
        "data",
        "logs",
        ".pytest_cache",
        ".ruff_cache",
    ]

    for include_dir in include_dirs:
        dir_path = root / include_dir
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*"):
            if any(p in path.parts for p in ignore_patterns):
                continue
            if path.suffix not in include_exts:
                continue
            if not path.is_file():
                continue

            try:
                content = path.read_text(encoding="utf-8")
                # Structure for fine-tuning: context + content
                dataset.append(
                    {
                        "instruction": f"Explain or implement logic for the trading system component: {path.relative_to(root)}",
                        "input": "",
                        "output": content,
                        "metadata": {"path": str(path.relative_to(root)), "type": path.suffix},
                    }
                )
            except Exception as e:
                print(f"Skipping {path}: {e}")

    return dataset


if __name__ == "__main__":
    print("🚀 Starting Dataset Collection for Unsloth Fine-tuning...")
    data = collect_trading_codebase()

    output_file = "data/ml_training_data/trading_specialization_dataset.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Collected {len(data)} code samples.")
    print(f"📂 Dataset saved to: {output_file}")
    print(
        "\nNext step: Run Unsloth fine-tuning on this dataset to create a specialized local model."
    )
