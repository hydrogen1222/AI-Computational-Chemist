#!/usr/bin/env python3
"""Create slide-ready DDEC6 summaries for EVERY reported bond type.

Requires matplotlib. Output: 16:9 editable-text SVG and 300-dpi PNG.
Long plots are paginated (all classes retained; no hidden top-N filtering).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re


def args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("summary", type=Path, help="Directory with ddec6_elements.csv and ddec6_bond_types.csv")
    p.add_argument("--case", help="Restrict to one case")
    p.add_argument("--max-cases", type=int, default=0,
                   help="Optional limit on models to chart (0, default = all)")
    p.add_argument("--items-per-figure", type=int, default=10,
                   help="Number of element/bond categories per slide; rest go on following pages")
    return p.parse_args(argv)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", name).strip("._")[:80] or "root"


def draw(folder, case, values, charge, page, pages):
    """One slide; caller paginates every category instead of truncating data."""
    import matplotlib.pyplot as plt

    plt.rcParams["svg.fonttype"] = "none"  # text remains editable in SVG
    label_key = "element" if charge else "element_pair"
    mean = "mean_charge_e" if charge else "mean_bond_order"
    low = "min_charge_e" if charge else "min_bond_order"
    high = "max_charge_e" if charge else "max_bond_order"
    count = "n_atoms" if charge else "n_periodic_bonds"
    suffix = "charges" if charge else "bond_orders"
    title = "DDEC6 net atomic charge" if charge else "DDEC6 pair bond order"
    unit = "Net atomic charge q (e)" if charge else "DDEC6 bond order (dimensionless)"
    subtitle = ("+q denotes electron depletion" if charge else
                "All Chargemol-printed pair classes; each periodic image counted once")
    labels = [f"{v[label_key]} (n={v[count]})" for v in values]
    means = [float(v[mean]) for v in values]
    bounds = [[max(0, m-float(v[low])) for m,v in zip(means,values)],
              [max(0, float(v[high])-m) for m,v in zip(means,values)]]
    fig, ax = plt.subplots(figsize=(12.8, 7.2), constrained_layout=True)
    positions = list(range(len(values)))
    ax.bar(positions, means)
    ax.errorbar(positions, means, yerr=bounds, fmt="none", capsize=4,
                color="black", linewidth=1)
    ax.axhline(0, linewidth=0.8, color="black", alpha=0.5)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=25 if len(labels)>5 else 0,
                       ha="right" if len(labels)>5 else "center")
    ax.set_ylabel(unit)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.set_title(f"{title} — {case}   [{page}/{pages}]\n{subtitle}",
                 loc="left", fontsize=15, pad=18)
    ax.text(0.99, -0.14,
            "Chargemol DDEC6 | min–max across atoms/printed bonds, NOT statistical error",
            transform=ax.transAxes, ha="right", va="top", fontsize=9)
    name = safe_name(case) + "_" + suffix + (f"_part{page:02d}" if page>1 else "")
    for ext, kwargs in ((".svg", {}), (".png", {"dpi": 300})):
        fig.savefig(folder / (name + ext), bbox_inches="tight", **kwargs)
    plt.close(fig)


def main(argv=None):
    opt = args(argv)
    if not opt.summary.is_dir() or opt.items_per_figure < 1 or opt.max_cases < 0:
        raise SystemExit("invalid summary directory / figure category count / case limit")
    try:
        import matplotlib  # noqa: F401
    except ImportError as e:
        raise SystemExit("Install matplotlib into the analysis environment to create PNG/SVG") from e
    try:
        charges = read_rows(opt.summary / "ddec6_elements.csv")
        bonds = read_rows(opt.summary / "ddec6_bond_types.csv")
    except FileNotFoundError as e:
        raise SystemExit(f"missing DDEC6 CSV: {e}") from e

    cases = sorted(set(x["case"] for x in charges) | set(x["case"] for x in bonds))
    if opt.case is not None:
        if opt.case not in cases:
            raise SystemExit(f"unknown case {opt.case!r}")
        cases = [opt.case]
    elif opt.max_cases:
        if len(cases) > opt.max_cases:
            print(f"WARNING: explicitly limited to {opt.max_cases}/{len(cases)} models")
        cases = cases[:opt.max_cases]

    destination = opt.summary / "ppt_figures"
    destination.mkdir(exist_ok=True)
    pages_created = 0
    for case in cases:
        for is_charge, all_rows, key in (
            (True, charges, "element"),
            (False, bonds, "element_pair"),
        ):
            subset = sorted((row for row in all_rows if row["case"] == case),
                            key=lambda x: x[key])
            page_count = (len(subset) + opt.items_per_figure - 1) // opt.items_per_figure
            for page in range(page_count):
                start = page*opt.items_per_figure
                draw(destination, case, subset[start:start+opt.items_per_figure],
                     is_charge, page+1, page_count)
                pages_created += 1
    print(f"Rendered {pages_created} figure pairs (SVG+PNG) across {len(cases)} models; "
          f"all {len(charges)} element and {len(bonds)} reported bond-type rows retained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
