"""
Visualizer: produces an animated GIF/MP4 of the simulation.

Requires: matplotlib, Pillow (for GIF), ffmpeg (for MP4, optional).
"""
import math
import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np

from .engine import SimulationEngine
from .junction import Junction
from .source_sink import Source, Sink
from .road import Road


def _node_pos(node) -> tuple[float, float]:
    return node.x, node.y


def _road_endpoints(road: Road):
    sx, sy = _node_pos(road.source_node)
    dx, dy = _node_pos(road.dest_node)
    return sx, sy, dx, dy


def _offset_road(sx, sy, dx, dy, offset=0.018):
    """Offset parallel roads so they don't overlap."""
    angle = math.atan2(dy - sy, dx - sx)
    perp = angle + math.pi / 2
    ox = math.cos(perp) * offset
    oy = math.sin(perp) * offset
    return sx + ox, sy + oy, dx + ox, dy + oy


def render_frame(
    ax,
    engine: SimulationEngine,
    snapshot: dict,
    title: str = "",
    show_labels: bool = True,
):
    ax.clear()
    ax.set_facecolor("#1a1a2e")

    # --- Draw roads -------------------------------------------------------
    road_objects = engine.roads

    for road in road_objects.values():
        sx, sy, dx, dy = _road_endpoints(road)
        osx, osy, odx, ody = _offset_road(sx, sy, dx, dy)

        # Road line
        ax.annotate(
            "",
            xy=(odx, ody),
            xytext=(osx, osy),
            arrowprops=dict(
                arrowstyle="-|>",
                color="#4a4a6a",
                lw=2,
                mutation_scale=12,
            ),
        )

        if show_labels:
            mid_x = (osx + odx) / 2
            mid_y = (osy + ody) / 2
            ax.text(
                mid_x, mid_y, road.road_id,
                fontsize=5, color="#6a6a9a",
                ha="center", va="center",
            )

    # --- Draw nodes -------------------------------------------------------
    for node in engine.nodes.values():
        x, y = node.x, node.y
        if isinstance(node, Junction):
            shape = plt.Circle((x, y), 0.025, color="#16213e", zorder=5)
            ax.add_patch(shape)
            ax.text(x, y, node.node_id, fontsize=7, color="#e0e0ff",
                    ha="center", va="center", zorder=6, fontweight="bold")
            # Traffic light colour
            green_road = node.current_green_road
            if green_road:
                tl_colour = "#00ff88"
            else:
                tl_colour = "#ff4444"
            ax.plot(x + 0.035, y + 0.035, "o", color=tl_colour,
                    markersize=5, zorder=7)
        elif isinstance(node, Source):
            ax.plot(x, y, "^", color="#FFE66D", markersize=10, zorder=5)
            ax.text(x, y - 0.05, node.node_id, fontsize=7, color="#FFE66D",
                    ha="center", va="top", zorder=6)
        elif isinstance(node, Sink):
            ax.plot(x, y, "s", color="#FF6B6B", markersize=10, zorder=5)
            ax.text(x, y - 0.05, node.node_id, fontsize=7, color="#FF6B6B",
                    ha="center", va="top", zorder=6)

    # --- Draw vehicles ----------------------------------------------------
    road_vehicle_groups: dict[str, list] = {}
    for vdata in snapshot["vehicles"]:
        rid = vdata["road_id"]
        if rid not in road_vehicle_groups:
            road_vehicle_groups[rid] = []
        road_vehicle_groups[rid].append(vdata)

    for rid, vlist in road_vehicle_groups.items():
        road = road_objects.get(rid)
        if road is None:
            continue
        sx, sy, dx, dy = _road_endpoints(road)
        osx, osy, odx, ody = _offset_road(sx, sy, dx, dy)

        for vdata in vlist:
            p = vdata["progress"]
            vx = osx + p * (odx - osx)
            vy = osy + p * (ody - osy)
            # Queue offset: stack vehicles perpendicular at the end
            if "queue_pos" in vdata:
                angle = math.atan2(ody - osy, odx - osx) + math.pi / 2
                q = vdata["queue_pos"]
                vx += math.cos(angle) * 0.012 * q
                vy += math.sin(angle) * 0.012 * q

            colour = vdata["colour"]
            ax.plot(vx, vy, "o", color=colour, markersize=5,
                    zorder=10, alpha=0.9,
                    markeredgecolor="white", markeredgewidth=0.3)

    # --- Legend (destinations) --------------------------------------------
    from .vehicle import Vehicle as Veh
    legend_patches = []
    for dest_id, colour in Veh._dest_colours.items():
        legend_patches.append(mpatches.Patch(color=colour, label=f"→ {dest_id}"))
    if legend_patches:
        ax.legend(
            handles=legend_patches,
            loc="upper right",
            fontsize=6,
            framealpha=0.3,
            facecolor="#1a1a2e",
            edgecolor="#4a4a6a",
            labelcolor="white",
        )

    # Node type legend
    src_patch = mpatches.Patch(color="#FFE66D", label="Source ▲")
    snk_patch = mpatches.Patch(color="#FF6B6B", label="Sink ■")
    jct_patch = mpatches.Patch(color="#e0e0ff", label="Junction ●")
    ax.legend(
        handles=legend_patches + [src_patch, snk_patch, jct_patch],
        loc="upper left",
        fontsize=6,
        framealpha=0.3,
        facecolor="#1a1a2e",
        edgecolor="#4a4a6a",
        labelcolor="white",
    )

    # --- Stats bar --------------------------------------------------------
    completed = engine.total_completed
    spawned = engine.total_spawned
    total_q = sum(r.queue_length for r in road_objects.values())
    ax.set_title(
        f"{title}  |  t={snapshot['time']:.1f}s  |  "
        f"vehicles: {spawned} spawned, {completed} completed  |  "
        f"queue: {total_q}",
        fontsize=8, color="#c0c0e0", pad=6,
    )

    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_aspect("equal")
    ax.axis("off")


def make_gif(
    engine: SimulationEngine,
    output_path: str = "simulation.gif",
    fps: int = 10,
    max_frames: int = 200,
    title: str = "Traffic Simulation",
):
    """
    Render the simulation history as an animated GIF.

    Args:
        engine:      Completed SimulationEngine with history populated.
        output_path: Output file path.
        fps:         Frames per second.
        max_frames:  Cap frames to keep file size manageable.
    """
    from PIL import Image as PilImage

    history = engine.history
    # Subsample if too many frames
    if len(history) > max_frames:
        step = len(history) // max_frames
        history = history[::step]

    fig, ax = plt.subplots(figsize=(9, 7))
    fig.patch.set_facecolor("#1a1a2e")

    frames = []
    print(f"  Rendering {len(history)} frames...")
    for i, snapshot in enumerate(history):
        render_frame(ax, engine, snapshot, title=title)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor="#1a1a2e")
        buf.seek(0)
        frames.append(PilImage.open(buf).copy())
        buf.close()
        if (i + 1) % 20 == 0:
            print(f"    {i+1}/{len(history)} frames done")

    plt.close(fig)

    duration_ms = int(1000 / fps)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=duration_ms,
        loop=0,
    )
    print(f"  GIF saved: {output_path}  ({len(frames)} frames @ {fps} fps)")


def make_static_summary(
    engine: SimulationEngine,
    output_path: str = "summary.png",
    title: str = "Traffic Simulation – Final State",
):
    """
    Save a single static image of the final network state.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#1a1a2e")

    # Left: final network snapshot
    ax = axes[0]
    if engine.history:
        render_frame(ax, engine, engine.history[-1], title=title)
    else:
        ax.set_facecolor("#1a1a2e")
        ax.text(0.5, 0.5, "No history", color="white", ha="center", transform=ax.transAxes)

    # Right: bar charts
    ax2 = axes[1]
    ax2.set_facecolor("#16213e")

    road_ids = [r.road_id for r in engine.roads.values()]
    wait_times = [r.avg_wait_time for r in engine.roads.values()]
    queue_lens = [r.avg_queue_length for r in engine.roads.values()]

    x = np.arange(len(road_ids))
    width = 0.35

    bars1 = ax2.bar(x - width/2, wait_times, width, label="Avg Wait (s)",
                    color="#4ECDC4", alpha=0.8)
    bars2 = ax2.bar(x + width/2, queue_lens, width, label="Avg Queue Len",
                    color="#FF6B6B", alpha=0.8)

    ax2.set_xticks(x)
    ax2.set_xticklabels(road_ids, rotation=45, ha="right", fontsize=7, color="#c0c0e0")
    ax2.set_ylabel("Value", color="#c0c0e0")
    ax2.set_title("Road Statistics", color="#c0c0e0", fontsize=10)
    ax2.tick_params(colors="#c0c0e0")
    ax2.spines[:].set_color("#4a4a6a")
    ax2.legend(fontsize=7, framealpha=0.3, facecolor="#1a1a2e",
               edgecolor="#4a4a6a", labelcolor="white")
    ax2.set_facecolor("#16213e")

    fig.suptitle(
        f"Spawned: {engine.total_spawned}  |  "
        f"Completed: {engine.total_completed}  |  "
        f"Avg Travel Time: {engine.avg_travel_time:.1f}s",
        color="#e0e0ff", fontsize=10,
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    print(f"  Summary image saved: {output_path}")
