import argparse
import csv
import json
import math
import random
from pathlib import Path
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse news_with_percentage.json into shuffled row-level train/test/validate CSV files."
    )
    parser.add_argument("--input", type=Path, default=Path("data/news_with_percentage.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/split_dataset"))
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--validate-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def validate_ratios(train_ratio: float, test_ratio: float, validate_ratio: float) -> None:
    if min(train_ratio, test_ratio, validate_ratio) <= 0:
        raise ValueError("train-ratio, test-ratio, and validate-ratio must all be > 0")

    total = train_ratio + test_ratio + validate_ratio
    if abs(total - 1.0) > 1e-9:
        raise ValueError(
            f"Ratios must sum to 1.0, got {total:.6f}"
        )


def parse_rows(input_path: Path) -> List[Tuple[str, str, int, str, float]]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Input JSON must be a list")

    rows: List[Tuple[str, str, int, str, float]] = []

    for day in payload:
        date = str(day.get("date", "")).strip()
        if not date:
            continue

        pct = day.get("percentage_increase")
        if pct is None:
            continue

        try:
            pct_float = float(pct)
        except (TypeError, ValueError):
            continue

        label = 1 if pct_float > 0 else 0

        articles = day.get("articles") or []
        if not isinstance(articles, list):
            continue

        for article in articles:
            text = str(article or "").strip()
            if not text:
                continue

            rows.append((text, label, date, pct_float))

    return rows


def split_rows(
    rows: List[Tuple[str, int, str, float]],
    train_ratio: float,
    test_ratio: float,
) -> Tuple[List[Tuple[str, int, str, float]], List[Tuple[str, int, str, float]], List[Tuple[str, int, str, float]]]:
    n = len(rows)
    if n < 3:
        raise ValueError("Need at least 3 rows to split into train/test/validate")

    train_n = int(math.floor(n * train_ratio))
    test_n = int(math.floor(n * test_ratio))
    validate_n = n - train_n - test_n

    if train_n == 0 or test_n == 0 or validate_n == 0:
        raise ValueError(
            "Split resulted in an empty partition. Increase dataset size or adjust ratios."
        )

    train_rows = rows[:train_n]
    test_rows = rows[train_n : train_n + test_n]
    validate_rows = rows[train_n + test_n :]

    return train_rows, test_rows, validate_rows


def write_csv(path: Path, rows: List[Tuple[str, int, str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Keep the exact requested format with two text columns.
        writer.writerow(["text", "label", "date", "percentage_increase"])
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    validate_ratios(args.train_ratio, args.test_ratio, args.validate_ratio)

    rows = parse_rows(args.input)
    if not rows:
        raise ValueError("No valid rows parsed from input JSON")

    random.Random(args.seed).shuffle(rows)

    train_rows, test_rows, validate_rows = split_rows(rows, args.train_ratio, args.test_ratio)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "train.csv", train_rows)
    write_csv(args.output_dir / "test.csv", test_rows)
    write_csv(args.output_dir / "validate.csv", validate_rows)

    print(
        f"Wrote randomized splits to {args.output_dir} | "
        f"train={len(train_rows)}, test={len(test_rows)}, validate={len(validate_rows)}"
    )


if __name__ == "__main__":
    main()
