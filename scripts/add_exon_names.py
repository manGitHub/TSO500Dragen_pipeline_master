#!/usr/bin/env python3
"""Add BED exon names to a TSO500 exon coverage report by exact coordinates."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


COORDINATE_COLUMNS = ["chr", "start", "end"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exon_bed", type=Path, help="Headerless four-column exon BED")
    parser.add_argument("exon_cov_report", type=Path, help="Input exon coverage TSV")
    parser.add_argument("output", type=Path, help="Output modified exon coverage TSV")
    return parser.parse_args()


def read_exon_bed(path: Path) -> pd.DataFrame:
    bed = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=[*COORDINATE_COLUMNS, "exon"],
        usecols=[0, 1, 2, 3],
        dtype=str,
        keep_default_na=False,
    )
    if bed[[*COORDINATE_COLUMNS, "exon"]].eq("").any(axis=None):
        raise ValueError("BED contains an empty coordinate or exon value")

    duplicate_rows = bed.loc[
        bed.duplicated(COORDINATE_COLUMNS, keep=False),
        COORDINATE_COLUMNS,
    ]
    if not duplicate_rows.empty:
        examples = duplicate_rows.drop_duplicates().head(10).to_dict("records")
        raise ValueError(f"BED contains duplicate coordinates: {examples}")
    return bed


def add_exon_names(exon_bed: Path, exon_cov_report: Path) -> pd.DataFrame:
    bed = read_exon_bed(exon_bed)
    report = pd.read_csv(
        exon_cov_report,
        sep="\t",
        dtype=str,
        keep_default_na=False,
    )

    missing_columns = [
        column for column in COORDINATE_COLUMNS if column not in report.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Exon report is missing required columns: {', '.join(missing_columns)}"
        )
    if "exon" in report.columns:
        raise ValueError("Exon report already contains an exon column")

    modified = report.merge(
        bed,
        on=COORDINATE_COLUMNS,
        how="left",
        sort=False,
        validate="many_to_one",
    )
    unmatched = modified["exon"].isna()
    if unmatched.any():
        examples = (
            modified.loc[unmatched, COORDINATE_COLUMNS]
            .head(10)
            .to_dict("records")
        )
        raise ValueError(
            f"{int(unmatched.sum())} report rows have no BED exon match: {examples}"
        )
    if len(modified) != len(report):
        raise ValueError("Output row count differs from the input report")

    modified = modified.drop(columns="gene")
    exon = modified.pop("exon")
    modified.insert(modified.columns.get_loc("end") + 1, "exon", exon)
    return modified


def main() -> None:
    args = parse_args()
    modified = add_exon_names(args.exon_bed, args.exon_cov_report)
    modified.to_csv(args.output, sep="\t", index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
