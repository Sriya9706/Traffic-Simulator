"""
Road module: directional roads with capacity and vehicle queuing.
"""
from collections import deque
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .vehicle import Vehicle
    from .junction import Junction


class Road:
    """
    A directional road connecting two junctions (or a source/sink).
    Vehicles travel along the road and queue at the end before entering
    the next junction.
    """

    def __init__(
        self,
        road_id: str,
        length: float,
        speed_limit: float,
        capacity: int,
        source_node,
        dest_node,
    ):
        """
        Args:
            road_id:     Unique identifier for the road.
            length:      Length of the road in metres.
            speed_limit: Maximum speed in m/s.
            capacity:    Max number of vehicles on the road simultaneously.
            source_node: Junction/Source the road starts at.
            dest_node:   Junction/Sink the road ends at.
        """
        self.road_id = road_id
        self.length = length
        self.speed_limit = speed_limit
        self.capacity = capacity
        self.source_node = source_node
        self.dest_node = dest_node

        # Travel time at free-flow speed (seconds)
        self.free_flow_time: float = length / speed_limit

        # Vehicles currently travelling on the road: list of (vehicle, arrival_time)
        # arrival_time = simulation time when the vehicle reaches the end of the road
        self._travelling: list[tuple["Vehicle", float]] = []

        # Queue at the end of the road waiting to enter dest_node
        self._queue: deque["Vehicle"] = deque()

        # Statistics
        self.total_vehicles_passed: int = 0
        self.total_wait_time: float = 0.0
        self._queue_length_samples: list[int] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def occupancy(self) -> int:
        """Number of vehicles on road (travelling + queued)."""
        return len(self._travelling) + len(self._queue)

    @property
    def is_full(self) -> bool:
        return self.occupancy >= self.capacity

    @property
    def queue_length(self) -> int:
        return len(self._queue)

    @property
    def travelling_count(self) -> int:
        return len(self._travelling)

    # ------------------------------------------------------------------
    # Vehicle management
    # ------------------------------------------------------------------

    def accept_vehicle(self, vehicle: "Vehicle", current_time: float) -> bool:
        """
        Try to place a vehicle onto this road.
        Returns True if accepted, False if road is full.
        """
        if self.is_full:
            return False

        # Compute effective travel time (increases with congestion)
        congestion_factor = 1.0 + 0.5 * (self.occupancy / self.capacity)
        travel_time = self.free_flow_time * congestion_factor
        arrival_time = current_time + travel_time

        self._travelling.append((vehicle, arrival_time))
        vehicle.enter_road(self, current_time)
        return True

    def step(self, current_time: float):
        """
        Advance simulation: move vehicles that have arrived to the queue.
        """
        self._queue_length_samples.append(self.queue_length)

        still_travelling = []
        for vehicle, arrival_time in self._travelling:
            if current_time >= arrival_time:
                self._queue.append(vehicle)
                vehicle.reach_road_end(current_time)
            else:
                still_travelling.append((vehicle, arrival_time))
        self._travelling = still_travelling

    def dequeue_vehicle(self, current_time: float) -> Optional["Vehicle"]:
        """
        Remove and return the front vehicle from the queue (called by dest_node).
        """
        if self._queue:
            vehicle = self._queue.popleft()
            wait = current_time - vehicle.road_end_time
            self.total_wait_time += wait
            self.total_vehicles_passed += 1
            return vehicle
        return None

    def peek_queue(self) -> Optional["Vehicle"]:
        """Return front vehicle without removing."""
        return self._queue[0] if self._queue else None

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    @property
    def avg_queue_length(self) -> float:
        if not self._queue_length_samples:
            return 0.0
        return sum(self._queue_length_samples) / len(self._queue_length_samples)

    @property
    def avg_wait_time(self) -> float:
        if self.total_vehicles_passed == 0:
            return 0.0
        return self.total_wait_time / self.total_vehicles_passed

    def __repr__(self) -> str:
        return (
            f"Road({self.road_id!r}, {self.source_node.node_id!r} → "
            f"{self.dest_node.node_id!r}, "
            f"len={self.length}m, occ={self.occupancy}/{self.capacity})"
        )
