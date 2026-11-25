"""Placing the transmitter and the receiver by clicking on the map (pure logic)."""

from dataclasses import dataclass, replace

from radiocoverage.geo import GeoPoint, distance_km, is_in_spain

MIN_SEPARATION_KM = 0.02


@dataclass(frozen=True)
class Placement:
    tx: GeoPoint | None = None
    rx: GeoPoint | None = None
    mode: str = "tx"  # which end the next click places: "tx" or "rx"

    @property
    def complete(self) -> bool:
        return self.tx is not None and self.rx is not None

    @property
    def empty(self) -> bool:
        return self.tx is None and self.rx is None


def check_point(lat: float, lon: float) -> tuple[GeoPoint | None, str | None]:
    """The clicked point, or the key of the reason it cannot be used."""
    try:
        point = GeoPoint(round(lat, 6), round(lon, 6))
    except (TypeError, ValueError):
        return None, "planner.msg.invalid"
    if not is_in_spain(point):
        return None, "planner.msg.outside"
    return point, None


def place(state: Placement, lat: float, lon: float) -> tuple[Placement, str]:
    """Apply a click. Returns the new state and a message key describing the outcome.

    After placing the transmitter the next click places the receiver, so a link is
    built with two clicks; later clicks keep moving the end that is selected.
    """
    point, problem = check_point(lat, lon)
    if problem:
        return state, problem
    other = state.rx if state.mode == "tx" else state.tx
    if other is not None and distance_km(point, other) < MIN_SEPARATION_KM:
        return state, "planner.msg.too_close"

    if state.mode == "tx":
        new = replace(state, tx=point)
        if new.rx is None:
            new = replace(new, mode="rx")
        return new, "planner.msg.tx_placed"
    new = replace(state, rx=point)
    if new.tx is None:
        new = replace(new, mode="tx")
    return new, "planner.msg.rx_placed"


def swap(state: Placement) -> Placement:
    return replace(state, tx=state.rx, rx=state.tx)


def clear() -> Placement:
    return Placement()


def set_point(state: Placement, end: str, lat: float, lon: float) -> tuple[Placement, str | None]:
    """Set an end from typed coordinates. Returns an error message key or None."""
    try:
        point = GeoPoint(lat, lon)
    except ValueError:
        return state, "planner.msg.invalid"
    if not is_in_spain(point):
        return state, "planner.msg.outside"
    return replace(state, **{end: point}), None
