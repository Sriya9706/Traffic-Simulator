"""
Simulation engine: time-step based discrete simulation with Dijkstra routing.
"""
import heapq
from collections import defaultdict
from typing import Optional

from .road import Road
from .junction import Junction
from .source_sink import Source, Sink
from .vehicle import Vehicle


class SimulationEngine:
    """
    Manages the entire network simulation.

    Network elements:
      nodes  – dict[node_id → Junction | Source | Sink]
      roads  – dict[road_id → Road]

    Each tick:
      1. Sources spawn vehicles (and place on first road).
      2. All roads advance (move travelling → queue).
      3. All junctions/sinks process queues.
      4. Statistics are recorded.
    """

    def __init__(self, dt: float = 1.0):
        """
        Args:
            dt: Simulation time-step in seconds.
        """
        self.dt = dt
        self.current_time: float = 0.0

        self.nodes: dict[str, Junction | Source | Sink] = {}
        self.roads: dict[str, Road] = {}

        self._all_vehicles: list[Vehicle] = []
        self._completed_vehicles: list[Vehicle] = []

        # Snapshot history for visualisation
        # Each entry: {'time': float, 'vehicles': [(vid, road_id, progress, colour), ...]}
        self.history: list[dict] = []
        self._record_every: int = 1   # record every N ticks

    # ------------------------------------------------------------------
    # Network builder API
    # ------------------------------------------------------------------

    def add_node(self, node: Junction | Source | Sink):
        self.nodes[node.node_id] = node
        if isinstance(node, Source):
            node.set_route_fn(self.find_path)

    def add_road(self, road: Road):
        self.roads[road.road_id] = road
        road.source_node.add_outgoing(road)
        road.dest_node.add_incoming(road)

    # ------------------------------------------------------------------
    # Routing (Dijkstra on road network)
    # ------------------------------------------------------------------

    def find_path(self, source_id: str, dest_id: str) -> list[str]:
        """
        Dijkstra shortest-path (by free-flow travel time) from source_id to dest_id.
        Returns ordered list of road_ids, or [] if no path exists.
        """
        if source_id == dest_id:
            return []

        # Build adjacency: node_id → [(cost, road_id, next_node_id)]
        adj: dict[str, list] = defaultdict(list)
        for road in self.roads.values():
            adj[road.source_node.node_id].append(
                (road.free_flow_time, road.road_id, road.dest_node.node_id)
            )

        dist: dict[str, float] = {source_id: 0.0}
        prev_road: dict[str, str] = {}   # node_id → road_id taken to reach it
        prev_node: dict[str, str] = {}   # node_id → previous node_id
        heap = [(0.0, source_id)]

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist.get(u, float("inf")):
                continue
            if u == dest_id:
                break
            for cost, road_id, v in adj[u]:
                nd = d + cost
                if nd < dist.get(v, float("inf")):
                    dist[v] = nd
                    prev_road[v] = road_id
                    prev_node[v] = u
                    heapq.heappush(heap, (nd, v))

        if dest_id not in prev_road and dest_id not in dist:
            return []
        if dest_id == source_id:
            return []

        # Reconstruct path
        path = []
        node = dest_id
        while node in prev_road:
            path.append(prev_road[node])
            node = prev_node[node]
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Main simulation loop
    # ------------------------------------------------------------------

    def run(self, duration: float, record_every: int = 1):
        """
        Run simulation for `duration` seconds.

        Args:
            duration:     Total simulated time in seconds.
            record_every: Record snapshot every N ticks (reduces memory).
        """
        self._record_every = record_every
        steps = int(duration / self.dt)
        tick = 0

        for _ in range(steps):
            self._tick()
            if tick % record_every == 0:
                self._record_snapshot()
            tick += 1

        self._finalise()

    def _tick(self):
        t = self.current_time

        # 1. Sources spawn vehicles
        for node in self.nodes.values():
            if isinstance(node, Source):
                new_vehicles = node.step(t, self.roads)
                self._all_vehicles.extend(new_vehicles)

        # 2. Advance roads (travelling → queue)
        for road in self.roads.values():
            road.step(t)

        # 3. Process junctions and sinks
        for node in self.nodes.values():
            if isinstance(node, (Junction, Sink)):
                node.step(t, self.roads)

        # 4. Collect completed vehicles
        for v in self._all_vehicles:
            if v.completion_time is not None and v not in self._completed_vehicles:
                self._completed_vehicles.append(v)

        self.current_time += self.dt

    def _record_snapshot(self):
        """Record current vehicle positions for animation."""
        t = self.current_time
        snapshot = {"time": t, "vehicles": []}

        for road in self.roads.values():
            # Travelling vehicles – compute progress along road
            for vehicle, arrival_time in road._travelling:
                elapsed = t - vehicle.road_enter_time
                travel_time_total = arrival_time - vehicle.road_enter_time
                progress = min(elapsed / max(travel_time_total, 1e-9), 1.0)
                snapshot["vehicles"].append({
                    "vid": vehicle.vehicle_id,
                    "road_id": road.road_id,
                    "progress": progress,
                    "colour": vehicle.colour,
                    "dest": vehicle.dest_id,
                })

            # Queued vehicles – at end of road (progress = 1.0)
            for i, vehicle in enumerate(road._queue):
                snapshot["vehicles"].append({
                    "vid": vehicle.vehicle_id,
                    "road_id": road.road_id,
                    "progress": 1.0,
                    "queue_pos": i,
                    "colour": vehicle.colour,
                    "dest": vehicle.dest_id,
                })

        self.history.append(snapshot)

    def _finalise(self):
        """Mark any remaining vehicles on network as incomplete."""
        pass  # stats available via properties

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @property
    def total_spawned(self) -> int:
        return sum(
            n.total_spawned for n in self.nodes.values() if isinstance(n, Source)
        )

    @property
    def total_completed(self) -> int:
        return len(self._completed_vehicles)

    @property
    def completion_rate(self) -> float:
        s = self.total_spawned
        return self.total_completed / s if s else 0.0

    @property
    def avg_travel_time(self) -> float:
        times = [
            v.travel_time
            for v in self._completed_vehicles
            if v.travel_time is not None
        ]
        return sum(times) / len(times) if times else 0.0

    def print_statistics(self):
        sep = "=" * 60
        print(sep)
        print("  SIMULATION STATISTICS")
        print(sep)
        print(f"  Simulated time     : {self.current_time:.1f} s")
        print(f"  Total spawned      : {self.total_spawned}")
        print(f"  Total completed    : {self.total_completed}")
        print(f"  Completion rate    : {self.completion_rate * 100:.1f}%")
        print(f"  Avg travel time    : {self.avg_travel_time:.2f} s")
        print()
        print("  Road Statistics:")
        print(f"  {'Road':<20} {'Passed':>8} {'AvgQueue':>10} {'AvgWait(s)':>12}")
        print(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*12}")
        for road in sorted(self.roads.values(), key=lambda r: r.road_id):
            print(
                f"  {road.road_id:<20} {road.total_vehicles_passed:>8} "
                f"{road.avg_queue_length:>10.2f} {road.avg_wait_time:>12.2f}"
            )
        print()
        print("  Junction Statistics:")
        for node in sorted(self.nodes.values(), key=lambda n: n.node_id):
            if isinstance(node, Junction):
                print(f"  {node.node_id}: processed {node.total_vehicles_processed} vehicles")
        print()
        print("  Sink Statistics:")
        for node in sorted(self.nodes.values(), key=lambda n: n.node_id):
            if isinstance(node, Sink):
                print(
                    f"  {node.node_id}: absorbed {node.throughput} vehicles, "
                    f"avg travel time {node.avg_travel_time:.2f} s"
                )
        print(sep)
