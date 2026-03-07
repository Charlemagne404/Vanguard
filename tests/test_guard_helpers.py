import importlib
import sys
from datetime import datetime, timezone


def load_guard(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("VANGUARD_DATA_DIR", str(data_dir))
    for module_name in ("thingamabot", "guard", "vote", "data_paths"):
        sys.modules.pop(module_name, None)
    return importlib.import_module("guard")


def test_normalize_guard_settings_clamps(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)
    cfg = guard.normalize_guard_settings(
        {
            "guard_cooldown_seconds": 1,
            "guard_slowmode_scope": "everywhere",
            "guard_timeout_seconds": 999999999,
            "guard_detect_links": "off",
            "guard_link_threshold": -5,
        }
    )

    assert cfg["guard_cooldown_seconds"] == 300
    assert cfg["guard_slowmode_scope"] == "trigger"
    assert cfg["guard_timeout_seconds"] == 0
    assert cfg["guard_detect_links"] is False
    assert cfg["guard_link_threshold"] == 5


def test_guard_preset_alias_resolves(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)

    assert guard.resolve_guard_preset_name("high") == "strict"
    assert guard.resolve_guard_preset_name("panic") == "siege"
    assert guard.resolve_guard_preset_name("unknown") is None


def test_apply_guard_preset_updates_config(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)

    cfg = guard.guard_default_settings()
    assert guard.apply_guard_preset(cfg, "balanced") is True

    assert cfg["guard_enabled"] is True
    assert cfg["guard_timeout_seconds"] == 300
    assert cfg["guard_slowmode_scope"] == "active"


def test_runtime_snapshot_contains_counters(monkeypatch, tmp_path):
    guard = load_guard(monkeypatch, tmp_path)

    guild_id = 999
    now = datetime.now(timezone.utc)
    guard.new_account_message_tracker[guild_id].append(now)
    guard.join_rate_tracker[guild_id].append(now)

    snapshot = guard.get_guard_runtime_snapshot(guild_id, guard.guard_default_settings())

    assert snapshot["new_account_window_count"] >= 1
    assert snapshot["join_window_count"] >= 1
    assert snapshot["triggers_total"] == 0
    assert snapshot["suppressed_total"] == 0
