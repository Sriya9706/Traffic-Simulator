"""
Junction module: supports 2-way, 3-way, and 4-way junctions.

Traffic light scheduling:
  Each incoming road gets a green phase in round-robin order.
  Phase duration is configurable (default 10 s green + 2 s all-red).
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .road import Road
    from .vehicle import Vehicle


class Junction:
    """
    A road junction that manages incoming and outgoing roads.

    Scheduling strategy: round-robin traffic light phases.
    During a green phase for road R, all queued vehicles on R that have a
    valid onward road are admitted (up to a per-phase throughput cap).
    """

    def __init__(
        self,
        node_id: str,
        x: float = 0.0,
        y: float = 0.0,
        green_duration: float = 10.0,
        all_red_duration: float = 2.0,
        throughput_per_phase: int = 3,
    ):
        """
        Args:
            node_id:             Unique identifier.
            x, y:                Position for visualisation.
            green_duration:      Seconds each incoming road stays green.
            all_red_duration:    Seconds between phase switches.
            throughput_per_phase: Max vehicles admitted per green phase.
        """
        self.node_id = node_id
        self.x = x
        self.y = y
        self.green_duration = green_duration
        self.all_red_duration = all_red_duration
        self.throughput_per_phase = throughput_per_phase

        self.incoming_roads: list["Road"] = []
        self.outgoing_roads: list["Road"] = []

        # Traffic light state
        self._phase_index: int = 0           # which incoming road is green
        self._phase_start: float = 0.0       # simulation time phase started
        self._in_all_red: bool = False

        # Statistics
        self.total_vehicles_processed: int = 0

    # ------------------------------------------------------------------
    # Network topology
    # ------------------------------------------------------------------

    def add_incoming(self, road: "Road"):
        self.incoming_roads.append(road)

    def add_outgoing(self, road: "Road"):
        self.outgoing_roads.append(road)

    @property
    def way(self) -> int:
        """Return junction type: 2, 3, or 4-way (based on road count)."""
        n = max(len(self.incoming_roads), len(self.outgoing_roads))
        return min(n, 4)

    # ------------------------------------------------------------------
    # Traffic light helpers
    # ------------------------------------------------------------------

    @property
    def current_green_road(self) -> Optional["Road"]:
        if not self.incoming_roads or self._in_all_red:
            return None
        return self.incoming_roads[self._phase_index % len(self.incoming_roads)]

    def _advance_phase(self, current_time: float):
        if self._in_all_red:
            self._in_all_red = False
            self._phase_index = (self._phase_index + 1) % max(1, len(self.incoming_roads))
            self._phase_start = current_time
        else:
            self._in_all_red = True
            self._phase_start = current_time

    def _phase_elapsed(self, current_time: float) -> float:
        return current_time - self._phase_start

    def get_light_state(self, road: "Road") -> str:
        """Return 'green', 'red' for a given incoming road."""
        if self._in_all_red:
            return "red"
        if self.current_green_road is road:
            return "green"
        return "red"

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------

    def step(self, current_time: float, roads: dict[str, "Road"]):
        """
        Process one simulation tick at this junction.

        Args:
            current_time: Current simulation clock.
            roads:        Dict mapping road_id → Road (full network).
        """
        if not self.incoming_roads:
            return

        # Advance traffic light phase if needed
        duration = self.all_red_duration if self._in_all_red else self.green_duration
        if self._phase_elapsed(current_time) >= duration:
            self._advance_phase(current_time)

        # Admit vehicles from the currently green road
        green_road = self.current_green_road
        if green_road is None:
            return

        admitted = 0
        while admitted < self.throughput_per_phase:
            vehicle = green_road.peek_queue()
            if vehicle is None:
                break

            # Determine next road for this vehicle
            next_road = self._resolve_next_road(vehicle, roads)

            if next_road is None:
                # Vehicle has reached its destination (this junction is its sink)
                green_road.dequeue_vehicle(current_time)
                vehicle.completion_time = current_time
                self.total_vehicles_processed += 1
                admitted += 1
                continue

            if next_road.is_full:
                break  # Can't admit – downstream road full, block this phase

            green_road.dequeue_vehicle(current_time)
            accepted = next_road.accept_vehicle(vehicle, current_time)
            if accepted:
                vehicle.advance_path()
                self.total_vehicles_processed += 1
                admitted += 1
            else:
                # Put back (shouldn't happen since we checked is_full)
                green_road._queue.appendleft(vehicle)
                break

    def _resolve_next_road(
        self, vehicle: "Vehicle", roads: dict[str, "Road"]
    ) -> Optional["Road"]:
        """
        Return the Road object that the vehicle should move to next,
        or None if the vehicle has reached its destination.
        """
        next_road_id = vehicle.next_road_id
        if next_road_id is None:
            return None
        road = roads.get(next_road_id)
        return road

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Junction({self.node_id!r}, {self.way}-way, "
            f"in={len(self.incoming_roads)}, out={len(self.outgoing_roads)})"
        )
