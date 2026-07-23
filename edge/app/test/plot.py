"""
generate_exp_charts.py
======================
Generates the 4 charts embedded in docs/EXP_RESULT.md.

Usage
-----
    python docs/scripts/generate_exp_charts.py --log edge/perf.jsonl --out docs/images/

Dependencies
------------
    pip install pandas plotly kaleido

The script reads the NDJSON telemetry file produced by the edge IDS pipeline
and writes 4 PNG files into the output directory:

    stride_fps_coverage.png       — Processed FPS vs effective source coverage
    stride_stage_latency.png      — Stacked pipeline stage latency breakdown
    stride_budget_vs_latency.png  — Stride budget vs actual frame latency
    tracker_latency_vs_tracks.png — Tracker latency vs active track count
"""

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# ── Theme ──────────────────────────────────────────────────────────────────
BG        = "#0F1117"
PLOT_BG   = "#181C27"
GRID      = "#252A3A"
FONT_COL  = "#D8DCE8"
COLORS    = ["#4CB8C4", "#F4A261", "#E76F51"]   # Stride 2, 4, 20
STAGE_COL = ["#4CB8C4", "#F4A261", "#E76F51", "#A8DADC"]
SOURCE_FPS = 25  # assumed camera frame rate


def _base_layout(title: str, subtitle: str, xtitle: str, ytitle: str) -> dict:
    return dict(
        title=dict(
            text=(
                f"<b>{title}</b><br>"
                f"<span style='font-size:13px;color:#8A90A8;font-weight:normal'>{subtitle}</span>"
            ),
            font=dict(size=18, color=FONT_COL),
            x=0.5,
            xanchor="center",
        ),
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=BG,
        font=dict(size=13, color=FONT_COL),
        xaxis=dict(
            title=dict(text=xtitle, font=dict(size=13)),
            tickfont=dict(size=12),
            gridcolor=GRID,
            linecolor=GRID,
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text=ytitle, font=dict(size=13)),
            tickfont=dict(size=12),
            gridcolor=GRID,
            linecolor=GRID,
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5,
            font=dict(size=13),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=70, r=40, t=120, b=65),
    )


def load_telemetry(log_path: str) -> pd.DataFrame:
    """Read NDJSON telemetry and return a flat DataFrame."""
    records = []
    with open(log_path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.json_normalize(records)
    df["ts"] = pd.to_datetime(df["ts"])
    return df


# ── Chart 1: Processed FPS vs Effective Source Coverage ───────────────────
def chart_fps_coverage(data_s: dict, strides: list, out: str) -> None:
    proc_fps     = [data_s[s][data_s[s]["fps"] > 0]["fps"].mean() for s in strides]
    src_coverage = [round(fps * s, 1) for fps, s in zip(proc_fps, strides)]
    labels       = [f"Stride {s}" for s in strides]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Processed FPS (logger)",
        x=labels, y=[round(v, 2) for v in proc_fps],
        marker_color=COLORS,
        text=[f"{v:.2f}" for v in proc_fps],
        textposition="outside",
        textfont=dict(size=13, color=FONT_COL),
    ))
    fig.add_trace(go.Scatter(
        name="Source Coverage (eff. fps)",
        x=labels, y=src_coverage,
        mode="lines+markers",
        line=dict(color="#E0E060", width=2.5, dash="dot"),
        marker=dict(size=10, color="#E0E060"),
        text=[f"{v:.1f} fps" for v in src_coverage],
        textposition="top center",
        textfont=dict(size=12, color="#E0E060"),
    ))
    # 25 fps reference line
    fig.add_shape(
        type="line", x0=-0.5, x1=2.5, y0=SOURCE_FPS, y1=SOURCE_FPS,
        line=dict(color="rgba(255,80,80,0.7)", width=1.5, dash="dash"),
    )
    fig.add_annotation(
        x=2.2, y=SOURCE_FPS + 0.8, text=f"{SOURCE_FPS} fps source",
        showarrow=False, font=dict(size=11, color="rgba(255,100,100,0.9)"),
    )
    fig.update_layout(**_base_layout(
        "Processed FPS vs Effective Source Coverage",
        "Processed FPS misleads — stride×fps shows only Stride 20 covers the source",
        "Frame Stride", "FPS",
    ))
    fig.update_yaxes(range=[0, 33])
    fig.write_image(os.path.join(out, "stride_fps_coverage.png"))
    print("  ✓ stride_fps_coverage.png")


# ── Chart 2: Stacked Stage Latency ────────────────────────────────────────
def chart_stage_latency(data_s: dict, strides: list, out: str) -> None:
    labels = [f"Stride {s}" for s in strides]
    stages = {
        "Inference":     [data_s[s]["stages_ms.inference"].mean()    for s in strides],
        "Tracker":       [data_s[s]["stages_ms.tracker"].mean()      for s in strides],
        "Zone Engine":   [data_s[s]["stages_ms.zone_engine"].mean()  for s in strides],
        "State Machine": [data_s[s]["stages_ms.state_machine"].mean() for s in strides],
    }

    fig = go.Figure()
    for (name, vals), col in zip(stages.items(), STAGE_COL):
        fig.add_trace(go.Bar(
            name=name, x=labels, y=[round(v, 1) for v in vals],
            marker_color=col,
            text=[f"{v:.0f}" for v in vals],
            textposition="inside",
            textfont=dict(size=12, color="#111"),
        ))
    fig.update_layout(
        barmode="stack",
        **_base_layout(
            "Pipeline Stage Latency Breakdown",
            "Inference is the fixed floor (~350 ms); tracker is the variable cost",
            "Frame Stride", "Avg Latency (ms)",
        ),
    )
    fig.write_image(os.path.join(out, "stride_stage_latency.png"))
    print("  ✓ stride_stage_latency.png")


# ── Chart 3: Budget vs Actual Latency ─────────────────────────────────────
def chart_budget_vs_latency(data_s: dict, strides: list, out: str) -> None:
    labels         = [f"Stride {s}" for s in strides]
    stride_budget  = [round(s / SOURCE_FPS * 1000) for s in strides]  # ms
    frame_ms_mean  = [round(data_s[s]["frame_ms"].mean()) for s in strides]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Frame Time Budget",
        x=labels, y=stride_budget,
        marker_color="rgba(80,200,120,0.25)",
        marker_line_color="rgba(80,200,120,0.7)",
        marker_line_width=2,
    ))
    fig.add_trace(go.Bar(
        name="Actual Frame Latency",
        x=labels, y=frame_ms_mean,
        marker_color=COLORS,
        text=[f"{v} ms" for v in frame_ms_mean],
        textposition="outside",
        textfont=dict(size=13, color=FONT_COL),
    ))
    fig.update_layout(
        barmode="overlay",
        **_base_layout(
            "Stride Budget vs Actual Frame Latency",
            "Strides 2 & 4 overflow their budget by 6.8× and 3.3×; only Stride 20 fits",
            "Frame Stride", "Time (ms)",
        ),
    )
    fig.update_yaxes(range=[0, 950])
    # Budget annotations
    for label, budget in zip(labels, stride_budget):
        fig.add_annotation(
            x=label, y=budget + 10,
            text=f"budget: {budget} ms",
            showarrow=False,
            font=dict(size=11, color="rgba(80,200,120,0.9)"),
        )
    fig.write_image(os.path.join(out, "stride_budget_vs_latency.png"))
    print("  ✓ stride_budget_vs_latency.png")


# ── Chart 4: Tracker Latency vs Active Tracks ─────────────────────────────
def chart_tracker_vs_tracks(data_s: dict, strides: list, out: str) -> None:
    fig = go.Figure()
    for s, col in zip(strides, COLORS):
        binned = (
            data_s[s]
            .groupby("active_tracks")["stages_ms.tracker"]
            .median()
            .reset_index()
        )
        fig.add_trace(go.Scatter(
            x=binned["active_tracks"],
            y=binned["stages_ms.tracker"],
            mode="lines+markers",
            name=f"Stride {s}",
            line=dict(color=col, width=2.5),
            marker=dict(size=9, color=col),
        ))
    fig.update_layout(**_base_layout(
        "Tracker Latency Scales with Active Track Count",
        "MobileNet re-ID cost per frame: each extra track adds ~100–130 ms",
        "Active Tracks", "Median Tracker Latency (ms)",
    ))
    fig.update_xaxes(dtick=1)
    fig.write_image(os.path.join(out, "tracker_latency_vs_tracks.png"))
    print("  ✓ tracker_latency_vs_tracks.png")


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate EXP_RESULT stride charts.")
    parser.add_argument(
    "--log-file",
    required=True,
    type=Path,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--strides",
        nargs="+",
        type=int,
        default=[2, 4, 20],
        help="Frame stride values to analyse (default: 2 4 20)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading telemetry from: {args.log_file}")
    df = load_telemetry(args.log_file)
    print(f"  {len(df)} records loaded")

    strides = args.strides
    data_s  = {s: df[df["config.frame_stride"] == s].copy() for s in strides}

    for s in strides:
        n = len(data_s[s])
        print(f"  Stride {s:>2}: {n} records")

    print(f"\nWriting charts to: {args.output_dir}/")
    chart_fps_coverage(data_s, strides, args.output_dir)
    chart_stage_latency(data_s, strides, args.output_dir)
    chart_budget_vs_latency(data_s, strides, args.output_dir)
    chart_tracker_vs_tracks(data_s, strides, args.output_dir)
    print("\nDone. 4 charts written.")


if __name__ == "__main__":
    main()