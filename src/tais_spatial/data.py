"""Read-only XLSX provenance ledger and explicit proxy-clock as-of queries."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from .io import gzip_text

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EPOCH = datetime(1970, 1, 1)
HEADERS = ["Date", "Time", "Onboard Temperature", "Onboard Humidity", "RSSI", "SNR"]


def seconds(value: str) -> int:
    """Naive proxy axis, deliberately independent of the machine's timezone."""
    return int((datetime.fromisoformat(value) - EPOCH).total_seconds())


def position(node: int) -> tuple[int, int]:
    if node not in range(16, 43):
        raise ValueError("Unmapped AF node")
    return (node - 16) % 3, (node - 16) // 3


def neighbors(node: int, count: int = 4) -> list[int]:
    r, c = position(node)
    return sorted((j for j in range(16, 43) if j != node),
                  key=lambda j: (abs(position(j)[0] - r) + abs(position(j)[1] - c), j))[:count]


def proxy_timestamp(date, time, date1904=False):
    if date is None or time is None:
        return None
    origin = datetime(1904, 1, 1) if date1904 else datetime(1899, 12, 30)
    try:
        day = origin + timedelta(days=int(float(date)))
    except (ValueError, TypeError):
        day = datetime.fromisoformat(str(date)).replace(hour=0, minute=0, second=0)
    try:
        offset = round(float(time) * 86400)
    except (ValueError, TypeError):
        parsed = datetime.strptime(str(time), "%H:%M:%S").time()
        offset = parsed.hour * 3600 + parsed.minute * 60 + parsed.second
    return int(((day + timedelta(seconds=offset)) - EPOCH).total_seconds())


def number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


def prepare(workbook: Path, output: Path, config: dict) -> dict:
    """Exclusive outputs; preserve every nonempty original AF row in a ledger."""
    sha = hashlib.sha256(workbook.read_bytes()).hexdigest()
    if sha != config["workbook_sha256"]:
        raise ValueError("Workbook SHA-256 mismatch; refusing substitution")
    output.mkdir(parents=True, exist_ok=False)
    arrays, quality = {}, {}
    total = Counter()
    with zipfile.ZipFile(workbook) as archive:
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        properties = book.find("s:workbookPr", NS)
        date1904 = properties is not None and properties.get("date1904") in ("1", "true")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for _, e in ET.iterparse(archive.open("xl/sharedStrings.xml"), events=["end"]):
                if e.tag == "{" + NS["s"] + "}si":
                    shared.append("".join(e.itertext())); e.clear()
        links = {e.get("Id"): e.get("Target") for e in
                 ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = {e.get("name"): links[e.get("{" + REL + "}id")] for e in book.find("s:sheets", NS)}
        expected = {f"AF{n}" for n in config["nodes"]}
        if not expected.issubset(sheets):
            raise ValueError("Missing mapped worksheets")
        with gzip_text(output / "source-ledger.jsonl.gz", compresslevel=2) as ledger:
            for node in config["nodes"]:
                sheet = f"AF{node}"; target = sheets[sheet]
                target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
                rows, counts, last = [], Counter(), None
                with archive.open(target) as stream:
                    for _, e in ET.iterparse(stream, events=["end"]):
                        if e.tag != "{" + NS["s"] + "}row":
                            continue
                        row_number = int(e.get("r")); raw = [None] * 6; values = [None] * 6
                        for cell in e:
                            column = "".join(c for c in cell.get("r", "") if c.isalpha())
                            if column not in "ABCDEF" or len(column) != 1:
                                continue
                            k = ord(column) - ord("A"); typ = cell.get("t", "n")
                            v = cell.find("s:v", NS); inline = cell.find("s:is", NS)
                            token = v.text if v is not None else None
                            decoded = shared[int(token)] if typ == "s" and token is not None else (
                                "".join(inline.itertext()) if inline is not None else token)
                            raw[k] = {"type": typ, "token": token, "decoded": decoded,
                                      "style": cell.get("s"), "formula": cell.findtext("s:f", None, NS)}
                            values[k] = decoded
                        if row_number == 1:
                            if values != HEADERS:
                                raise ValueError(f"Unexpected schema {sheet}: {values}")
                            e.clear(); continue
                        if not any(v is not None for v in values):
                            counts["blank_format_rows"] += 1; e.clear(); continue
                        counts["raw_rows"] += 1; flags = []
                        try:
                            timestamp = proxy_timestamp(values[0], values[1], date1904)
                        except (ValueError, OverflowError):
                            timestamp = None
                        if timestamp is None:
                            counts["missing_or_invalid_time"] += 1; flags.append("unusable_time")
                        else:
                            counts["valid_time_rows"] += 1
                            if last is not None and timestamp < last:
                                counts["source_order_backsteps"] += 1
                            last = timestamp
                        measurements = []
                        for k, variable in [(2, "temperature"), (3, "humidity")]:
                            value = number(values[k]); lo, hi = config["variables"][variable]["bounds"]
                            if not np.isfinite(value) or not lo <= value <= hi:
                                counts[variable + "_unusable"] += 1; flags.append(variable + "_unusable")
                                value = float("nan")
                            measurements.append(value)
                        ledger.write(json.dumps({"sheet": sheet, "row": row_number, "node": node,
                                                 "raw_cells": raw, "proxy_time": timestamp,
                                                 "quality": flags}, separators=(",", ":")) + "\n")
                        if timestamp is not None:
                            rows.append((timestamp, row_number, *measurements))
                        e.clear()
                a = np.asarray(rows, dtype=float).reshape(-1, 4)
                if len(a):
                    a = a[np.argsort(a[:, 0], kind="stable")]
                    duplicate = np.zeros(len(a), dtype=bool)
                    same = np.diff(a[:, 0]) == 0
                    duplicate[1:] |= same; duplicate[:-1] |= same
                    a[duplicate, 2:] = np.nan
                    counts["duplicate_time_rows_quarantined"] = int(duplicate.sum())
                    gaps = np.diff(a[:, 0]); positive = gaps[gaps > 0]
                    counts["gaps_over_hour"] = int((gaps > 3600).sum())
                    counts["maximum_gap_seconds"] = int(positive.max()) if len(positive) else 0
                    counts["median_positive_gap_seconds"] = float(np.median(positive)) if len(positive) else None
                arrays[f"time_{node}"] = a[:, 0].astype(np.int64)
                arrays[f"row_{node}"] = a[:, 1].astype(np.int64)
                arrays[f"temperature_{node}"] = a[:, 2]
                arrays[f"humidity_{node}"] = a[:, 3]
                quality[sheet] = dict(counts)
                total.update({k: counts[k] for k in ["raw_rows", "valid_time_rows", "missing_or_invalid_time",
                                                    "source_order_backsteps", "temperature_unusable", "humidity_unusable"]})
    np.savez_compressed(output / "observations.npz", **arrays)
    report = {"workbook_sha256": sha, "cache_version": 1, "date1904": date1904,
              "axis": "naive reception proxy, rounded seconds; not acquisition or real arrival",
              "total": dict(total), "nodes": quality,
              "ledger_sha256": hashlib.sha256((output / "source-ledger.jsonl.gz").read_bytes()).hexdigest(),
              "cache_sha256": hashlib.sha256((output / "observations.npz").read_bytes()).hexdigest()}
    (output / "quality.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


class Dataset:
    def __init__(self, arrays, config):
        self.arrays, self.config = arrays, config

    @classmethod
    def open(cls, directory, config):
        directory = Path(directory); report = json.loads((directory / "quality.json").read_text())
        if report["workbook_sha256"] != config["workbook_sha256"]:
            raise ValueError("Source mismatch")
        if hashlib.sha256((directory / "observations.npz").read_bytes()).hexdigest() != report["cache_sha256"]:
            raise ValueError("Cache mismatch")
        with np.load(directory / "observations.npz", allow_pickle=False) as a:
            arrays = {k: a[k] for k in a.files}
        return cls(arrays, config)

    def asof(self, node, variable, query, max_age, shift=0):
        query = np.asarray(query, dtype=np.int64)
        t = self.arrays[f"time_{node}"] + shift
        index = np.searchsorted(t, query, side="right") - 1
        if not len(t):
            return np.full(len(query), np.nan), np.full(len(query), -1), np.full(len(query), -1)
        take = np.maximum(index, 0)
        available = (index >= 0) & (query - t[take] <= max_age)
        value = np.where(available, self.arrays[f"{variable}_{node}"][take], np.nan)
        row = np.where(available, self.arrays[f"row_{node}"][take], -1)
        arrival = np.where(available, t[take], -1)
        return value, row, arrival

    def calibration(self, variable):
        start, end = map(seconds, self.config["calibration"])
        medians = {}
        for node in self.config["nodes"]:
            t = self.arrays[f"time_{node}"]; x = self.arrays[f"{variable}_{node}"]
            eligible = (t >= start) & (t < end) & np.isfinite(x)
            medians[node] = float(np.median(x[eligible])) if eligible.sum() >= 100 else float("nan")
        return medians
