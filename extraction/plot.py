"""Draw results/accuracy_by_field.png from results/metrics.json (k=16).

    pip install matplotlib && python -m extraction.plot
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
LABELS = {"net_income": "Net income", "total_assets": "Total assets", "diluted_eps": "Diluted EPS",
          "cash": "Cash and equivalents", "equity": "Shareholders' equity", "revenue": "Revenue"}
INK, MUTED, ACCENT, PAPER = "#1a1916", "#6a655c", "#b8461b", "#fbf9f4"


def main() -> None:
    k16 = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))["k16"]
    fields = sorted(k16["by_field"], key=lambda f: k16["by_field"][f]["accuracy"])
    acc = [k16["by_field"][f]["accuracy"] * 100 for f in fields]
    counts = [round(k16["by_field"][f]["accuracy"] * k16["by_field"][f]["n"]) for f in fields]
    totals = [k16["by_field"][f]["n"] for f in fields]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.barh([LABELS[f] for f in fields], acc, height=0.42, color=ACCENT)
    for y, (a, c, t) in enumerate(zip(acc, counts, totals)):
        ax.text(a + 1, y, f"{c}/{t}", va="center", fontsize=10, color=INK)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Correct values, % (within 0.5% of the XBRL figure)", color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=10, length=0)
    ax.tick_params(axis="y", colors=INK)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#d9d5cc")
    ax.grid(axis="x", color="#e6e2d9", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(f"LLM reading 39 SEC 10-K filings: {k16['overall']['accuracy'] * 100:.1f}% of 220 values correct",
                 loc="left", fontsize=12, color=INK, pad=14)
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "accuracy_by_field.png", facecolor=PAPER)


if __name__ == "__main__":
    main()
