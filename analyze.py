"""
Lab 11 — Data Visualization for the Smart Wastebin
analyze.py: Loads JSONL event data and generates 7 analytical charts using Seaborn.
"""

import json
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ── Global config 

sns.set_theme(style="whitegrid")

CHARTS_DIR = "charts"
os.makedirs(CHARTS_DIR, exist_ok=True)


# ── Data loading 

def load_events(filepath: str) -> pd.DataFrame:
    
    records = []

    with open(filepath, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip malformed lines silently

    df = pd.DataFrame(records)

    # Normalise timestamp
    if "timestamp_utc" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    elif "resultTime" in df.columns:
        df["timestamp"] = pd.to_datetime(df["resultTime"], utc=True, errors="coerce")
    elif "event_time" in df.columns:
        df["timestamp"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")

    if "timestamp" in df.columns:
        df["hour"]        = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.day_name()
        df["date"]        = df["timestamp"].dt.date
        df["minute"]      = df["timestamp"].dt.minute

    return df


# Chart 1 — Events per hour (bar chart) 

def plot_events_per_hour(df: pd.DataFrame) -> None:
    
    hourly = (
        df.groupby("hour")
        .size()
        .reset_index(name="event_count")
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=hourly, x="hour", y="event_count", color="steelblue", ax=ax)

    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Number of Events")
    ax.set_title("Motion Events by Hour of Day")

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "events_per_hour.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")


# Chart 2 — Latency distribution (histogram + KDE)

def plot_latency_distribution(df: pd.DataFrame) -> None:

    if "pipeline_latency_ms" not in df.columns:
        print("  ⚠  Skipping latency_distribution — column 'pipeline_latency_ms' not found.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(data=df, x="pipeline_latency_ms", kde=True, color="seagreen", ax=ax)

    ax.set_xlabel("Pipeline Latency (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Pipeline Latency")

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "latency_distribution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")


# Chart 3 — Events over time (line chart)

def plot_events_over_time(df: pd.DataFrame) -> None:

    daily = (
        df.groupby("date")
        .size()
        .reset_index(name="event_count")
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=daily, x="date", y="event_count",
        marker="o", color="orangered", ax=ax
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Events")
    ax.set_title("Daily Motion Events Over Time")
    plt.xticks(rotation=45)

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "events_over_time.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")


#  Chart 4 — Heatmap: hour × day of week 

def plot_heatmap(df: pd.DataFrame) -> None:

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    pivot_raw = (
        df.groupby(["day_of_week", "hour"])
        .size()
        .reset_index(name="count")
    )

    pivot_table = pivot_raw.pivot(index="day_of_week", columns="hour", values="count")
    pivot_table = pivot_table.fillna(0)
    pivot_table = pivot_table.reindex(
        [d for d in day_order if d in pivot_table.index]
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(
        pivot_table,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        ax=ax
    )

    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("")
    ax.set_title("Motion Events: Hour × Day of Week")

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "heatmap_hour_day.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")


# Chart 5 — Latency over time (scatter plot) 

def plot_latency_over_time(df: pd.DataFrame) -> None:

    if "pipeline_latency_ms" not in df.columns or "timestamp" not in df.columns:
        print("  ⚠  Skipping latency_over_time — required columns not found.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(
        df["timestamp"], df["pipeline_latency_ms"],
        alpha=0.5, s=15, color="purple"
    )

    ax.set_xlabel("Time")
    ax.set_ylabel("Pipeline Latency (ms)")
    ax.set_title("Pipeline Latency Over Time")
    plt.xticks(rotation=45)

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "latency_over_time.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")


# Chart 6 — Latency box plot per hour (EXTRA) 

def plot_latency_boxplot_per_hour(df: pd.DataFrame) -> None:

    if "pipeline_latency_ms" not in df.columns or "hour" not in df.columns:
        print("  ⚠  Skipping latency_boxplot_per_hour — required columns not found.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.boxplot(
        data=df, x="hour", y="pipeline_latency_ms",
        palette="coolwarm", ax=ax
    )

    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Pipeline Latency (ms)")
    ax.set_title("Pipeline Latency Distribution per Hour")

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "latency_boxplot_per_hour.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  ✓  Saved {path}")




# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/events.jsonl"

    print(f"\n📂  Loading events from: {filepath}")
    df = load_events(filepath)
    print(f"    {len(df)} events loaded.\n")

    if df.empty:
        print("❌  No data found. Run your pipeline first to generate the JSONL log.")
        sys.exit(1)

    print("📊  Generating charts …\n")
    plot_events_per_hour(df)          # Chart 1
    plot_latency_distribution(df)     # Chart 2
    plot_events_over_time(df)         # Chart 3
    plot_heatmap(df)                  # Chart 4
    plot_latency_over_time(df)        # Chart 5
    plot_latency_boxplot_per_hour(df) # Chart 6 (extra)

    print(f"\n✅  All charts saved to '{CHARTS_DIR}/'")