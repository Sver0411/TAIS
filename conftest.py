"""Make the pinned provenance tree available in shallow GitHub Actions checkouts."""
import os
from pathlib import Path
import subprocess


IRB_BASE = '89aa8341181aa42791f9a4de80739bb7c10fa9e5'


def pytest_sessionstart(session):
    # No network in ordinary local tests, and no fallback to a different base.
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    root = Path(__file__).resolve().parent
    probe = ['git', 'cat-file', '-e', IRB_BASE + '^{commit}']
    if subprocess.run(probe, cwd=root, capture_output=True).returncode == 0:
        return
    shallow = subprocess.check_output(
        ['git', 'rev-parse', '--is-shallow-repository'], cwd=root, text=True,
    ).strip()
    if shallow != 'true':
        raise RuntimeError('Pinned IRB provenance commit is absent from a full CI checkout')
    subprocess.run(
        ['git', 'fetch', '--no-tags', '--depth=1', 'origin', IRB_BASE],
        cwd=root, check=True, timeout=60,
    )
    subprocess.run(probe, cwd=root, check=True)
