from pathlib import Path

from unibac_integrations.parsers import BankStatementParser, CibilParser, GstParser


def test_parsers_return_defaults(tmp_path: Path) -> None:
    f = tmp_path / "x"
    f.write_text("")
    assert BankStatementParser().parse(f).bounce_count == 0
    assert CibilParser().parse(f).score is None
    assert GstParser().parse(f).last_filed_period is None
