"""Causality, provenance, identifiability and fair-cost tests for the pilot."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import struct
import zipfile

import numpy as np
import pytest

from tais_spatial.data import Dataset, neighbors, position, prepare, proxy_timestamp, seconds
from tais_spatial.interventions import schedule
from tais_spatial.methods import detect, features, trend
from tais_spatial.pilot import (costs, dates, donor_values, materialize, packet_residual,
                                run_split, unmatched)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg():
    return json.loads((ROOT/"configs/offline_spatial_pilot.json").read_text())


def workbook(path):
    # Minimal OOXML *test fixture*, not an authored user workbook or modified source.
    head = "".join(f'<c r="{c}1" t="inlineStr"><is><t>{v}</t></is></c>' for c, v in
                   zip("ABCDEF", ["Date", "Time", "Onboard Temperature", "Onboard Humidity", "RSSI", "SNR"]))
    def row(n, time, temp=24, humidity=50):
        cells = [("A", 43939), ("B", time), ("C", temp), ("D", humidity), ("E", -100), ("F", 5)]
        return f'<row r="{n}">' + "".join(f'<c r="{c}{n}"><v>{v}</v></c>' for c, v in cells if v is not None) + '</row>'
    sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             + f'<row r="1">{head}</row>' + row(2, .5) + row(3, None) + row(4, .4, 200)
             + row(5, .6) + row(6, .6) + '</sheetData></worksheet>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="AF16" sheetId="1" r:id="r1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def fake_dataset(cfg):
    prefix = np.arange(seconds(cfg["calibration"][0]), seconds(cfg["calibration"][1]), 600)
    day = seconds(cfg["splits"]["development"][0])
    times = np.concatenate([prefix, np.arange(day+4*3600, day+20*3600+1, 600)])
    arrays = {}
    for n in cfg["nodes"]:
        arrays[f"time_{n}"] = times.copy(); arrays[f"row_{n}"] = np.arange(len(times))+2
        arrays[f"temperature_{n}"] = 24+np.sin(times/3600)/10+n/100
        arrays[f"humidity_{n}"] = 50+np.sin(times/3600)+n/100
    return Dataset(arrays, cfg)


def test_reader_preserves_original_rows_values_and_quarantines(tmp_path, cfg):
    p = tmp_path/"fixture.xlsx"; workbook(p); before = p.read_bytes()
    cfg["nodes"] = [16]; cfg["workbook_sha256"] = hashlib.sha256(before).hexdigest()
    report = prepare(p, tmp_path/"cache", cfg)
    assert report["total"]["raw_rows"] == 5
    assert report["total"]["missing_or_invalid_time"] == 1
    assert report["total"]["source_order_backsteps"] == 1
    assert report["nodes"]["AF16"]["duplicate_time_rows_quarantined"] == 2
    records = [json.loads(line) for line in gzip.open(tmp_path/"cache/source-ledger.jsonl.gz", "rt")]
    assert records[1]["row"] == 3 and records[1]["proxy_time"] is None
    assert records[2]["raw_cells"][2]["token"] == "200"
    d = Dataset.open(tmp_path/"cache", cfg)
    assert np.isnan(d.arrays["temperature_16"]).sum() == 3
    assert np.isnan(d.arrays["humidity_16"]).sum() == 2
    assert p.read_bytes() == before
    with pytest.raises(FileExistsError):
        prepare(p, tmp_path/"cache", cfg)


def test_source_substitution_rejected(tmp_path, cfg):
    p = tmp_path/"wrong.xlsx"; p.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="SHA-256"):
        prepare(p, tmp_path/"cache", cfg)


def test_proxy_clock_has_no_machine_timezone_or_missing_midnight_fill():
    assert proxy_timestamp(None, "0") is None
    assert proxy_timestamp("43939", None) is None
    assert proxy_timestamp("43939", ".5") - proxy_timestamp("43939", "0") == 43200


@pytest.mark.parametrize("shift", [-600, 0, 600])
@pytest.mark.parametrize("age", [300, 900, 1800])
def test_asof_causality_and_maximum_age(cfg, shift, age):
    d = fake_dataset(cfg); queries = np.arange(seconds("2020-04-26T04:00"), seconds("2020-04-26T20:00"), 111)
    values, rows, arrival = d.asof(16, "temperature", queries, age, shift)
    ok = np.isfinite(values)
    assert np.all(arrival[ok] <= queries[ok])
    assert np.all(queries[ok]-arrival[ok] <= age)
    assert np.all(rows[~ok] == -1)


def test_future_mutations_cannot_change_prefix(cfg):
    d = fake_dataset(cfg); cutoff = seconds("2020-04-26T12:00")
    query = np.arange(cutoff-3600, cutoff+1, 600)
    first = d.asof(16, "temperature", query, 900)[0]
    d.arrays["temperature_16"][d.arrays["time_16"] > cutoff] = 9999
    np.testing.assert_array_equal(first, d.asof(16, "temperature", query, 900)[0])


def test_calibration_and_null_cannot_read_evaluation_values(cfg):
    d = fake_dataset(cfg); median = d.calibration("temperature")[16]
    query = np.arange(seconds("2020-04-26T04:00"), seconds("2020-04-26T20:00"), 600)
    values = donor_values(d, 16, "temperature", "fixed", query, cfg, median)[0]
    end = seconds(cfg["calibration"][1]); mask = d.arrays["time_16"] >= end
    d.arrays["temperature_16"][mask] = 9999
    assert d.calibration("temperature")[16] == median
    np.testing.assert_array_equal(values, donor_values(d, 16, "temperature", "fixed", query, cfg, median)[0])


def test_layout_is_explicit_and_not_a_correlation_selection():
    assert [position(n)[0] for n in range(16, 43)] == [0, 1, 2]*9
    assert neighbors(29) == [26, 28, 30, 32]
    assert all(n not in neighbors(n) and len(neighbors(n)) == 4 for n in range(16, 43))
    with pytest.raises(ValueError):
        position(49)


def test_cache_repeats_are_not_new_confirmation_evidence(cfg):
    x = np.arange(20, dtype=float)
    f = features(x, np.ones(20, dtype=int), x, x, cfg)
    assert f["fresh"].sum() == 1
    assert np.isnan(f["score"]).all()
    assert not detect(f, .5, "HistoryShort", cfg)[0].any()


def test_slow_local_and_drift_are_nonidentifiable_even_with_spatial_input(cfg):
    query = np.arange(seconds("2020-04-26T04:00"), seconds("2020-04-26T20:00")+1, 600)
    inputs = dict(target=np.full(len(query), 95.), target_arrival=query, real=np.full((4, len(query)), 95.),
                  null=np.full((4, len(query)), 95.), ref_arrival=np.tile(query, (4, 1)), query=query, shift=0)
    outputs = []
    for case in ["drift", "local_slow"]:
        label = schedule(case, seconds("2020-04-26"), 29, "humidity", neighbors(29), cfg)
        x, real, null, clipped = materialize(inputs, label, cfg)
        assert clipped > 0 and np.max(x) <= 100
        z, _ = packet_residual(x, real, 95, np.ones(4)*95, 2)
        feature = features(x, np.arange(len(query)), z, z, cfg)
        outputs.append([detect(feature, 4, m, cfg)[0] for m in cfg["methods"]])
    for a, b in zip(*outputs):
        np.testing.assert_array_equal(a, b)


def test_missing_references_fail_open_and_fast_local_change_can_report(cfg):
    x = np.r_[np.ones(10)*24, np.ones(10)*28]; rows = np.arange(20)
    z, count = packet_residual(x, np.full((4, 20), np.nan), 24, np.ones(4)*24, 2)
    assert not count.any() and np.isnan(z).all()
    feature = features(x, rows, z, z, cfg)
    expected = detect(feature, 1, "HistoryShort", cfg)[0]
    assert expected.sum() == 1
    np.testing.assert_array_equal(expected, detect(feature, 1, "Spatial", cfg)[0])


def test_model_prefix_causality_not_just_input_lookup(cfg):
    rng = np.random.default_rng(1); x = rng.normal(24, 1, 40); rows = np.arange(40)
    a = features(x, rows, x/2, x/3, cfg)
    changed = x.copy(); changed[20:] += 100
    b = features(changed, rows, changed/2, changed/3, cfg)
    for method in cfg["methods"]:
        np.testing.assert_array_equal(detect(a, 1, method, cfg)[0][:20], detect(b, 1, method, cfg)[0][:20])


def test_budget_includes_missing_reference_responses_and_is_equal_for_null(cfg):
    x = np.arange(10, dtype=float); refs = np.full((4, 10), np.nan)
    inp = {"target_rows": np.arange(10), "ref_rows": np.full((4, 10), -1)}
    spatial = costs(inp, x, refs, refs, "Spatial", [])
    null = costs(inp, x, refs, refs, "NullSpatial", [])
    assert spatial == null
    assert spatial["reference_requests"] == 40
    assert spatial["application_bytes"] == 40*(struct.calcsize("<BqB")+struct.calcsize("<BqqdB"))
    assert struct.calcsize("<BqBd") == 18


def test_counterfactual_matching_is_one_to_one():
    added, removed = unmatched([100, 110, 300], [105, 900], 10)
    assert added.tolist() == [110, 300] and removed.tolist() == [900]


def test_split_guards_and_weekly_dates(cfg):
    assert [d.date().isoformat() for d in dates(cfg, "development")] == ["2020-04-26", "2020-05-03", "2020-05-10", "2020-05-17", "2020-05-24", "2020-05-31"]
    assert len(dates(cfg, "test")) == 9
    assert seconds(cfg["calibration"][1]) < seconds(cfg["splits"]["development"][0])
    assert seconds(cfg["splits"]["development"][1]) < seconds(cfg["splits"]["validation"][0])
    assert seconds(cfg["splits"]["validation"][1]) < seconds(cfg["splits"]["test"][0])


def test_experiment_and_truth_artifacts_repeat_byte_for_byte(tmp_path, cfg):
    d = fake_dataset(cfg)
    first = run_split(d, cfg, "development", tmp_path/"one", ROOT, smoke=True)
    second = run_split(d, cfg, "development", tmp_path/"two", ROOT, smoke=True)
    assert first == second
    for name in first["artifacts"]:
        assert (tmp_path/"one"/name).read_bytes() == (tmp_path/"two"/name).read_bytes()
    assert first["rows"] == 3*2*13*4
    labels = [json.loads(line) for line in gzip.open(tmp_path/"one/interventions.jsonl.gz", "rt")]
    assert len(labels) == 3*2*13
