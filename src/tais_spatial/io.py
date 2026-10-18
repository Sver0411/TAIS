"""Deterministic compressed artifacts and strict JSON-compatible diagnostics."""
from contextlib import contextmanager
import gzip
import io
import math


@contextmanager
def gzip_text(path, compresslevel=6, newline=None):
    with open(path, "xb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=compresslevel) as z:
            with io.TextIOWrapper(z, encoding="utf-8", newline=newline) as text:
                yield text


def safe_json(value):
    if isinstance(value, dict):
        return {k: safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
