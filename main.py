#!/usr/bin/env python3
"""
main.py – Assignment 6 network.

Grid of 4 junctions (2×2), bi-directional roads (modelled as two
one-way roads), 3 sources and 2 sinks as per the provided diagram.

Junction layout (x, y):
    J_TL (top-left)    J_TR (top-right)
    J_ML (mid-left)    J_MR (mid-right)
    J_BL (bot-left)    J_BR (bot-right)

Sources (also act as sinks for return traffic, handled via separate nodes):
    SRC_S1S4  – top-left     (sends to K2, K1K5, K3K4)
    SRC_S2S5  – mid-left     (sends to K2, K1K5, K3K4)
    SRC_S3    – mid-right    (sends to K2, K1K5, K3K4)

Sinks:
    SNK_K2    – top-right
    SNK_K1K5  – bot-right
    SNK_K3K4  – bot-left

All horizontal and vertical roads are bi-directional (one lane each way).
Traffic intensity tuned to demonstrate maximum coherent density.

Usage:
    python3 main.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from traffic_sim import (
    Road, Junction, Source, Sink,
    SimulationEngine, make_gif, make_static_summary,
)


def make_road(engine, road_id, src_node, dst_node,
              length=300, speed=10, capacity=8):
    road = Road(road_id, length, speed, capacity, src_node, dst_node)
    engine.add_road(road)
    return road


def build_network(engine: SimulationEngine):
    """
    Network from assignment diagram.

    Coordinate system (matches diagram x→right, y→up, normalised 0-1):

        S1S4(0.05,0.85) ── J_TL(0.35,0.85) ──────── J_TR(0.65,0.85) ── K2(0.95,0.85)
                                │                           │
        S2S5(0.05,0.50) ── J_ML(0.35,0.50) ──────── J_MR(0.65,0.50) ── S3(0.95,0.50)
                                │                           │
                           J_BL(0.35,0.15) ──────── J_BR(0.65,0.15)
                                │                           │
                           K3K4(0.05,0.15)             K1K5(0.95,0.15)
    """

    # ── Junctions ────────────────────────────────────────────────
    j_tl = Junction("J_TL", x=0.35, y=0.85, green_duration=8,  all_red_duration=2, throughput_per_phase=4)
    j_tr = Junction("J_TR", x=0.65, y=0.85, green_duration=8,  all_red_duration=2, throughput_per_phase=4)
    j_ml = Junction("J_ML", x=0.35, y=0.50, green_duration=10, all_red_duration=2, throughput_per_phase=4)
    j_mr = Junction("J_MR", x=0.65, y=0.50, green_duration=10, all_red_duration=2, throughput_per_phase=4)
    j_bl = Junction("J_BL", x=0.35, y=0.15, green_duration=8,  all_red_duration=2, throughput_per_phase=4)
    j_br = Junction("J_BR", x=0.65, y=0.15, green_duration=8,  all_red_duration=2, throughput_per_phase=4)

    # ── Sources ───────────────────────────────────────────────────
    # Each source label carries two traffic streams (e.g. S1 and S4)
    # so rate is doubled accordingly. Destinations are all 3 sinks.
    all_sinks = ["K2", "K1K5", "K3K4"]

    src_s1s4 = Source("S1+S4", rate=0.14, destinations=all_sinks,
                      mode="poisson", x=0.05, y=0.85)
    src_s2s5 = Source("S2+S5", rate=0.14, destinations=all_sinks,
                      mode="poisson", x=0.05, y=0.50)
    src_s3   = Source("S3",    rate=0.10, destinations=all_sinks,
                      mode="poisson", x=0.95, y=0.50)

    # ── Sinks ─────────────────────────────────────────────────────
    snk_k2   = Sink("K2",   x=0.95, y=0.85)
    snk_k1k5 = Sink("K1K5", x=0.95, y=0.15)
    snk_k3k4 = Sink("K3K4", x=0.05, y=0.15)

    for node in [j_tl, j_tr, j_ml, j_mr, j_bl, j_br,
                 src_s1s4, src_s2s5, src_s3,
                 snk_k2, snk_k1k5, snk_k3k4]:
        engine.add_node(node)

    # ── Roads (bi-directional = two one-way roads per link) ───────
    #
    # Naming: R_<from>_<to>
    # Horizontal roads
    #   Top row:    S1S4 ↔ J_TL ↔ J_TR ↔ K2
    make_road(engine, "R_S14_TL",  src_s1s4, j_tl,    length=250, speed=12, capacity=8)
    make_road(engine, "R_TL_S14",  j_tl,  src_s1s4,   length=250, speed=12, capacity=8)  # return (for routing completeness)
    make_road(engine, "R_TL_TR",   j_tl,  j_tr,       length=300, speed=12, capacity=8)
    make_road(engine, "R_TR_TL",   j_tr,  j_tl,       length=300, speed=12, capacity=8)
    make_road(engine, "R_TR_K2",   j_tr,  snk_k2,     length=250, speed=12, capacity=8)
    make_road(engine, "R_K2_TR",   snk_k2, j_tr,      length=250, speed=12, capacity=8)  # dummy for bi-dir display

    #   Mid row:    S2S5 ↔ J_ML ↔ J_MR ↔ S3
    make_road(engine, "R_S25_ML",  src_s2s5, j_ml,    length=250, speed=12, capacity=8)
    make_road(engine, "R_ML_S25",  j_ml,  src_s2s5,   length=250, speed=12, capacity=8)
    make_road(engine, "R_ML_MR",   j_ml,  j_mr,       length=300, speed=12, capacity=8)
    make_road(engine, "R_MR_ML",   j_mr,  j_ml,       length=300, speed=12, capacity=8)
    make_road(engine, "R_MR_S3",   j_mr,  src_s3,     length=250, speed=12, capacity=8)
    make_road(engine, "R_S3_MR",   src_s3, j_mr,      length=250, speed=12, capacity=8)

    #   Bot row:    K3K4 ↔ J_BL ↔ J_BR ↔ K1K5
    make_road(engine, "R_K34_BL",  snk_k3k4, j_bl,   length=250, speed=12, capacity=8)
    make_road(engine, "R_BL_K34",  j_bl,  snk_k3k4,  length=250, speed=12, capacity=8)
    make_road(engine, "R_BL_BR",   j_bl,  j_br,       length=300, speed=12, capacity=8)
    make_road(engine, "R_BR_BL",   j_br,  j_bl,       length=300, speed=12, capacity=8)
    make_road(engine, "R_BR_K15",  j_br,  snk_k1k5,  length=250, speed=12, capacity=8)
    make_road(engine, "R_K15_BR",  snk_k1k5, j_br,   length=250, speed=12, capacity=8)

    # Vertical roads
    #   Left col:   J_TL ↔ J_ML ↔ J_BL
    make_road(engine, "R_TL_ML",   j_tl,  j_ml,       length=350, speed=10, capacity=8)
    make_road(engine, "R_ML_TL",   j_ml,  j_tl,       length=350, speed=10, capacity=8)
    make_road(engine, "R_ML_BL",   j_ml,  j_bl,       length=350, speed=10, capacity=8)
    make_road(engine, "R_BL_ML",   j_bl,  j_ml,       length=350, speed=10, capacity=8)

    #   Right col:  J_TR ↔ J_MR ↔ J_BR
    make_road(engine, "R_TR_MR",   j_tr,  j_mr,       length=350, speed=10, capacity=8)
    make_road(engine, "R_MR_TR",   j_mr,  j_tr,       length=350, speed=10, capacity=8)
    make_road(engine, "R_MR_BR",   j_mr,  j_br,       length=350, speed=10, capacity=8)
    make_road(engine, "R_BR_MR",   j_br,  j_mr,       length=350, speed=10, capacity=8)


def main():
    print("=" * 60)
    print("  TRAFFIC SIMULATOR – Assignment 6 Network")
    print("=" * 60)

    engine = SimulationEngine(dt=1.0)
    build_network(engine)

    print(f"  Nodes : {len(engine.nodes)}")
    print(f"  Roads : {len(engine.roads)}")

    # Verify all source→sink paths exist
    print("\n  Route check:")
    for src in ["S1+S4", "S2+S5", "S3"]:
        for snk in ["K2", "K1K5", "K3K4"]:
            path = engine.find_path(src, snk)
            status = "OK" if path else "NO PATH"
            print(f"    {src:6s} → {snk:5s} : {status}  {path}")

    print("\n  Running 600 s simulation...")
    engine.run(duration=600, record_every=2)

    engine.print_statistics()

    out = os.path.dirname(os.path.abspath(__file__))

    print("  Generating summary image...")
    make_static_summary(engine,
                        os.path.join(out, "simulation_summary.png"),
                        title="Assignment 6 – Traffic Network")

    print("  Generating animated GIF...")
    make_gif(engine,
             os.path.join(out, "simulation.gif"),
             fps=12, max_frames=150,
             title="Assignment 6 – Traffic Network")

    print("\n  Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
