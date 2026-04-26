#!/usr/bin/env python3
"""
main.py – Simple 4-junction test network.

Topology:
                    SNK_N
                      ▲
                      R5
                      │
  SRC_W ──R1──► J_A ──R2──► J_B ──R3──► SNK_E
                              │
                              R4
                              ▼
                            J_C ──R6──► SNK_S
                              ▲
                              R7
                              │
                           SRC_S

4 junctions (J_A, J_B, J_C, one 3-way each)
2 sources (SRC_W, SRC_S)
3 sinks   (SNK_N, SNK_E, SNK_S)
7 roads   (R1–R7)

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
              length=200, speed=10, capacity=6):
    road = Road(road_id, length, speed, capacity, src_node, dst_node)
    engine.add_road(road)
    return road


def build_network(engine: SimulationEngine):
    # ── Nodes ────────────────────────────────────────────────────
    src_w = Source("SRC_W", rate=0.07, destinations=["SNK_N", "SNK_E", "SNK_S"],
                   mode="poisson", x=0.05, y=0.50)
    src_s = Source("SRC_S", rate=0.05, destinations=["SNK_N", "SNK_E", "SNK_S"],
                   mode="poisson", x=0.55, y=0.05)

    snk_n = Sink("SNK_N", x=0.30, y=0.95)
    snk_e = Sink("SNK_E", x=0.95, y=0.50)
    snk_s = Sink("SNK_S", x=0.95, y=0.20)

    j_a = Junction("J_A", x=0.30, y=0.50, green_duration=10)  # 2-way (W→E, branch N)
    j_b = Junction("J_B", x=0.65, y=0.50, green_duration=10)  # 3-way (from W, to E/S)
    j_c = Junction("J_C", x=0.65, y=0.20, green_duration=10)  # 3-way (from S/B, to S sink)

    for node in [src_w, src_s, snk_n, snk_e, snk_s, j_a, j_b, j_c]:
        engine.add_node(node)

    # ── Roads ────────────────────────────────────────────────────
    #          id      src     dst    len  spd  cap
    make_road(engine, "R1", src_w, j_a,  200, 10, 6)   # west entry
    make_road(engine, "R2", j_a,   j_b,  350, 10, 6)   # main east axis
    make_road(engine, "R3", j_b,   snk_e,200, 12, 6)   # east exit
    make_road(engine, "R4", j_b,   j_c,  300,  9, 6)   # south branch
    make_road(engine, "R5", j_a,   snk_n,250, 10, 6)   # north exit
    make_road(engine, "R6", j_c,   snk_s,200, 12, 6)   # south exit
    make_road(engine, "R7", src_s, j_c,  200, 10, 6)   # south entry


def main():
    print("=" * 55)
    print("  TRAFFIC SIMULATOR – simple test network")
    print("=" * 55)

    engine = SimulationEngine(dt=1.0)
    build_network(engine)

    print(f"  Nodes: {len(engine.nodes)}   Roads: {len(engine.roads)}")
    print("  Running 600 s simulation...\n")

    engine.run(duration=600, record_every=2)
    engine.print_statistics()

    out = os.path.dirname(os.path.abspath(__file__))
    make_static_summary(engine, os.path.join(out, "simulation_summary.png"),
                        title="Simple Test Network – 600 s")
    make_gif(engine, os.path.join(out, "simulation.gif"),
             fps=12, max_frames=150, title="Simple Test Network")

    print("\n  Output: simulation.gif  +  simulation_summary.png")
    print("=" * 55)


if __name__ == "__main__":
    main()
