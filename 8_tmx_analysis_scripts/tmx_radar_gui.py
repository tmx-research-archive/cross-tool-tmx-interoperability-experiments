#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Tkinter is required but could not be imported: {exc}")

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "matplotlib is required. Install it with: pip install matplotlib\n"
        f"Original error: {exc}"
    )

# Optional drag-and-drop support.
DND_AVAILABLE = False
try:  # pragma: no cover - optional dependency
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    DND_AVAILABLE = True
except Exception:  # pragma: no cover
    TkinterDnD = None
    DND_FILES = None


AXIS_ORDER = [
    "A1_tu_count_retention",
    "A2_text_retention",
    "A3_inline_tag_count_retention",
    "A4_inline_tag_type_retention",
    "A5_bpt_ept_pairing_retention",
    "A6_nesting_retention",
    "A7_attribute_key_retention",
    "A8_attribute_value_retention",
    "A9_header_retention",
    "A10_prop_retention",
    "A11_language_retention",
    "A12_tuid_retention",
]

AXIS_LABELS_SHORT = {
    "A1_tu_count_retention": "A1 TU count",
    "A2_text_retention": "A2 Text (A2b)",
    "A3_inline_tag_count_retention": "A3 Tag count",
    "A4_inline_tag_type_retention": "A4 Tag type (A4b)",
    "A5_bpt_ept_pairing_retention": "A5 Pairing",
    "A6_nesting_retention": "A6 Nesting (DOM)",
    "A7_attribute_key_retention": "A7 Attr key",
    "A8_attribute_value_retention": "A8 Attr value",
    "A9_header_retention": "A9 Header (A9a)",
    "A10_prop_retention": "A10 Prop (A10a)",
    "A11_language_retention": "A11 Lang (A11b)",
    "A12_tuid_retention": "A12 TUID",
}

# Alternate names tolerated from older or manual files.
AXIS_ALIASES = {
    "tu_count_retention": "A1_tu_count_retention",
    "TU count retention": "A1_tu_count_retention",
    "text_retention": "A2_text_retention",
    "Text retention": "A2_text_retention",
    # New supplementary axes from the revised diff script — map them onto
    # the existing 12-axis radar so they can still be plotted (the radar
    # shows only the headline axis per family; supplementary ones are
    # available in axis_*.csv for fuller analysis).
    "A2b_pure_text_retention": "A2_text_retention",
    "A2b_user_visible_text_retention": "A2_text_retention",
    "A4b_inline_tag_type_multiset_retention": "A4_inline_tag_type_retention",
    "A6_dom_nesting_retention": "A6_nesting_retention",
    # A6b is a reverse diagnostic axis and is intentionally not mapped to the main radar axis.
    "A9a_header_field_presence_retention": "A9_header_retention",
    "A9b_header_value_retention": "A9_header_retention",
    "A10a_prop_type_retention": "A10_prop_retention",
    # A10a_strict_prop_type_retention_per_tu is an intentionally separate
    # all-or-nothing diagnostic and is not aggregated to the A10 main axis.
    "A10b_prop_value_retention": "A10_prop_retention",
    "A11a_language_strict_retention": "A11_language_retention",
    "A11b_language_case_normalised_retention": "A11_language_retention",
    "inline_tag_count_retention": "A3_inline_tag_count_retention",
    "inline_tag_type_retention": "A4_inline_tag_type_retention",
    "tag_count_retention": "A3_inline_tag_count_retention",
    "tag_type_retention": "A4_inline_tag_type_retention",
    "pairing_retention": "A5_bpt_ept_pairing_retention",
    "bpt_ept_pairing_retention": "A5_bpt_ept_pairing_retention",
    "nesting_retention": "A6_nesting_retention",
    "attribute_key_retention": "A7_attribute_key_retention",
    "attribute_value_retention": "A8_attribute_value_retention",
    "header_retention": "A9_header_retention",
    "prop_retention": "A10_prop_retention",
    "language_retention": "A11_language_retention",
    "lang_retention": "A11_language_retention",
    "tuid_retention": "A12_tuid_retention",
}

# Preferred keys for the headline 12-axis radar when a result file contains
# supplementary metrics. The choices follow the revised axis definition:
# A2 prefers user-visible/pure text over raw itertext when available.
# A4 prefers multiset tag-type retention over position-sensitive type retention when available.
# A9/A10 use presence/type retention as headline axes; value retention stays diagnostic.
# A11 uses case-normalised language retention as headline axis.
# Reverse axes such as A3b tag introduction or A6b nesting introduction are not plotted as headline retention axes.
AXIS_KEY_PRIORITY = {
    "A1_tu_count_retention": ["A1_tu_count_retention"],
    "A2_text_retention": ["A2b_user_visible_text_retention", "A2b_pure_text_retention", "A2_text_retention"],
    "A3_inline_tag_count_retention": ["A3_inline_tag_count_retention"],
    "A4_inline_tag_type_retention": ["A4b_inline_tag_type_multiset_retention", "A4_inline_tag_type_retention"],
    "A5_bpt_ept_pairing_retention": ["A5_bpt_ept_pairing_retention"],
    "A6_nesting_retention": ["A6_dom_nesting_retention", "A6_nesting_retention"],
    "A7_attribute_key_retention": ["A7_attribute_key_retention"],
    "A8_attribute_value_retention": ["A8_attribute_value_retention"],
    "A9_header_retention": ["A9a_header_field_presence_retention", "A9_header_retention", "A9b_header_value_retention"],
    "A10_prop_retention": ["A10a_prop_type_retention", "A10_prop_retention", "A10b_prop_value_retention"],
    "A11_language_retention": ["A11b_language_case_normalised_retention", "A11_language_retention", "A11a_language_strict_retention"],
    "A12_tuid_retention": ["A12_tuid_retention"],
}


@dataclass
class RadarSeries:
    label: str
    path: Path
    scores: Dict[str, Optional[float]]
    mode: str = ""
    group: str = ""
    route: str = ""

    def values(self, missing_as: float = 0.0) -> List[float]:
        """Return raw axis values for plotting.

        Values are no longer capped at 100 here. This is intentional:
        A3/A5 can exceed 100 when a CAT tool expands inline-code or
        bpt/ept-pair representations during TMX migration. The radar
        chart can therefore show the actual >100% values.
        """
        vals: List[float] = []
        for axis in AXIS_ORDER:
            v = self.scores.get(axis)
            if v is None:
                vals.append(float(missing_as))
            else:
                vals.append(max(0.0, float(v)))
        return vals


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in {"na", "n/a", "none", "null", "nan"}:
        return None
    s = s.replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalise_axis_name(name: str) -> Optional[str]:
    raw = str(name).strip()
    if raw in AXIS_ORDER:
        return raw
    if raw in AXIS_ALIASES:
        return AXIS_ALIASES[raw]
    lower = raw.lower().strip()
    for k, v in AXIS_ALIASES.items():
        if lower == k.lower():
            return v
    # Strict prefix match: only fold "A3_..." into A3, never "A3b_...".
    # The trailing "(?:[_\s]|$)" ensures the digit run is terminated by an
    # underscore, whitespace, or end-of-string — so a single letter suffix
    # like "b" disqualifies the match and the supplementary axis is left
    # for explicit AXIS_ALIASES handling above.
    m = re.match(r"^(A\d+)(?:[_\s]|$)", raw, flags=re.I)
    if m:
        prefix = m.group(1).upper()
        for axis in AXIS_ORDER:
            if axis.startswith(prefix + "_"):
                return axis
    return None


def infer_label_from_path(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^(axis|summary|per_tu|diagnostics)_", "", stem, flags=re.I)
    stem = stem.replace("_", " ")
    return stem


def read_axis_csv(path: Path) -> List[RadarSeries]:
    """Read an axis CSV. Returns a list of one or more RadarSeries.

    For H0/H1/C0 outputs the CSV contains a single comparison and this
    returns exactly one series. For H2/H3 outputs the CSV may contain a
    "comparison" column splitting the rows into multiple comparisons
    (step1, step2, end_to_end, ...). Each comparison becomes its own
    series so the radar can overlay them in one chart.
    """
    label = infer_label_from_path(path)
    mode_default = group_default = route_default = ""

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        lower_fields = {h.lower().strip(): h for h in reader.fieldnames}

        # Expected long format: axis, score, layer, interpretation [, comparison]
        axis_col = lower_fields.get("axis") or lower_fields.get("metric") or lower_fields.get("name")
        score_col = lower_fields.get("score") or lower_fields.get("value") or lower_fields.get("pct")
        comparison_col = lower_fields.get("comparison")

        # Wide format fallback: one row with axis names as columns.
        if not axis_col or not score_col:
            scores: Dict[str, Optional[float]] = {axis: None for axis in AXIS_ORDER}
            rows = list(reader)
            if not rows:
                return [RadarSeries(label=label, path=path, scores=scores)]
            row = rows[0]
            for col, val in row.items():
                axis = normalise_axis_name(col)
                if axis:
                    scores[axis] = safe_float(val)
            mode = group = route = ""
            for meta_col in ("mode", "group", "route", "label"):
                if meta_col in row and row[meta_col]:
                    if meta_col == "mode":
                        mode = row[meta_col]
                    elif meta_col == "group":
                        group = row[meta_col]
                    elif meta_col == "route":
                        route = row[meta_col]
                    elif meta_col == "label":
                        label = row[meta_col]
            return [RadarSeries(label=label, path=path, scores=scores, mode=mode, group=group, route=route)]

        # Long format: group rows by comparison (if present) so that
        # H2/H3 files emit one series per comparison.
        rows = list(reader)

        # Build a temporary per-comparison map of raw_axis_name -> value
        # so we can resolve multiple-key-per-slot conflicts using the
        # documented AXIS_KEY_PRIORITY preferences instead of last-wins.
        raw_by_comparison: Dict[str, Dict[str, Optional[float]]] = {}
        for row in rows:
            comp_value = (row.get(comparison_col) or "").strip() if comparison_col else ""
            slot = raw_by_comparison.setdefault(comp_value, {})
            raw_name = (row.get(axis_col, "") or "").strip()
            if not raw_name:
                continue
            slot[raw_name] = safe_float(row.get(score_col))
            if not mode_default and "mode" in row:
                mode_default = row.get("mode", "") or ""
            if not group_default and "group" in row:
                group_default = row.get("group", "") or ""
            if not route_default and "route" in row:
                route_default = row.get("route", "") or ""

        # Resolve each comparison's raw values into the headline 12-axis
        # buckets using AXIS_KEY_PRIORITY when several keys would map to
        # the same target slot (e.g. A2 vs A2b vs A2b_user_visible).
        by_comparison: Dict[str, Dict[str, Optional[float]]] = {}
        for comp_value, raw_map in raw_by_comparison.items():
            bucket: Dict[str, Optional[float]] = {axis: None for axis in AXIS_ORDER}
            for target_axis in AXIS_ORDER:
                for key in AXIS_KEY_PRIORITY.get(target_axis, [target_axis]):
                    if key in raw_map and raw_map[key] is not None:
                        bucket[target_axis] = raw_map[key]
                        break
            # Fallback: any remaining raw_name that normalises to a
            # target slot still without a value gets adopted now (this
            # covers legacy CSVs whose column names don't match the
            # priority lists exactly).
            for raw_name, val in raw_map.items():
                if val is None:
                    continue
                target = normalise_axis_name(raw_name)
                if target and bucket.get(target) is None:
                    bucket[target] = val
            by_comparison[comp_value] = bucket

    # Fallback: extract mode/group/route from filename if not in the CSV.
    stem = path.stem
    fname_match = re.match(
        r"^(?:axis|summary|diagnostics|per_tu|trajectory)_(H[0-3]|C0)_(G[ABC]|NA)_(.+)$",
        stem,
        flags=re.I,
    )
    if fname_match:
        if not mode_default:
            mode_default = fname_match.group(1).upper()
        if not group_default:
            group_default = fname_match.group(2).upper()
        if not route_default:
            route_default = fname_match.group(3)

    if not group_default:
        m = re.search(r"[_/\\](G[ABC]|NA)[_./]", str(path), flags=re.I)
        if m:
            group_default = m.group(1).upper()

    # Build one series per comparison key.
    series_list: List[RadarSeries] = []
    for comp_value, scores in by_comparison.items():
        if comp_value:
            # Use the comparison label (e.g. "step1:Trados->memoQ",
            # "end_to_end:Trados->Trados") as the series label so they
            # are distinguishable in the legend.
            comp_short = comp_value.replace(":", " ").replace("->", "→")
            series_label = comp_short
        elif route_default:
            series_label = route_default.replace("_", " ")
        elif mode_default or group_default:
            series_label = " | ".join([p for p in [mode_default, group_default] if p])
        else:
            series_label = label
        series_list.append(
            RadarSeries(
                label=series_label,
                path=path,
                scores=scores,
                mode=mode_default,
                group=group_default,
                route=route_default,
            )
        )

    if not series_list:
        # Defensive: no rows produced any data.
        empty = {axis: None for axis in AXIS_ORDER}
        series_list = [RadarSeries(label=label, path=path, scores=empty,
                                   mode=mode_default, group=group_default, route=route_default)]
    return series_list


def read_summary_json(path: Path) -> RadarSeries:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    scores: Dict[str, Optional[float]] = {axis: None for axis in AXIS_ORDER}

    # H0/C0/H1 summaries normally store axis_scores at the top level.
    # H2/H3 route summaries store pair-level scores under end_to_end.
    # For radar visualisation, use end_to_end by default when top-level axis_scores is absent.
    score_source = data
    axis_scores = data.get("axis_scores") or data.get("scores")
    if axis_scores is None and isinstance(data.get("end_to_end"), dict):
        score_source = data["end_to_end"]
        axis_scores = score_source.get("axis_scores") or score_source.get("scores")
    if not isinstance(axis_scores, dict):
        raise ValueError("JSON does not contain an axis_scores object or an end_to_end.axis_scores object")

    def _read_score(key: str) -> Optional[float]:
        if key not in axis_scores:
            return None
        val = axis_scores[key]
        if isinstance(val, dict):
            return safe_float(val.get("score") or val.get("value"))
        return safe_float(val)

    # Populate headline radar axes using the revised priority rules.
    for target_axis in AXIS_ORDER:
        for key in AXIS_KEY_PRIORITY.get(target_axis, [target_axis]):
            val = _read_score(key)
            if val is not None:
                scores[target_axis] = val
                break

    # Fallback for older files with only aliases/manual axis names.
    for key, val in axis_scores.items():
        target = normalise_axis_name(key)
        if target and scores.get(target) is None:
            if isinstance(val, dict):
                scores[target] = safe_float(val.get("score") or val.get("value"))
            else:
                scores[target] = safe_float(val)

    mode = str(data.get("mode", score_source.get("mode", "")) or "")
    group = str(data.get("group", score_source.get("group", "")) or "")
    route_obj = data.get("route", score_source.get("route", ""))
    if isinstance(route_obj, list):
        route = " → ".join(map(str, route_obj))
    else:
        route = str(route_obj or "")

    # Fallback from filename pattern (axis_<MODE>_<GROUP>_<route>.csv-style).
    stem = path.stem
    fname_match = re.match(
        r"^(?:axis|summary|diagnostics|per_tu|trajectory)_(H[0-3]|C0)_(G[ABC]|NA)_(.+)$",
        stem,
        flags=re.I,
    )
    if fname_match:
        if not mode:
            mode = fname_match.group(1).upper()
        if not group:
            group = fname_match.group(2).upper()
        if not route:
            route = fname_match.group(3).replace("_", " → ")

    # Older fallback: extract group alone if still missing.
    if not group:
        m = re.search(r"[_/\\](G[ABC]|NA)[_./]", str(path), flags=re.I)
        if m:
            group = m.group(1).upper()

    # Prefer route-only labels for overlay clarity; mode and group are usually
    # shared across overlaid series and belong in the chart title.
    if route:
        label = route
    elif mode or group:
        parts = [p for p in [mode, group] if p]
        label = " | ".join(parts)
    else:
        label = infer_label_from_path(path)

    return RadarSeries(label=label, path=path, scores=scores, mode=mode, group=group, route=route)


def read_result_file(path: Path) -> List[RadarSeries]:
    """Read one result file and return one or more series.

    JSON summaries always yield one series. CSV files may yield multiple
    series when they contain a "comparison" column (e.g. H2/H3 outputs).
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        return [read_summary_json(path)]
    if suffix == ".csv":
        return read_axis_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def parse_dropped_files(data: str) -> List[Path]:
    """Parse Tk DND file list, supporting spaces in paths."""
    # TkinterDnD wraps paths with braces when needed: {C:/a b/file.csv}
    paths: List[str] = []
    token = ""
    in_brace = False
    for ch in data:
        if ch == "{" and not in_brace:
            in_brace = True
            token = ""
        elif ch == "}" and in_brace:
            in_brace = False
            if token:
                paths.append(token)
            token = ""
        elif ch.isspace() and not in_brace:
            if token:
                paths.append(token)
                token = ""
        else:
            token += ch
    if token:
        paths.append(token)
    return [Path(p) for p in paths]


class RadarApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TMX Radar")
        self.root.geometry("1180x780")
        self.series: List[RadarSeries] = []
        self.output_dir: Optional[Path] = None

        self.title_var = tk.StringVar(value="TMX Structural Retention Radar")
        self.fill_var = tk.BooleanVar(value=True)
        self.markers_var = tk.BooleanVar(value=True)
        self.grid_var = tk.BooleanVar(value=True)
        self.show_values_var = tk.BooleanVar(value=True)
        self.missing_as_var = tk.StringVar(value="blank")
        self.legend_var = tk.StringVar(value="right")
        self.max_score_var = tk.StringVar(value="auto")
        self.figure: Optional[Figure] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.toolbar: Optional[NavigationToolbar2Tk] = None

        self._build_ui()
        self._draw_empty_chart()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Step 1: Input files
        step1 = ttk.LabelFrame(left, text="Step 1: Select result files to overlay")
        step1.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            step1,
            text="Supports axis_*.csv or summary_*.json; multiple files allowed.",
            wraplength=340,
        ).pack(anchor="w", padx=8, pady=(8, 2))

        btn_row = ttk.Frame(step1)
        btn_row.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btn_row, text="Pick files", command=self.pick_files).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Clear", command=self.clear_files).pack(side=tk.LEFT, padx=6)

        self.file_list = tk.Listbox(step1, height=8, selectmode=tk.EXTENDED)
        self.file_list.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.file_list.bind("<Double-Button-1>", self.rename_selected)

        if DND_AVAILABLE:
            self.file_list.drop_target_register(DND_FILES)
            self.file_list.dnd_bind("<<Drop>>", self.on_drop_files)
            ttk.Label(step1, text="You can also drag files directly into the list.", foreground="gray").pack(anchor="w", padx=8, pady=(0, 6))
        else:
            ttk.Label(step1, text="Drag-and-drop requires tkinterdnd2; use Pick files instead.", foreground="gray").pack(anchor="w", padx=8, pady=(0, 6))

        order_row = ttk.Frame(step1)
        order_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(order_row, text="Move up", command=lambda: self.move_selected(-1)).pack(side=tk.LEFT)
        ttk.Button(order_row, text="Move down", command=lambda: self.move_selected(1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(order_row, text="Rename", command=self.rename_selected).pack(side=tk.LEFT)

        # Step 2: Chart settings
        step2 = ttk.LabelFrame(left, text="Step 2: Configure radar chart")
        step2.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(step2, text="Chart title").pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Entry(step2, textvariable=self.title_var).pack(fill=tk.X, padx=8, pady=(2, 6))

        opts = ttk.Frame(step2)
        opts.pack(fill=tk.X, padx=8, pady=4)
        ttk.Checkbutton(opts, text="Fill area", variable=self.fill_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(opts, text="Markers", variable=self.markers_var).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Checkbutton(opts, text="Grid", variable=self.grid_var).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Checkbutton(opts, text="Show value table", variable=self.show_values_var).grid(row=1, column=1, sticky="w", padx=10, pady=(4, 0))

        grid2 = ttk.Frame(step2)
        grid2.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(grid2, text="Missing/N/A as").grid(row=0, column=0, sticky="w")
        ttk.Combobox(grid2, textvariable=self.missing_as_var, values=["0", "50", "100", "blank"], width=8, state="readonly").grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(grid2, text="Max score").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(grid2, textvariable=self.max_score_var, width=10).grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(grid2, text="use auto to include >100", foreground="gray").grid(row=1, column=2, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(grid2, text="Legend").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(grid2, textvariable=self.legend_var, values=["right", "bottom", "inside", "none"], width=10, state="readonly").grid(row=2, column=1, sticky="w", padx=6, pady=(6, 0))

        ttk.Button(step2, text="Generate / Refresh radar", command=self.refresh_chart).pack(fill=tk.X, padx=8, pady=(8, 8))

        # Step 3: Export
        step3 = ttk.LabelFrame(left, text="Step 3: Select output folder")
        step3.pack(fill=tk.X, pady=(0, 10))
        out_row = ttk.Frame(step3)
        out_row.pack(fill=tk.X, padx=8, pady=8)
        self.out_label = ttk.Label(out_row, text="No output folder selected", wraplength=250)
        self.out_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text="Pick", command=self.pick_output_dir).pack(side=tk.RIGHT)

        export_row = ttk.Frame(step3)
        export_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(export_row, text="Export PNG", command=lambda: self.export_chart("png")).pack(side=tk.LEFT)
        ttk.Button(export_row, text="PDF", command=lambda: self.export_chart("pdf")).pack(side=tk.LEFT, padx=4)
        ttk.Button(export_row, text="SVG", command=lambda: self.export_chart("svg")).pack(side=tk.LEFT)
        ttk.Button(export_row, text="CSV", command=self.export_combined_csv).pack(side=tk.LEFT, padx=4)

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(left, textvariable=self.status_var, foreground="gray", wraplength=360).pack(fill=tk.X, pady=(8, 0))

        # Right panel chart
        self.chart_frame = ttk.Frame(right)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

    def pick_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select axis CSV or summary JSON files",
            filetypes=[
                ("TMX result files", "*.csv *.json"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        self.add_files([Path(p) for p in paths])

    def on_drop_files(self, event) -> None:  # pragma: no cover - GUI callback
        paths = parse_dropped_files(event.data)
        self.add_files(paths)

    def add_files(self, paths: List[Path]) -> None:
        loaded = 0
        errors: List[str] = []
        # Track already-loaded series by (path, label) so the same file can
        # contribute multiple comparison-labelled series (H2/H3) while still
        # preventing accidental double-load when the same file is picked twice.
        existing = {(s.path.resolve(), s.label) for s in self.series if s.path.exists()}
        # Also track resolved file paths already processed in this call so we
        # do not call read_result_file on the same path twice.
        processed_paths: set = set()
        for path in paths:
            try:
                path = path.expanduser().resolve()
                if path in processed_paths:
                    continue
                processed_paths.add(path)
                new_series_list = read_result_file(path)
                for s in new_series_list:
                    if (path, s.label) in existing:
                        continue
                    self.series.append(s)
                    existing.add((path, s.label))
                    loaded += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.refresh_file_list()
        if loaded:
            self._auto_update_title()
            self.status_var.set(f"Loaded {loaded} series. Double-click a file to rename its legend label.")
            self.refresh_chart()
        if errors:
            messagebox.showwarning("Some files could not be loaded", "\n".join(errors[:10]))

    def _auto_update_title(self) -> None:
        """Suggest a chart title from the loaded series metadata.

        Only overwrites the title when (a) the user has not customised it,
        i.e. it is still empty or the previous auto-generated value, and
        (b) the loaded series share enough metadata to build a meaningful
        title.
        """
        if not self.series:
            return
        modes = {s.mode for s in self.series if s.mode}
        groups = {s.group for s in self.series if s.group}
        routes = {s.route for s in self.series if s.route}
        current = self.title_var.get().strip()
        # Treat "TMX Structural Retention Radar" (the default placeholder)
        # and any previously auto-generated title as overwritable.
        overwritable = (
            not current
            or current == "TMX Structural Retention Radar"
            or current == getattr(self, "_last_auto_title", "")
        )
        if not overwritable:
            return
        parts: List[str] = []
        if len(modes) == 1:
            parts.append(next(iter(modes)))
        if len(groups) == 1:
            parts.append(next(iter(groups)))
        elif len(routes) == 1:
            # All series share a single route but differ in group; surface
            # the route in the title so readers know what is being compared.
            route_name = next(iter(routes)).replace("_", " ")
            parts.append(route_name)
        if not parts:
            return
        new_title = " — ".join(parts)
        self.title_var.set(new_title)
        self._last_auto_title = new_title

    def refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for i, s in enumerate(self.series, start=1):
            missing = sum(1 for axis in AXIS_ORDER if s.scores.get(axis) is None)
            suffix = f"  [{missing} N/A]" if missing else ""
            self.file_list.insert(tk.END, f"{i}. {s.label}{suffix}")

    def clear_files(self) -> None:
        self.series.clear()
        # Reset the auto-suggested title so the placeholder shows again.
        if getattr(self, "_last_auto_title", "") == self.title_var.get().strip():
            self.title_var.set("")
            self._last_auto_title = ""
        self.refresh_file_list()
        self._draw_empty_chart()
        self.status_var.set("Cleared.")

    def move_selected(self, direction: int) -> None:
        sel = list(self.file_list.curselection())
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.series):
            return
        self.series[idx], self.series[new_idx] = self.series[new_idx], self.series[idx]
        self.refresh_file_list()
        self.file_list.selection_set(new_idx)
        self.refresh_chart()

    def rename_selected(self, event=None) -> None:
        sel = list(self.file_list.curselection())
        if not sel:
            return
        idx = sel[0]
        old = self.series[idx].label

        dialog = tk.Toplevel(self.root)
        dialog.title("Rename legend label")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Legend label").pack(anchor="w", padx=10, pady=(10, 2))
        var = tk.StringVar(value=old)
        entry = ttk.Entry(dialog, textvariable=var, width=60)
        entry.pack(fill=tk.X, padx=10, pady=4)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def apply():
            new = var.get().strip()
            if new:
                self.series[idx].label = new
                self.refresh_file_list()
                self.file_list.selection_set(idx)
                self.refresh_chart()
            dialog.destroy()

        row = ttk.Frame(dialog)
        row.pack(fill=tk.X, padx=10, pady=(6, 10))
        ttk.Button(row, text="OK", command=apply).pack(side=tk.RIGHT)
        ttk.Button(row, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=6)
        dialog.bind("<Return>", lambda e: apply())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def pick_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.output_dir = Path(d).expanduser().resolve()
            self.out_label.configure(text=str(self.output_dir))
            self.status_var.set(f"Output folder selected: {self.output_dir}")

    def _new_figure(self, with_table: bool = False) -> Tuple[Figure, object]:
        if with_table:
            # Taller canvas; the polar axes get the upper ~72% of the figure
            # and a value table occupies the remainder.
            fig = Figure(figsize=(7.6, 8.6), dpi=100)
            gs = fig.add_gridspec(2, 1, height_ratios=[3.2, 1.0], hspace=0.18)
            ax = fig.add_subplot(gs[0, 0], polar=True)
            table_ax = fig.add_subplot(gs[1, 0])
            table_ax.set_axis_off()
            # Attach table_ax to the figure for later retrieval.
            fig._tmx_table_ax = table_ax  # type: ignore[attr-defined]
        else:
            fig = Figure(figsize=(7.2, 6.6), dpi=100)
            ax = fig.add_subplot(111, polar=True)
        return fig, ax

    def _mount_figure(self, fig: Figure) -> None:
        if self.toolbar:
            self.toolbar.destroy()
            self.toolbar = None
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        self.figure = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
        self.toolbar.update()

    def _draw_empty_chart(self) -> None:
        fig, ax = self._new_figure()
        ax.set_title("Load axis CSV or summary JSON files", pad=20)
        ax.set_ylim(0, 100)
        angles = self._angles()
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([AXIS_LABELS_SHORT[a] for a in AXIS_ORDER], fontsize=8)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8)
        self._mount_figure(fig)

    def _angles(self) -> List[float]:
        n = len(AXIS_ORDER)
        angles = [2 * math.pi * i / n for i in range(n)]
        return angles + angles[:1]

    def refresh_chart(self) -> None:
        if not self.series:
            self._draw_empty_chart()
            return
        try:
            missing_choice = self.missing_as_var.get().strip().lower()
            missing_as = float("nan") if missing_choice == "blank" else float(missing_choice)
        except ValueError:
            messagebox.showerror("Invalid setting", "Missing value must be 0, 50, 100, or blank.")
            return

        max_score_setting = self.max_score_var.get().strip().lower()
        auto_max = max_score_setting in {"", "auto", "automatic"}
        manual_max_score: Optional[float] = None
        if not auto_max:
            try:
                manual_max_score = float(max_score_setting)
                if manual_max_score <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid setting", "Max score must be > 0 or 'auto'.")
                return

        show_values = self.show_values_var.get()
        fig, ax = self._new_figure(with_table=show_values)
        angles = self._angles()
        labels = [AXIS_LABELS_SHORT[a] for a in AXIS_ORDER]

        # Distinct marker shapes for overlaid series so they are visually
        # distinguishable even when lines overlap or are printed in greyscale.
        marker_cycle = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]
        n_series = len(self.series)

        # First pass: collect raw values per axis across all series.
        # A3/A5 may legitimately exceed 100 when a tool expands tags;
        # the default 'auto' scale includes those values instead of clipping them.
        raw_vals_all: List[List[float]] = []
        finite_values: List[float] = []
        for series in self.series:
            raw = series.values(missing_as=missing_as)
            raw_vals_all.append(raw)
            finite_values.extend([v for v in raw if not math.isnan(v)])

        data_max = max(finite_values) if finite_values else 100.0
        if auto_max:
            # Keep ordinary retention charts on a 0-100 scale, but expand
            # to the next 20-point gridline when actual data exceed 100.
            max_score = max(100.0, math.ceil(data_max / 20.0) * 20.0)
        else:
            max_score = float(manual_max_score)

        all_vals: List[List[float]] = []
        for raw in raw_vals_all:
            # Only clip when the user manually sets a scale below the data.
            # With auto scale, this normally leaves >100 values visible at
            # their real radial positions.
            all_vals.append([v if math.isnan(v) else min(max(v, 0), max_score) for v in raw])

        # Detect whether the user is mapping N/A to 0, which produces
        # misleading collapse-to-centre artefacts when some axes are
        # legitimately N/A (e.g. inline-tag axes for GA).
        na_collapsed_to_zero = False
        if missing_choice == "0":
            for series, vals in zip(self.series, all_vals):
                raw_vals = series.values(missing_as=float("nan"))
                if any(math.isnan(rv) for rv in raw_vals):
                    na_collapsed_to_zero = True
                    break

        line_artists = []
        # Compute display labels. If multiple series share the same base
        # label (e.g. all three are "memoQ to Trados" but differ by group),
        # prepend the group code so each line is uniquely identifiable in
        # the legend and the value-table row labels.
        base_labels = [s.label for s in self.series]
        label_counts: dict[str, int] = {}
        for b in base_labels:
            label_counts[b] = label_counts.get(b, 0) + 1
        display_labels: List[str] = []
        for s in self.series:
            if label_counts.get(s.label, 0) > 1 and s.group:
                display_labels.append(f"{s.group} | {s.label}")
            else:
                display_labels.append(s.label)

        # Also reflect the disambiguated label in the legend artist below.
        for series_idx, series in enumerate(self.series):
            vals = all_vals[series_idx]
            vals_closed = vals + vals[:1]
            if self.markers_var.get():
                marker = marker_cycle[series_idx % len(marker_cycle)]
            else:
                marker = None
            # Vary line width so that overlaid series remain visually
            # separable where lines coincide: earlier (lower index) series
            # are drawn thicker and therefore visible at the back; later
            # series are drawn progressively thinner and sit on top.
            base_width = 6.0
            min_width = 1.0
            if n_series > 1:
                linewidth = base_width - (base_width - min_width) * series_idx / (n_series - 1)
            else:
                linewidth = 2.5
            (line,) = ax.plot(
                angles,
                vals_closed,
                linewidth=linewidth,
                marker=marker,
                markersize=6,
                label=display_labels[series_idx],
                zorder=2 + series_idx,
            )
            line_artists.append(line)
            if self.fill_var.get() and not any(math.isnan(v) for v in vals_closed):
                ax.fill(angles, vals_closed, alpha=0.08, zorder=1)

            # Overflow markers: where the raw value exceeded max_score and
            # was clipped to the rim above, draw a small upward-pointing
            # triangle just outside the rim so readers see "this axis went
            # over 100%" rather than reading the clip as a full retention.
            colour = line.get_color()
            raw_vals = raw_vals_all[series_idx]
            for axis_idx, raw_v in enumerate(raw_vals):
                if math.isnan(raw_v) or raw_v <= max_score:
                    continue
                ax.scatter(
                    [angles[axis_idx]],
                    [max_score * 1.05],
                    marker="^",
                    color=colour,
                    s=70,
                    zorder=20,
                    edgecolors="white",
                    linewidths=0.8,
                    clip_on=False,
                )

        # Tabular display: when "Show values" is on, render the raw axis
        # scores as a table below the radar instead of annotating each
        # point. This keeps the chart itself uncluttered while preserving
        # the exact numbers.
        if show_values and hasattr(fig, "_tmx_table_ax"):
            table_ax = fig._tmx_table_ax  # type: ignore[attr-defined]
            # Compact column labels: pick the sub-metric code (e.g. "A2b",
            # "A4b", "A9a") when one is present in parentheses, otherwise
            # use the leading axis number ("A1", "A6", "A12"). Non-axis
            # parenthetical content like "(DOM)" is ignored so that A6 in
            # the table stays simply "A6".
            def _short_code(label: str) -> str:
                m = re.search(r"\((A\d+\w?)\)", label)
                if m:
                    return m.group(1)
                m = re.match(r"^(A\d+\w?)", label)
                return m.group(1) if m else label
            header_row = [_short_code(AXIS_LABELS_SHORT[a]) for a in AXIS_ORDER]
            # Build the body: one row per series, formatted values per axis.
            # Use raw (unclipped) values so that overflow (>max_score) values
            # like 198 or 200 appear in the table as-is, paired with the
            # overflow triangles drawn outside the radar rim.
            body_rows: List[List[str]] = []
            row_colours: List[str] = []
            for series_idx, raw_vals in enumerate(raw_vals_all):
                cells = []
                for v in raw_vals:
                    cells.append("—" if math.isnan(v) else f"{v:.0f}")
                body_rows.append(cells)
                row_colours.append(line_artists[series_idx].get_color())
            # Row labels mirror the legend labels for the series.
            # Compact row labels for the value table. The legend above
            # already shows the full series name, so the table can use a
            # shorter form: prefer the group code on its own when groups
            # disambiguate the series; otherwise fall back to a trimmed
            # version of the display label.
            base_labels = [s.label for s in self.series]
            label_counts2: dict[str, int] = {}
            for b in base_labels:
                label_counts2[b] = label_counts2.get(b, 0) + 1
            row_labels: List[str] = []
            for s in self.series:
                if label_counts2.get(s.label, 0) > 1 and s.group:
                    row_labels.append(s.group)
                else:
                    # Truncate long labels for the narrow row-label column.
                    short = s.label
                    if len(short) > 22:
                        short = short[:20] + "…"
                    row_labels.append(short)
            tbl = table_ax.table(
                cellText=body_rows,
                rowLabels=row_labels,
                colLabels=header_row,
                loc="center",
                cellLoc="center",
                rowLoc="left",
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(7)
            tbl.scale(1.0, 1.25)
            # Colour each row label with its series colour for quick mapping.
            for series_idx, colour in enumerate(row_colours):
                # The rowLabels live in column index -1.
                try:
                    lbl_cell = tbl[series_idx + 1, -1]  # +1 to skip header row
                    lbl_cell.get_text().set_color(colour)
                    lbl_cell.get_text().set_fontweight("bold")
                except KeyError:
                    pass
            # Bold the column headers for readability.
            for col_idx in range(len(header_row)):
                try:
                    hdr_cell = tbl[0, col_idx]
                    hdr_cell.get_text().set_fontweight("bold")
                except KeyError:
                    pass
            # Wider room for row label column (only the rows that have a label).
            for ri in range(1, len(row_labels) + 1):
                try:
                    tbl[ri, -1].set_width(0.22)
                except KeyError:
                    pass

        # Warn once per render if N/A values have been silently mapped to 0.
        if na_collapsed_to_zero:
            self.status_var.set(
                "Note: some axes are N/A but Missing/N/A is set to 0, "
                "which makes the polygon collapse on those axes. "
                "Switch to 'blank' to hide N/A points instead."
            )

        ax.set_title(self.title_var.get().strip() or "TMX Structural Retention Radar", pad=24, fontsize=13)
        # Set the radial scale. In auto mode, max_score expands beyond
        # 100 when the loaded data contain actual >100% values. A small
        # margin keeps markers and labels from touching the outer frame.
        ax.set_ylim(0, max_score * 1.08)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=8)
        if max_score <= 100:
            tick_step = 20 if max_score >= 100 else max_score / 5
        else:
            tick_step = 20
        yticks = []
        t = tick_step
        while t <= max_score + 1e-9:
            yticks.append(t)
            t += tick_step
        ax.set_yticks(yticks)
        ax.set_yticklabels([str(int(t)) if abs(t - int(t)) < 1e-9 else f"{t:.1f}" for t in yticks], fontsize=8)
        ax.grid(self.grid_var.get())

        legend_pos = self.legend_var.get()
        if legend_pos == "right":
            ax.legend(loc="center left", bbox_to_anchor=(1.10, 0.5), fontsize=8)
            # subplots_adjust conflicts with gridspec used for the value-table
            # layout, so skip it when a table is also being rendered.
            if not show_values:
                fig.subplots_adjust(right=0.76)
        elif legend_pos == "bottom":
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=8)
            if not show_values:
                fig.subplots_adjust(bottom=0.18)
        elif legend_pos == "inside":
            ax.legend(loc="upper right", fontsize=8)
        # none: no legend

        self._mount_figure(fig)
        self.status_var.set(f"Radar generated with {len(self.series)} overlaid file(s). Radial max: {max_score:.0f}.")

    def _default_export_name(self, ext: str) -> str:
        base = self.title_var.get().strip() or "tmx_radar_overlay"
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_") or "tmx_radar_overlay"
        return f"{base}.{ext}"

    def ensure_output_dir(self) -> Optional[Path]:
        if self.output_dir and self.output_dir.exists():
            return self.output_dir
        d = filedialog.askdirectory(title="Select output folder")
        if not d:
            return None
        self.output_dir = Path(d).expanduser().resolve()
        self.out_label.configure(text=str(self.output_dir))
        return self.output_dir

    def export_chart(self, ext: str) -> None:
        if not self.figure:
            messagebox.showerror("No chart", "Generate a chart first.")
            return
        out_dir = self.ensure_output_dir()
        if not out_dir:
            return
        path = out_dir / self._default_export_name(ext)
        try:
            self.figure.savefig(path, bbox_inches="tight")
            self.status_var.set(f"Exported chart: {path}")
            messagebox.showinfo("Export complete", f"Saved:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_combined_csv(self) -> None:
        if not self.series:
            messagebox.showerror("No data", "Load files first.")
            return
        out_dir = self.ensure_output_dir()
        if not out_dir:
            return
        path = out_dir / "radar_combined_scores.csv"
        try:
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["label", "source_file"] + AXIS_ORDER)
                for s in self.series:
                    writer.writerow([s.label, str(s.path)] + [s.scores.get(a) for a in AXIS_ORDER])
            self.status_var.set(f"Exported combined CSV: {path}")
            messagebox.showinfo("Export complete", f"Saved:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))


def main() -> None:
    if DND_AVAILABLE and TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = RadarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
