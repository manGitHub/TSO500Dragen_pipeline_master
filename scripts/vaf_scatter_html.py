#!/usr/bin/env python3
"""Create dynamic HTML VAF scatter plots for one or more TMB trace samples."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

from bokeh.embed import file_html
from bokeh.layouts import column, row
from bokeh.models import CheckboxGroup, ColumnDataSource, CustomJS, Div, HoverTool, Range1d, Select
from bokeh.palettes import Category10, Category20
from bokeh.plotting import figure
from bokeh.resources import INLINE


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "input"
OUTPUT_DIR = PROJECT_DIR / "output"
ALL_STATUS = "All"
ALL_GERMLINE = "All Germline"
DEFAULT_STATUS = "Germline_DB"
PREFERRED_OPTIONS = ["Germline_DB", "Germline_Proxi", "Somatic"]
HOVER_COLUMNS = [
    "GeneName",
    "Chromosome",
    "Position",
    "RefCall",
    "AltCall",
    "VAF",
    "Depth",
    "Status",
    "Consequence",
    "ProteinChange",
]
REQUIRED_COLUMNS = ["Status", "VAF", *[name for name in HOVER_COLUMNS if name not in {"Status", "VAF"}]]
EMPTY_SOURCE = {
    "x": [],
    "vaf": [],
    "color": [],
    **{name: [] for name in HOVER_COLUMNS},
}


def read_samples(sample_or_list: str) -> list[str]:
    value = Path(sample_or_list)
    if value.is_file():
        samples = [line.strip() for line in value.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        samples = [sample_or_list]
    if not samples:
        raise ValueError(f"No samples found in {sample_or_list}")
    return samples


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames or []
        missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
        if missing:
            raise ValueError(f"Missing required column(s): {', '.join(missing)}")
        return list(reader)


def status_options(rows: Iterable[dict[str, str]]) -> list[str]:
    statuses = sorted({row.get("Status", "") for row in rows if row.get("Status", "")})
    options = [ALL_STATUS]
    options.extend(status for status in PREFERRED_OPTIONS if status in statuses)
    options.append(ALL_GERMLINE)
    options.extend(status for status in statuses if status not in options)
    return options


def rows_for_status(rows: Iterable[dict[str, str]], selected_status: str) -> list[dict[str, str]]:
    rows = list(rows)
    if selected_status == ALL_STATUS:
        return rows
    if selected_status == ALL_GERMLINE:
        return [row for row in rows if "Germline" in (row.get("Status") or "")]
    return [row for row in rows if row.get("Status") == selected_status]


def color_map(rows: Iterable[dict[str, str]]) -> dict[str, str]:
    statuses = sorted({row.get("Status", "") for row in rows if row.get("Status", "")})
    palette = Category10[10] if len(statuses) <= 10 else Category20[20]
    return {status: palette[index % len(palette)] for index, status in enumerate(statuses)}


def source_data(rows: Iterable[dict[str, str]], colors: dict[str, str] | None = None) -> dict[str, list[object]]:
    rows = list(rows)
    colors = colors or color_map(rows)
    data: dict[str, list[object]] = {
        "x": [],
        "vaf": [],
        "color": [],
        **{name: [] for name in HOVER_COLUMNS},
    }
    for index, row_data in enumerate(rows, start=1):
        try:
            vaf = float(row_data["VAF"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid VAF value: {row_data.get('VAF')!r}") from error

        status = row_data.get("Status", "")
        data["x"].append(index)
        data["vaf"].append(vaf)
        data["color"].append(colors.get(status, "#4c78a8"))
        for column_name in HOVER_COLUMNS:
            data[column_name].append(row_data.get(column_name, ""))
    return data


def chromosome_boundaries(rows: Iterable[dict[str, str]]) -> list[float]:
    boundaries = []
    previous_chromosome = None
    for index, row_data in enumerate(rows, start=1):
        chromosome = row_data.get("Chromosome", "")
        if previous_chromosome is not None and chromosome != previous_chromosome:
            boundaries.append(index - 0.5)
        previous_chromosome = chromosome
    return boundaries


def boundary_source_data(rows: Iterable[dict[str, str]]) -> dict[str, list[list[float]]]:
    boundaries = chromosome_boundaries(rows)
    return {
        "xs": [[boundary, boundary] for boundary in boundaries],
        "ys": [[0, 1] for _ in boundaries],
    }


def count_label(status: str, count: int) -> str:
    noun = "variant" if count == 1 else "variants"
    return f"{status}: {count} {noun}"


def build_plot(sample: str, rows: list[dict[str, str]]):
    options = status_options(rows)
    if not options:
        options = [ALL_STATUS, ALL_GERMLINE]
    initial_status = DEFAULT_STATUS if DEFAULT_STATUS in options else (ALL_GERMLINE if ALL_GERMLINE in options else options[0])
    colors = color_map(rows)
    filtered_rows = {status: rows_for_status(rows, status) for status in options}
    datasets = {
        status: source_data(status_rows, colors)
        for status, status_rows in filtered_rows.items()
    }
    boundary_sets = {
        status: boundary_source_data(status_rows)
        for status, status_rows in filtered_rows.items()
    }
    empty_boundaries = {"xs": [], "ys": []}
    boundary_source = ColumnDataSource(data=boundary_sets.get(initial_status, empty_boundaries))
    line_toggle = CheckboxGroup(labels=["CHR_EDGES"], active=[0], width=120)
    counts = {status: count_label(status, len(data["x"])) for status, data in datasets.items()}
    initial_data = datasets.get(initial_status, EMPTY_SOURCE)

    source = ColumnDataSource(data=initial_data)
    status_select = Select(title="Variant status", value=initial_status, options=options, width=260)
    count_div = Div(text=counts[initial_status], width=260, height=30)

    plot = figure(
        title=f"{sample} VAF scatter - {initial_status}",
        width=1000,
        height=650,
        sizing_mode="stretch_width",
        x_axis_label="Filtered variant index",
        y_axis_label="VAF",
        x_range=Range1d(0.5, max(1.5, len(initial_data["x"]) + 0.5)),
        y_range=Range1d(0, 1),
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )
    plot.scatter(
        "x",
        "vaf",
        source=source,
        size=7,
        color="color",
        alpha=0.75,
        legend_field="Status",
    )
    separator_renderer = plot.multi_line(
        "xs",
        "ys",
        source=boundary_source,
        line_color="red",
        line_width=1.5,
        line_alpha=0.8,
    )
    plot.add_tools(
        HoverTool(
            tooltips=[
                ("Gene", "@GeneName"),
                ("Chromosome", "@Chromosome"),
                ("Position", "@Position"),
                ("Ref", "@RefCall"),
                ("Alt", "@AltCall"),
                ("VAF", "@VAF"),
                ("Depth", "@Depth"),
                ("Status", "@Status"),
                ("Consequence", "@Consequence"),
                ("Protein Change", "@ProteinChange"),
            ]
        )
    )
    legend = plot.legend[0]
    legend.title = "Status"
    legend.location = "center"
    plot.add_layout(legend, "right")
    plot.grid.grid_line_alpha = 0.25

    callback = CustomJS(
        args={
            "source": source,
            "datasets": datasets,
            "boundary_source": boundary_source,
            "boundary_sets": boundary_sets,
            "counts": counts,
            "count_div": count_div,
            "plot": plot,
            "sample": sample,
        },
        code="""
        const selected = cb_obj.value;
        const selectedData = datasets[selected] || {x: [], vaf: [], color: []};
        const selectedBoundaries = boundary_sets[selected] || {xs: [], ys: []};
        source.data = selectedData;
        boundary_source.data = selectedBoundaries;
        source.change.emit();
        boundary_source.change.emit();
        count_div.text = counts[selected] || `${selected}: 0 variants`;
        plot.title.text = `${sample} VAF scatter - ${selected}`;
        const pointCount = selectedData.x ? selectedData.x.length : 0;
        plot.x_range.start = 0.5;
        plot.x_range.end = Math.max(1.5, pointCount + 0.5);
        """,
    )
    status_select.js_on_change("value", callback)
    line_toggle.js_on_change(
        "active",
        CustomJS(
            args={"separator_renderer": separator_renderer},
            code="separator_renderer.visible = cb_obj.active.includes(0);",
        ),
    )

    controls = row(status_select, line_toggle, count_div, sizing_mode="stretch_width")
    return column(controls, plot, sizing_mode="stretch_width")


def write_sample_html(sample: str) -> Path:
    input_path = INPUT_DIR / f"{sample}_TMB_Trace.tsv"
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    rows = load_rows(input_path)
    layout = build_plot(sample, rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{sample}_variant_scatter.html"
    output_path.write_text(file_html(layout, INLINE, f"{sample} VAF scatter"), encoding="utf-8")
    return output_path


def process_samples(samples: Iterable[str]) -> list[Path]:
    return [write_sample_html(sample) for sample in samples]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_or_list", help="Sample ID or path to a file containing sample IDs")
    args = parser.parse_args()
    process_samples(read_samples(args.sample_or_list))


if __name__ == "__main__":
    main()
