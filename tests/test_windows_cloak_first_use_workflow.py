from pathlib import Path

import yaml


def test_windows_workflow_uses_frozen_first_use_worker_and_narrow_receipt() -> None:
    workflow = yaml.safe_load(Path('.github/workflows/windows-validation.yml').read_text(encoding='utf-8'))
    steps = workflow['jobs']['build-and-smoke']['steps']
    provision = next(step for step in steps if step['name'].startswith('Provision isolated licensed Cloak'))
    assert '.\\dist\\ParserRIba\\ParserRIba.exe --local-task --task cloak_runtime_install --input-stdin' in provision['run']
    assert '.build-venv\\Scripts\\python.exe scripts\\install_cloakbrowser_runtime.py' not in provision['run']
    assert 'CLOAKBROWSER_LICENSE_KEY' in provision['env']
    assert 'cache is not empty' in provision['run']
    upload = next(step for step in steps if step['name'] == 'Upload candidate artifacts for review')
    assert 'dist/cloak-first-use-receipt.json' in upload['with']['path']
