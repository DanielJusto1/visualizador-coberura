import re
import string
from pathlib import Path

import pytest

from radiocoverage import i18n
from radiocoverage.i18n import tr

SRC = Path(__file__).resolve().parent.parent / "src" / "radiocoverage"


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def all_entries():
    entries = dict(i18n._TEXT)
    try:
        from radiocoverage.webapp.texts import WEB_TEXT
    except ImportError:  # web extra not installed
        return entries
    assert not set(entries) & set(WEB_TEXT), "a key is defined twice"
    entries.update(WEB_TEXT)
    return entries


@pytest.mark.parametrize(("key", "texts"), sorted(all_entries().items()))
def test_both_languages_present_with_same_placeholders(key, texts):
    spanish, english = texts
    assert spanish.strip() and english.strip()
    assert fields(spanish) == fields(english), key


def test_tr_language_and_fallback():
    assert tr("verdict.ok", "es") == "ENLACE VIABLE"
    assert tr("verdict.ok", "en") == "LINK OK"
    assert tr("verdict.ok", "fr") == "LINK OK"  # unknown language -> English
    assert tr("map.link_tooltip", "es", distance=1.234, margin=5.67) == "1.23 km · margen 5.7 dB"
    with pytest.raises(KeyError):
        tr("does.not.exist")


def literal_keys() -> set[str]:
    pattern = re.compile(r"""\b(?:t|tr)\(\s*["']([a-z0-9_.\-]+)["']""")
    keys = set()
    for path in SRC.rglob("*.py"):
        keys |= set(pattern.findall(path.read_text(encoding="utf-8")))
    return keys


def dynamic_keys() -> set[str]:
    from radiocoverage.propagation import ENVIRONMENTS, MODEL_CHOICES
    from radiocoverage.rendering import SIGNAL_CLASSES

    keys = {f"env.{e}" for e in ENVIRONMENTS}
    keys |= {f"class.{c.label.lower()}" for c in SIGNAL_CLASSES}
    keys |= {f"terrain.{s}" for s in ("clear", "partial", "blocked")}
    keys |= {f"validity.{q}" for q in ("distance", "tx_height", "rx_height")}
    keys |= {"map.layer.signal", "map.layer.server"}
    try:
        from radiocoverage.webapp.presets import EXAMPLE_NETWORKS, TERMINAL_LOCATIONS
    except ImportError:
        return keys
    keys |= {f"web.model.{m}" for m in MODEL_CHOICES}
    keys |= {f"web.where.{w}" for w in TERMINAL_LOCATIONS}
    keys |= {f"planner.mode.{m}" for m in ("tx", "rx")}
    keys |= {f"network.example.{n}" for n in EXAMPLE_NETWORKS}
    keys |= {
        f"planner.msg.{m}"
        for m in ("tx_placed", "rx_placed", "swapped", "cleared", "outside", "invalid", "too_close")
    }
    keys |= {f"network.error.{e}" for e in ("coordinates", "outside", "band", "values")}
    keys |= {f"network.msg.{m}" for m in ("added", "loaded")}
    return keys  # fmt: skip


def test_every_used_key_exists():
    known = all_entries()
    missing = sorted(k for k in literal_keys() | dynamic_keys() if k not in known)
    assert missing == []
