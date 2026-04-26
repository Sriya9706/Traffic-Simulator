"""
Vehicle module: individual vehicles with source, destination, and routing.
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .road import Road


_VEHICLE_COUNTER = 0


def _next_id() -> int:
    global _VEHICLE_COUNTER
    _VEHICLE_COUNTER += 1
    return _VEHICLE_COUNTER


class Vehicle:
    """
    A single vehicle travelling through the network.
    Holds a pre-computed path (list of road IDs) from source to destination.
    """

    # Colour palette – assigned per unique destination ID
    _dest_colours: dict[str, str] = {}
    _colour_pool = [
        "#FF6B6B", "#4ECDC4", "#FFE66D", "#A8E6CF",
        "#FF8B94", "#B39DDB", "#80DEEA", "#FFCC80",
        "#F48FB1", "#AED581", "#90CAF9", "#FFAB91",
    ]

    def __init__(
        self,
        source_id: str,
        dest_id: str,
        path: list[str],          # ordered list of road IDs
        spawn_time: float,
    ):
        self.vehicle_id: int = _next_id()
        self.source_id = source_id
        self.dest_id = dest_id
        self.path: list[str] = path          # road IDs from source to sink
        self.path_index: int = 0             # index of next road to take

        self.spawn_time: float = spawn_time
        self.completion_time: Optional[float] = None

        # Road-level tracking
        self.current_road: Optional["Road"] = None
        self.road_enter_time: float = 0.0
        self.road_end_time: float = 0.0      # when vehicle reached end of current road

        # Colour
        if dest_id not in Vehicle._dest_colours:
            idx = len(Vehicle._dest_colours) % len(Vehicle._colour_pool)
            Vehicle._dest_colours[dest_id] = Vehicle._colour_pool[idx]
        self.colour: str = Vehicle._dest_colours[dest_id]

        # Position for visualisation (set by engine each step)
        self.vis_x: float = 0.0
        self.vis_y: float = 0.0
        self.vis_road: Optional[str] = None  # road_id vehicle is on
        self.vis_progress: float = 0.0       # 0..1 along current road

    # ------------------------------------------------------------------
    # Road lifecycle callbacks
    # ------------------------------------------------------------------

    def enter_road(self, road: "Road", current_time: float):
        self.current_road = road
        self.road_enter_time = current_time
        self.vis_road = road.road_id

    def reach_road_end(self, current_time: float):
        self.road_end_time = current_time

    def advance_path(self) -> Optional[str]:
        """
        Move to next road in path. Returns next road_id or None if at destination.
        """
        self.path_index += 1
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    @property
    def next_road_id(self) -> Optional[str]:
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    @property
    def travel_time(self) -> Optional[float]:
        if self.completion_time is not None:
            return self.completion_time - self.spawn_time
        return None

    def __repr__(self) -> str:
        return (
            f"Vehicle({self.vehicle_id}, {self.source_id}→{self.dest_id}, "
            f"path={self.path}, idx={self.path_index})"
        )
