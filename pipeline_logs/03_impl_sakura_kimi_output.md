# Sakura AI Engine (`preview/Kimi-K2.7-Code`) Implementation Synthesis — `auraloop_vto`

## Module Synthesis 1 (`chatcmpl-9206fbc5df5e2583` — `preview/Kimi-K2.7-Code`)

 ```python
from __future__ import annotations

import threading
from collections.abc import Hashable
from dataclasses import dataclass
from enum import Enum, auto
from time import monotonic
from typing import Any


class BudgetError(Exception):
    """Base class for ledger errors."""


class InvalidUnitsError(BudgetError, ValueError):
    """Raised when a unit value is not a positive integer."""


class DuplicateReservationError(BudgetError):
    """Raised when a task already has an active reservation."""


class ReservationNotFoundError(BudgetError):
    """Raised when a task reservation cannot be found."""


class InsufficientBudgetError(BudgetError):
    """Raised when a reservation would exceed total_units."""


class HardCeilingError(BudgetError):
    """Raised when a commit would exceed hard_ceiling."""


class _Status(Enum):
    RESERVED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True, slots=True)
class _Reservation:
    units: int
    status: _Status
    reason: str | None = None
    marked_at: float | None = None


class UnitBudgetLedger:
    """
    Thread-safe budget ledger.

    - ``total_units`` is the maximum units that may be reserved at once.
    - ``hard_ceiling`` is the maximum units that may ever be committed.
    - Unknown submission states are recorded but never auto-rolled back.
    """

    def __init__(self, total_units: int = 1000, hard_ceiling: int = 950) -> None:
        if not isinstance(total_units, int) or total_units < 0:
            raise InvalidUnitsError("total_units must be a non-negative integer")
        if not isinstance(hard_ceiling, int) or not (0 <= hard_ceiling <= total_units):
            raise InvalidUnitsError("hard_ceiling must be an integer between 0 and total_units")

        self._total = total_units
        self._ceiling = hard_ceiling
        self._committed = 0
        self._reserved = 0
        self._lock = threading.RLock()
        self._reservations: dict[Hashable, _Reservation] = {}

    # --------------------------------------------------------------------- #
    # Read-only properties
    # --------------------------------------------------------------------- #
    @property
    def total_units(self) -> int:
        with self._lock:
            return self._total

    @property
    def hard_ceiling(self) -> int:
        with self._lock:
            return self._ceiling

    @property
    def committed_units(self) -> int:
        with self._lock:
            return self._committed

    @property
    def reserved_units(self) -> int:
        with self._lock:
            return self._reserved

    @property
    def available_units(self) -> int:
        with self._lock:
            return self._total - self._committed - self._reserved

    @property
    def remaining_ceiling(self) -> int:
        with self._lock:
            return self._ceiling - self._committed

    @property
    def unknown_reservations(self) -> dict[Hashable, tuple[int, str | None]]:
        """Snapshot of currently unknown reservations: {task_id: (units, reason)}."""
        with self._lock:
            return {
                task_id: (res.units, res.reason)
                for task_id, res in self._reservations.items()
                if res.status is _Status.UNKNOWN
            }

    # --------------------------------------------------------------------- #
    # Core operations
    # --------------------------------------------------------------------- #
    def reserve(self, task_id: Hashable, units: int) -> None:
        """
        Reserve ``units`` for ``task_id``.

        Raises:
            InvalidUnitsError: if ``units`` is not a positive integer.
            DuplicateReservationError: if ``task_id`` already has a reservation.
            InsufficientBudgetError: if the reservation exceeds ``total_units``.
        """
        if not isinstance(units, int) or units <= 0:
            raise InvalidUnitsError("units must be a positive integer")

        with self._lock:
            if task_id in self._reservations:
                raise DuplicateReservationError(f"task_id {task_id!r} already reserved")

            if self._committed + self._reserved + units > self._total:
                raise InsufficientBudgetError(
                    f"cannot reserve {units}; available={self._total - self._committed - self._reserved}"
                )

            self._reservations[task_id] = _Reservation(units=units, status=_Status.RESERVED)
            self._reserved += units

    def commit(self, task_id: Hashable) -> None:
        """
        Commit a previously reserved amount.

        Raises:
            ReservationNotFoundError: if ``task_id`` has no reservation.
            HardCeilingError: if committing would exceed ``hard_ceiling``.
        """
        with self._lock:
            reservation = self._reservations.get(task_id)
            if reservation is None:
                raise ReservationNotFoundError(f"no reservation for task_id {task_id!r}")

            if self._committed + reservation.units > self._ceiling:
                raise HardCeilingError(
                    f"committing {reservation.units} would exceed hard_ceiling {self._ceiling}"
                )

            self._committed += reservation.units
            self._reserved -= reservation.units
            del self._reservations[task_id]

    def rollback(self, task_id: Hashable) -> None:
        """
       

## Module Synthesis 2 (`chatcmpl-ad1318e7e5a69da6` — `preview/Kimi-K2.7-Code`)

 ```python
import math


def _srgb_inverse_gamma(c: float) -> float:
    """Convert an sRGB component from gamma-compressed [0, 1] to linear light."""
    return c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4)


def srgb_hex_to_cielab(hex_color: str) -> tuple[float, float, float]:
    """
    Convert an sRGB hex color (e.g. '#1a2b3c' or '1a2b3c') to CIELAB D65.
    Returns (L*, a*, b*).
    """
    hex_color = hex_color.lstrip("#").strip().lower()

    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    if len(hex_color) != 6 or not all(ch in "0123456789abcdef" for ch in hex_color):
        raise ValueError(f"Invalid hex color: {hex_color!r}")

    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    r = _srgb_inverse_gamma(r)
    g = _srgb_inverse_gamma(g)
    b = _srgb_inverse_gamma(b)

    # sRGB D65 -> XYZ
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    # D65 reference white
    xn, yn, zn = 95.047, 100.0, 108.883

    def f(t: float) -> float:
        delta = 6 / 29
        if t > delta**3:
            return math.cbrt(t)
        return t / (3 * delta**2) + 16 / 116

    l_star = 116.0 * f(y / yn) - 16.0
    a_star = 500.0 * (f(x / xn) - f(y / yn))
    b_star = 200.0 * (f(y / yn) - f(z / zn))

    return l_star, a_star, b_star


def ciede2000_delta_e(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
) -> float:
    """
    Compute the CIEDE2000 color difference between two CIELAB colors.
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0

    g = 0.5 * (1.0 - math.sqrt(c_bar**7 / (c_bar**7 + 25.0**7)))

    a1p = a1 * (1.0 + g)
    a2p = a2 * (1.0 + g)

    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0

    d_l = l2 - l1
    d_c = c2p - c1p

    d_h = 0.0
    if c1p * c2p != 0.0:
        diff = h2p - h1p
        if abs(diff) <= 180.0:
            d_h = diff
        elif diff > 180.0:
            d_h = diff - 360.0
        else:
            d_h = diff + 360.0

    d_h = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_h / 2.0))

    l_bar = (l1 + l2) / 2.0
    c_bar_p = (c1p + c2p) / 2.0

    if c1p * c2p == 0.0:
        h_bar_p = h1p + h2p
    else:
        h_sum = h1p + h2p
        if abs(h1p - h2p) <= 180.0:
            h_bar_p = h_sum / 2.0
        elif h_sum < 360.0:
            h_bar_p = (h_sum + 360.0) / 2.0
        else:
            h_bar_p = (h_sum - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_p - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_p))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_p + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_p - 63.0))
    )

    d_theta = 30.0 * math.exp(-((h_bar_p - 275.0) / 25.0) ** 2)
    r_c = 2.0 * math.sqrt(c_bar_p**7 / (c_bar_p**7 + 25.0**7))

    s_l = 1.0 + (0.015 * (l_bar - 50.0) ** 2) / math.sqrt(20.0 + (l_bar - 50.0) ** 2)
    s_c = 1.0 + 0.045 * c_bar_p
    s_h = 1.0 + 0.015 * c_bar_p * t

    r_t = -math.sin(math.radians(2.0 * d_theta)) * r_c

    term_l = d_l / s_l
    term_c = d_c / s_c
    term_h = d_h / s_h

    return math.sqrt(
        term_l**2 + term_c**2 + term_h**2 + r_t * term_c * term_h
    )

