"""Causal loader and Euclidean spatial topology for MIT CSAIL Intel Berkeley 54-mote data.

Raw data files remain outside Git under data/raw/intel_berkeley/.
No future interpolation is ever performed: missing sensor slots stay None.
"""
from collections import defaultdict
from dataclasses import dataclass
import gzip
import math
from pathlib import Path


def load_mote_locations(locs_path: Path) -> dict[int, tuple[float, float]]:
    locs: dict[int, tuple[float, float]] = {}
    for ln in locs_path.read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) == 3:
            locs[int(parts[0])] = (float(parts[1]), float(parts[2]))
    return locs


def k_nearest_neighbors(
    locs: dict[int, tuple[float, float]],
    target: int,
    k: int = 4,
    candidates: set[int] | None = None,
) -> list[tuple[int, float]]:
    """Return k nearest physical neighbors (mote_id, distance_m), excluding target."""
    if target not in locs:
        raise ValueError(f"Unknown mote {target}")
    tx, ty = locs[target]
    pool = locs.keys() if candidates is None else (m for m in candidates if m in locs)
    dists = [
        (m, math.hypot(locs[m][0] - tx, locs[m][1] - ty))
        for m in pool
        if m != target
    ]
    dists.sort(key=lambda item: (item[1], item[0]))
    return dists[:k]


@dataclass
class IntelBerkeleyDataset:
    locations: dict[int, tuple[float, float]]
    # records[date][mote] = list of (sec_of_day: float, temp_c: float, hum_rh: float) sorted chronologically
    records: dict[str, dict[int, list[tuple[float, float, float]]]]

    def causal_series(
        self,
        date: str,
        mote: int,
        start_s: int,
        end_s: int,
        step_s: int,
        max_staleness_s: float,
    ) -> list[dict]:
        """Sample a mote causally on [start_s, end_s) using ONLY obs <= t within max_staleness_s."""
        pts = self.records.get(date, {}).get(mote, [])
        n = len(pts)
        idx = 0
        last: tuple[float, float, float] | None = None
        out = []
        for t in range(start_s, end_s, step_s):
            while idx < n and pts[idx][0] <= t:
                last = pts[idx]
                idx += 1
            if last is not None and (t - last[0]) <= max_staleness_s:
                out.append(
                    dict(
                        timestamp=t,
                        temperature=last[1],
                        humidity=last[2],
                        obs_age_s=t - last[0],
                    )
                )
            else:
                out.append(
                    dict(
                        timestamp=t,
                        temperature=None,
                        humidity=None,
                        obs_age_s=None,
                    )
                )
        return out


def load_intel_berkeley(
    data_gz_path: Path,
    locs_path: Path,
    dates_filter: set[str] | None = None,
) -> IntelBerkeleyDataset:
    """Stream-parse data.txt.gz keeping only physically valid finite readings."""
    locs = load_mote_locations(locs_path)
    records: dict[str, dict[int, list[tuple[float, float, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    with gzip.open(data_gz_path, "rt", encoding="utf-8", errors="replace") as f:
        for ln in f:
            parts = ln.split()
            if len(parts) != 8:
                continue
            date_s, time_s, _, mote_s, temp_s, hum_s, _, _ = parts
            if dates_filter is not None and date_s not in dates_filter:
                continue
            try:
                mote = int(mote_s)
                if mote not in locs:
                    continue
                temp = float(temp_s)
                hum = float(hum_s)
                hh, mm, ss = time_s.split(":")
                sec = int(hh) * 3600 + int(mm) * 60 + float(ss)
            except Exception:
                continue
            if not (math.isfinite(temp) and -10.0 <= temp <= 60.0):
                continue
            if not (math.isfinite(hum) and 0.0 <= hum <= 100.0):
                continue
            records[date_s][mote].append((sec, temp, hum))

    # Ensure strictly chronological per-(date, mote) order
    clean: dict[str, dict[int, list[tuple[float, float, float]]]] = {}
    for d, by_mote in records.items():
        clean[d] = {}
        for m, pts in by_mote.items():
            pts.sort(key=lambda x: x[0])
            clean[d][m] = pts
    return IntelBerkeleyDataset(locations=locs, records=clean)
