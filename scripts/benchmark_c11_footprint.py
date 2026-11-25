#!/usr/bin/env python3
"""Compile & benchmark pure C11 TAIS-JALC + SensorTrust on Host and ESP32-S3 Xtensa."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
C11_DIR = ROOT / "src/tais/closed_loop/c11"
ST_DIR = ROOT / "vendor/SensorTrust/core"
OUT_DIR = ROOT / "results/phase5_c11"

XTENSA_BIN = Path.home() / ".platformio/packages/toolchain-xtensa-esp-elf/bin"


def _parse_berkeley_size(text: str) -> dict:
    # Berkeley `size` format: text  data  bss  dec  hex  filename
    for ln in text.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[0-9a-fA-F]+\s+(.+)$", ln)
        if m:
            return dict(
                text_bytes=int(m.group(1)),
                data_bytes=int(m.group(2)),
                bss_bytes=int(m.group(3)),
                total_bytes=int(m.group(4)),
            )
    return {"raw": text.strip()}


def _parse_darwin_size(text: str) -> dict:
    # macOS `size` format: __TEXT __DATA __OBJC others dec hex
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 5 and parts[0].isdigit():
            return dict(
                text_bytes=int(parts[0]),
                data_bytes=int(parts[1]),
                other_bytes=int(parts[3]),
                total_bytes=int(parts[4]),
            )
    return {"raw": text.strip()}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cc = shutil.which(os.environ.get("CC", "cc"))
    assert cc, "C11 host compiler required"

    report: dict = {
        "host_platform": platform.platform(),
        "host_machine": platform.machine(),
        "host_compiler": subprocess.check_output([cc, "--version"], text=True).splitlines()[0],
    }

    with tempfile.TemporaryDirectory(prefix="tais_c11_bench_") as tmp:
        td = Path(tmp)
        # 1. Compile host object files & standalone micro-benchmark
        jalc_o = td / "tais_jalc.o"
        st_o = td / "sensor_trust.o"
        bench_bin = td / "bench_main"

        subprocess.run(
            [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-I", str(C11_DIR), "-c", str(C11_DIR / "tais_jalc.c"), "-o", str(jalc_o)],
            check=True,
        )
        subprocess.run(
            [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-I", str(ST_DIR), "-c", str(ST_DIR / "sensor_trust.c"), "-o", str(st_o)],
            check=True,
        )
        subprocess.run(
            [
                cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                "-I", str(C11_DIR), "-I", str(ST_DIR),
                str(C11_DIR / "bench_main.c"), str(jalc_o), str(st_o),
                "-lm", "-o", str(bench_bin),
            ],
            check=True,
        )
        bench_out = json.loads(subprocess.check_output([str(bench_bin)], text=True))
        report["host_benchmark"] = bench_out

        size_tool = shutil.which("size")
        if size_tool:
            raw_j = subprocess.check_output([size_tool, str(jalc_o)], text=True)
            raw_s = subprocess.check_output([size_tool, str(st_o)], text=True)
            parser = _parse_darwin_size if platform.system() == "Darwin" else _parse_berkeley_size
            report["host_object_sizes"] = {
                "tais_jalc.o": parser(raw_j),
                "sensor_trust.o": parser(raw_s),
            }

        # 2. Cross-compile for real ESP32-S3 (Xtensa LX7) if toolchain is installed
        xt_gcc = XTENSA_BIN / "xtensa-esp32s3-elf-gcc"
        xt_size = XTENSA_BIN / "xtensa-esp32s3-elf-size"
        if xt_gcc.exists() and xt_size.exists():
            xt_jalc_o = td / "tais_jalc_esp32s3.o"
            xt_st_o = td / "sensor_trust_esp32s3.o"
            flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Os", "-mlongcalls", "-ffunction-sections", "-fdata-sections"]
            subprocess.run(
                [str(xt_gcc), *flags, "-I", str(C11_DIR), "-c", str(C11_DIR / "tais_jalc.c"), "-o", str(xt_jalc_o)],
                check=True,
            )
            subprocess.run(
                [str(xt_gcc), *flags, "-I", str(ST_DIR), "-c", str(ST_DIR / "sensor_trust.c"), "-o", str(xt_st_o)],
                check=True,
            )
            sj = _parse_berkeley_size(subprocess.check_output([str(xt_size), str(xt_jalc_o)], text=True))
            ss = _parse_berkeley_size(subprocess.check_output([str(xt_size), str(xt_st_o)], text=True))
            report["esp32s3_cross_compile"] = {
                "compiler": subprocess.check_output([str(xt_gcc), "--version"], text=True).splitlines()[0],
                "flags": " ".join(flags),
                "tais_jalc.o": sj,
                "sensor_trust.o": ss,
                "combined_flash_code_bytes": sj["text_bytes"] + ss["text_bytes"],
                "combined_static_data_bss_bytes": sj["data_bytes"] + sj["bss_bytes"] + ss["data_bytes"] + ss["bss_bytes"],
                "note": (
                    "Exact ELF section sizes compiled for Xtensa ESP32-S3 (-Os). "
                    "Runtime latency above is host-measured; physical ESP32-S3 cycle/current measurements remain future work."
                ),
            }
        else:
            report["esp32s3_cross_compile"] = {"available": False}

    out_path = OUT_DIR / "benchmark.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
