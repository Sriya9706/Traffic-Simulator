# Traffic Simulator

A modular, multi-junction traffic simulator with Dijkstra routing, traffic-light scheduling, and animated visualisation.

## Project Structure

```
traffic_sim/          ← reusable library
    __init__.py       ← public API
    road.py           ← Road (directional, capacity, queuing)
    junction.py       ← Junction (2/3/4-way, round-robin traffic lights)
    vehicle.py        ← Vehicle (source/dest, path, colour by destination)
    source_sink.py    ← Source (Poisson/constant spawning) + Sink
    engine.py         ← SimulationEngine (time-step loop + Dijkstra routing)
    visualizer.py     ← Animated GIF + static summary PNG
main.py               ← Demo 7-junction, 16-road planar network
```

## Usage

```bash
pip install matplotlib Pillow numpy
python3 main.py
```

Outputs:
- `simulation.gif`         – animated visualisation (vehicles coloured by destination)
- `simulation_summary.png` – final state + road statistics bar chart

## Library API

### Road
```python
Road(road_id, length, speed_limit, capacity, source_node, dest_node)
```
- Vehicles travel at `speed_limit` (m/s), slowed by congestion factor
- Queue forms at road end; released by destination junction/sink

### Junction
```python
Junction(node_id, x, y, green_duration=10, all_red_duration=2, throughput_per_phase=3)
```
- Round-robin traffic light: each incoming road gets `green_duration` seconds
- Up to `throughput_per_phase` vehicles admitted per green phase
- Supports 2-way, 3-way, 4-way (determined by connected roads)

### Source
```python
Source(node_id, rate, destinations, mode="poisson", x=0, y=0)
```
- `mode="poisson"` → exponential inter-arrival (λ = rate vehicles/second)
- `mode="constant"` → exactly 1/rate seconds between vehicles
- Destinations chosen uniformly at random from list

### Sink
```python
Sink(node_id, x=0, y=0)
```
- Absorbs all arriving vehicles; records travel time statistics

### SimulationEngine
```python
engine = SimulationEngine(dt=1.0)
engine.add_node(node)
engine.add_road(road)
engine.run(duration=600, record_every=2)
engine.print_statistics()
path = engine.find_path("SRC", "SNK")  # returns list of road_ids
```

## Design Decisions

| Question | Answer |
|---|---|
| How roads connect to junctions | Road holds `source_node` and `dest_node` references; junction tracks `incoming_roads` / `outgoing_roads` |
| Where queuing happens | At the **end of each road** (vehicles travel, then queue waiting for green light) |
| Scheduling at junctions | Round-robin traffic light phases; blocked if downstream road is full |
| Route discovery | Dijkstra on free-flow travel times, computed once at spawn time |
| Statistics collected | Avg wait time per road, avg queue length, throughput, avg travel time per sink, completion rate |

## Statistics (600s Demo Run)

- **83 vehicles spawned**, **66 completed** (79.5% completion rate)
- **Avg travel time**: 125s across 6 routes
- **Bottleneck**: R4 (SRC_S → J_SE) with avg queue 0.96 and 15.5s avg wait
- All 6 junctions active; traffic distributed across 3 sinks
# Traffic-Simulator
