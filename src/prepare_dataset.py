"""
Build a JSON dataset that pairs daily news articles with stock percentage change,
using APIs directly (no CSV dependencies).

Output format:
[
  {
    "date": "2026-02-28",
    "percentage_increase": 2.5,
    "articles": ["Text1", "Text2"]
  }
]

usage ex:

python src/prepare_bert_dataset.py \
  --start-date 2026-02-01 \
  --end-date 2026-02-28 \
  --output data/news_with_percentage.json

"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yfinance as yf
import news_ingest


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc


def date_range(start: date, end: date) -> List[str]:
    days: List[str] = []
    cursor = start
    while cursor <= end:
        days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


def fetch_news_by_date(start: date, end: date) -> Dict[str, List[str]]:
    ingestor = news_ingest.NewsIngestor()
    result: Dict[str, List[str]] = {}

    for day in date_range(start, end):
        try:
            result[day] = ingestor.get_news_articles(day)
        except Exception as exc:
            print(f"Warning: news fetch failed for {day}: {exc}")
            result[day] = []

    return result


def fetch_price_changes(start: date, end: date, symbol: str) -> Dict[str, float]:
    """
    Fetch open/close price for [start, end] and compute same-day percentage change.
    """
    # yfinance end is exclusive; add one day so the requested end date is included.
    fetch_end = (end + timedelta(days=1)).isoformat()
    data = yf.download([symbol], start=start.isoformat(), end=fetch_end, progress=False)
    if data.empty:
        return {}

    if getattr(data.columns, "nlevels", 1) > 1:
        open_block = data["Open"]
        close_block = data["Close"]
        if symbol in open_block.columns:
            open_series = open_block[symbol]
            close_series = close_block[symbol]
        else:
            open_series = open_block.iloc[:, 0]
            close_series = close_block.iloc[:, 0]
    else:
        open_series = data["Open"]
        close_series = data["Close"]

    changes: Dict[str, float] = {}
    for idx, open_price, close_price in zip(data.index, open_series, close_series):
        try:
            open_value = float(open_price)
            close_value = float(close_price)
        except Exception:
            continue
        if open_value == 0:
            continue

        changes[idx.strftime("%Y-%m-%d")] = ((close_value - open_value) / open_value) * 100.0

    return changes


def next_available_trading_day(news_date: str, trading_days: List[str]) -> Optional[str]:
    for trading_day in trading_days:
        if trading_day >= news_date:
            return trading_day
    return None


def build_records(
    start: date,
    end: date,
    news_by_date: Dict[str, List[str]],
    price_by_date: Dict[str, float],
) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    trading_days = sorted(price_by_date.keys())

    for day in date_range(start, end):
        pct_value = price_by_date.get(day)
        if pct_value is None:
            mapped_day = next_available_trading_day(day, trading_days)
            if mapped_day is not None:
                pct_value = price_by_date.get(mapped_day)

        records.append(
            {
                "date": day,
                "percentage_increase": None if pct_value is None else round(pct_value, 6),
                "articles": news_by_date.get(day, []),
            }
        )

    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build JSON with {date, percentage_increase, articles} from API data for a date range."
    )
    parser.add_argument("--start-date", type=parse_date, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=parse_date, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default="VGT", help="Ticker for price change (default: VGT)")
    parser.add_argument("--output", type=Path, default=Path("data/news_with_percentage.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.start_date > args.end_date:
        raise ValueError("start-date must be <= end-date")

    news_by_date = fetch_news_by_date(args.start_date, args.end_date)

    try:
        price_by_date = fetch_price_changes(args.start_date, args.end_date, args.symbol)
    except Exception as exc:
        print(f"Warning: price fetch failed: {exc}")
        price_by_date = {}

    records = build_records(args.start_date, args.end_date, news_by_date, price_by_date)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(records)} days to {args.output}")


if __name__ == "__main__":
    main()
