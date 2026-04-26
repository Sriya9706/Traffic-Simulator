"""
Source and Sink nodes for the traffic network.

Source: generates vehicles at a configurable rate (constant or Poisson).
Sink:   absorbs arriving vehicles and records completion statistics.
"""
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .road import Road
    from .vehicle import Vehicle


# ---------------------------------------------------------------------------
# Base node (shared interface with Junction)
# ---------------------------------------------------------------------------

class _Node:
    def __init__(self, node_id: str, x: float = 0.0, y: float = 0.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.incoming_roads: list["Road"] = []
        self.outgoing_roads: list["Road"] = []

    def add_incoming(self, road: "Road"):
        self.incoming_roads.append(road)

    def add_outgoing(self, road: "Road"):
        self.outgoing_roads.append(road)


# ---------------------------------------------------------------------------
# Sink
# ---------------------------------------------------------------------------

class Sink(_Node):
    """
    Absorbs vehicles that have completed their journey.
    A Sink is a valid destination node.
    """

    def __init__(self, node_id: str, x: float = 0.0, y: float = 0.0):
        super().__init__(node_id, x, y)
        self.absorbed_vehicles: list["Vehicle"] = []

    def step(self, current_time: float, roads: dict[str, "Road"]):
        """Drain all queues on incoming roads."""
        for road in self.incoming_roads:
            while road.peek_queue() is not None:
                vehicle = road.dequeue_vehicle(current_time)
                if vehicle is not None:
                    vehicle.completion_time = current_time
                    self.absorbed_vehicles.append(vehicle)

    @property
    def throughput(self) -> int:
        return len(self.absorbed_vehicles)

    @property
    def avg_travel_time(self) -> float:
        times = [v.travel_time for v in self.absorbed_vehicles if v.travel_time is not None]
        return sum(times) / len(times) if times else 0.0

    def __repr__(self) -> str:
        return f"Sink({self.node_id!r}, absorbed={self.throughput})"


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------

class Source(_Node):
    """
    Generates vehicles and places them onto outgoing roads.

    Rate modes:
      'constant'  – exactly one vehicle every (1/rate) seconds.
      'poisson'   – inter-arrival times ~ Exp(rate).
    """

    def __init__(
        self,
        node_id: str,
        rate: float,                    # vehicles per second
        destinations: list[str],        # list of sink node_ids to choose from
        mode: str = "poisson",          # 'constant' or 'poisson'
        x: float = 0.0,
        y: float = 0.0,
        seed: Optional[int] = None,
    ):
        super().__init__(node_id, x, y)
        self.rate = rate
        self.destinations = destinations
        self.mode = mode
        self._rng = random.Random(seed)

        self._next_spawn_time: float = 0.0
        self.spawned_vehicles: list["Vehicle"] = []

        # Routing callback – set by the engine
        self._route_fn = None  # fn(source_id, dest_id) -> list[str] (road ids)

    def set_route_fn(self, fn):
        self._route_fn = fn

    def _sample_inter_arrival(self) -> float:
        if self.rate <= 0:
            return float("inf")
        if self.mode == "constant":
            return 1.0 / self.rate
        # Poisson process → exponential inter-arrivals
        return self._rng.expovariate(self.rate)

    def step(self, current_time: float, roads: dict[str, "Road"]) -> list["Vehicle"]:
        """
        Spawn due vehicles and attempt to place them on an outgoing road.
        Returns list of newly spawned Vehicle objects.
        """
        from .vehicle import Vehicle  # local import to avoid circular

        newly_spawned = []

        while current_time >= self._next_spawn_time:
            dest_id = self._rng.choice(self.destinations)

            # Build route
            path = []
            if self._route_fn is not None:
                path = self._route_fn(self.node_id, dest_id)

            if not path:
                # No valid route – skip this vehicle
                self._next_spawn_time += self._sample_inter_arrival()
                continue

            vehicle = Vehicle(
                source_id=self.node_id,
                dest_id=dest_id,
                path=path,
                spawn_time=self._next_spawn_time,
            )

            # Try to place on first road
            first_road = roads.get(path[0])
            if first_road is not None and first_road.accept_vehicle(vehicle, current_time):
                vehicle.advance_path()
                self.spawned_vehicles.append(vehicle)
                newly_spawned.append(vehicle)
            # If road is full, vehicle is lost (dropped) – could queue here too

            self._next_spawn_time += self._sample_inter_arrival()

        return newly_spawned

    @property
    def total_spawned(self) -> int:
        return len(self.spawned_vehicles)

    def __repr__(self) -> str:
        return (
            f"Source({self.node_id!r}, rate={self.rate}/s, "
            f"dests={self.destinations}, spawned={self.total_spawned})"
        )
