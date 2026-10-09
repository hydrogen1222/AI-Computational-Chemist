#!/usr/bin/env python3
"""Slide-size DDEC6 charts from batch_ddec6.py CSV tables.

Requires matplotlib (only for plotting); writes vector SVG and 300-dpi PNG.
All figures are descriptive, showing means AND atom/bond ranges.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re


def args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path, help="Folder containing ddec6_elements.csv and ddec6_bond_types.csv")
    p.add_argument("--case", help="Plot one case instead of every case")
    p.add_argument("--max-cases", type=int, default=20,
                   help="Safety limit, default 20; 0 means all cases")
    return p.parse_args(argv)


def rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def safe_name(case):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", case).strip("._")[:80] or "root"


def chart(matplotlib, folder, case, data, charge):
    if not data:
        return
    import matplotlib.pyplot as plt

    if charge:
        title = "DDEC6 atomic net charge"
        subtitle = "Mean and atomic min–max range | +q = electron-deficient"
        ylabel, label_col = "Net atomic charge q (e)", "element"
        val, mini, maxi = "mean_charge_e", "min_charge_e", "max_charge_e"
        suffix = "charges"
    else:
        title = "DDEC6 pair bond order"
        subtitle = "Mean and printed bond min–max range | periodic images counted once"
        ylabel, label_col = "DDEC6 bond order (dimensionless)", "element_pair"
        val, mini, maxi = "mean_bond_order", "min_bond_order", "max_bond_order"
        suffix = "bond_orders"
    data = sorted(data, key=lambda x: x[label_col])
    labels = [x[label_col] for x in data]
    means = [float(x[val]) for x in data]
    error = [[max(0, means[i]-float(x[mini])) for i,x in enumerate(data)],
             [max(0, float(x[maxi])-means[i]) for i,x in enumerate(data)]]
    fig, ax = plt.subplots(figsize=(12.8, 7.2), constrained_layout=True)
    positions = list(range(len(data)))
    ax.bar(positions, means, alpha=0.85)
    ax.errorbar(positions, means, yerr=error, capsize=4, fmt="none", color="black", linewidth=1.1)
    ax.axhline(0, color="black", alpha=0.4, linewidth=0.8)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=25 if len(labels)>5 else 0, ha="right" if len(labels)>5 else "center")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} — {case}\n{subtitle}", loc="left", fontsize=16, pad=20)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.text(0.99, -0.12, "Source: Chargemol DDEC6 | error bars: min–max, not statistical uncertainty",
            transform=ax.transAxes, ha="right", va="top", fontsize=9)
    stem = folder / f"{safe_name(case)}_{suffix}"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    opt = args(argv)
    if not opt.summary.is_dir() or opt.max_cases < 0:
        raise SystemExit("summary directory missing or invalid max-cases")
    try:
        import matplotlib  # noqa: F401
    except ImportError as e:
        raise SystemExit("matplotlib is required for PNG/SVG; install it into your analysis environment") from e
    try:
        charges = rows(opt.summary / "ddec6_elements.csv")
        bonds = rows(opt.summary / "ddec6_bond_types.csv")
    except FileNotFoundError as e:
        raise SystemExit(f"missing batch CSV: {e}") from e
    cases = sorted(set(x["case"] for x in charges) | set(x["case"] for x in bonds))
    if opt.case is not None:
        if opt.case not in cases:
            raise SystemExit(f"unknown case {opt.case!r}")
        cases = [opt.case]
    elif opt.max_cases:
        if len(cases) > opt.max_cases:
            print(f"NOTE: {len(cases)} cases, plotting first {opt.max_cases}; use --max-cases 0 for all")
        cases = cases[:opt.max_cases]
    dest = opt.summary / "ppt_figures"
    dest.mkdir(exist_ok=True)
    for case in cases:
        chart(None, dest, case, [x for x in charges if x["case"] == case], True)
        chart(None, dest, case, [x for x in bonds if x["case"] == case], False)
    print(f"Created up to {len(cases)*2} SVG/PNG figure pairs in {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
