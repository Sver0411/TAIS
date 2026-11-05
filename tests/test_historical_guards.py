"""Exercise historical guards against committed additions and real Git changes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_paper_revision as revision
import verify_transfer as transfer
import verify_phase4 as phase4


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


@pytest.fixture(params=['revision', 'transfer'])
def guarded_repo(tmp_path, monkeypatch, request):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    git(tmp_path, 'config', 'user.name', 'Guard test')
    for name in ['src/tais/core.py', 'configs/experiment.yaml',
                 'results/tais-paper/metrics.csv']:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('inherited evidence\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'Historical baseline')
    base = git(tmp_path, 'rev-parse', 'HEAD')
    # Unlike untracked engineering files, committed additions triggered the bug.
    for name in ['src/tais/adaptive/sampling.py', 'configs/phase4.json']:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('new independent study\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'Add later study')
    module = revision if request.param == 'revision' else transfer
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    if module is transfer:
        monkeypatch.setattr(module, 'BASE', base)
        check = module.verify_inherited_paths
    else:
        check = lambda: module.verify_inherited_paths(base)
    return tmp_path, check


def test_committed_additive_study_is_allowed(guarded_repo):
    _, check = guarded_repo
    check()


@pytest.mark.parametrize('name', ['src/tais/core.py', 'configs/experiment.yaml',
                                 'results/tais-paper/metrics.csv'])
@pytest.mark.parametrize('change', ['modify', 'delete', 'rename', 'type'])
def test_inherited_changes_still_fail(guarded_repo, name, change):
    root, check = guarded_repo
    path = root/name
    if change == 'modify':
        path.write_text('changed evidence\n')
    elif change == 'delete':
        path.unlink()
    elif change == 'rename':
        git(root, 'mv', name, name+'.renamed')
    else:
        path.unlink()
        path.symlink_to('replacement')
    with pytest.raises(AssertionError):
        check()


@pytest.fixture
def maintenance(tmp_path, monkeypatch):
    names = ['scripts/verify_transfer.py', 'scripts/verify_paper_revision.py']
    original = {name: 'f'*64 for name in names}
    original['src/tais/core.py'] = hashlib.sha256(b'frozen\n').hexdigest()
    entries = {}
    for name in original:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('frozen\n')
        if name in names:
            entries[name] = dict(original_sha256=original[name],
                                 current_sha256=phase4.sha(path))
    out = tmp_path/'results/phase4'
    (out/'maintenance').mkdir(parents=True)
    archive = out/'maintenance/historical-protection-original.json'
    archive.write_text(json.dumps(dict(files=original)))
    active = dict(files={name: h for name, h in original.items() if name not in names},
                  original_ledger='maintenance/historical-protection-original.json',
                  original_ledger_sha256=phase4.sha(archive),
                  maintenance_ledger='maintenance/ci-guards.json')
    (out/'historical-protection.json').write_text(json.dumps(active))
    ledger = out/'maintenance/ci-guards.json'
    ledger.write_text(json.dumps(dict(files=entries)))
    monkeypatch.setattr(phase4, 'ROOT', tmp_path)
    monkeypatch.setattr(phase4, 'OUT', out)
    return tmp_path, ledger, entries


def test_maintenance_is_separate_from_original_hashes(maintenance):
    assert phase4.verify_historical_files() == (1, 2)


def test_original_ledger_archive_is_byte_exact(maintenance):
    _, ledger, _ = maintenance
    (ledger.parent/'historical-protection-original.json').write_text('{}')
    with pytest.raises(AssertionError):
        phase4.verify_historical_files()


@pytest.mark.parametrize('name', ['src/tais/core.py', 'scripts/verify_transfer.py'])
def test_maintenance_still_rejects_content_changes(maintenance, name):
    root, _, _ = maintenance
    (root/name).write_text('tampered\n')
    with pytest.raises(AssertionError):
        phase4.verify_historical_files()


@pytest.mark.parametrize('change', ['original_hash', 'extra_exception', 'omit_protected'])
def test_maintenance_cannot_change_original_hash_or_exempt_runtime(maintenance, change):
    _, ledger, entries = maintenance
    if change == 'original_hash':
        entries['scripts/verify_transfer.py']['original_sha256'] = '0'*64
    elif change == 'extra_exception':
        entries['src/tais/core.py'] = dict(original_sha256='0'*64, current_sha256='0'*64)
    else:
        active_path = ledger.parent.parent/'historical-protection.json'
        active = json.loads(active_path.read_text())
        active['files'].pop('src/tais/core.py')
        active_path.write_text(json.dumps(active))
    ledger.write_text(json.dumps(dict(files=entries)))
    with pytest.raises(AssertionError):
        phase4.verify_historical_files()
