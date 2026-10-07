import json
import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "seedance-2-0/scripts/seedance_job.py"
spec = importlib.util.spec_from_file_location("seedance_job", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
check = module.check

def test_text_template_is_valid():
    body=json.loads((Path(__file__).parents[1]/"seedance-2-0/templates/text.json").read_text())
    problems, report=check(body)
    assert problems == []
    assert report["model"] == "seedance-2.0"
    assert report["usd"] > 0

def test_720p_is_not_allowed_on_mini_when_wrong():
    problems,_=check({"model":"seedance-2.0-mini","prompt":"x","duration":5,"resolution":"4k"})
    assert any("renders" in x for x in problems)
