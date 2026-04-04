# Copyright (c) 2026 Continental. All rights reserved.
# Licensed under the Vanguard Proprietary Source-Available License (see /LICENSE).

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aiohttp import web
import discord

from guard import GUARD_PRESETS, guard_default_settings, normalize_guard_settings as normalize_guard_profile

AUTH_HEADER = "X-Vanguard-Control-Token"


def build_control_center_url(host: str, port: int, public_url: str = "") -> str:
    explicit = public_url.strip().rstrip("/")
    if explicit:
        return explicit
    normalized_host = host.strip() or "127.0.0.1"
    if normalized_host in {"0.0.0.0", "::"}:
        normalized_host = "localhost"
    return f"http://{normalized_host}:{port}"


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "" or value == "null":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _coerce_role_id_list(value: Any) -> list[int] | None:
    if value is None or value == "" or value == "null":
        return []
    if not isinstance(value, list):
        return None
    role_ids: list[int] = []
    seen: set[int] = set()
    for item in value:
        role_id = _coerce_optional_int(item)
        if role_id is None or role_id in seen:
            continue
        seen.add(role_id)
        role_ids.append(role_id)
    return role_ids


def _is_text_channel(channel: Any) -> bool:
    if isinstance(channel, discord.TextChannel):
        return True
    return str(getattr(channel, "type", "")).lower() == "text"


def _safe_icon_url(guild: discord.Guild) -> str | None:
    icon = getattr(guild, "icon", None)
    url = getattr(icon, "url", None)
    return str(url) if url else None


def _serialize_channel(channel: Any) -> dict[str, Any]:
    return {
        "id": int(getattr(channel, "id")),
        "name": str(getattr(channel, "name", "unknown")),
        "mention": str(getattr(channel, "mention", f"<#{getattr(channel, 'id', 0)}>")),
        "position": int(getattr(channel, "position", 0)),
    }


def _serialize_role(role: Any) -> dict[str, Any]:
    color = getattr(role, "color", None)
    color_value = getattr(color, "value", 0)
    return {
        "id": int(getattr(role, "id")),
        "name": str(getattr(role, "name", "unknown")),
        "mention": str(getattr(role, "mention", f"<@&{getattr(role, 'id', 0)}>")),
        "position": int(getattr(role, "position", 0)),
        "color": int(color_value),
    }


def _match_guard_preset_name(guard_cfg: Mapping[str, Any]) -> str:
    for preset_name, preset_values in GUARD_PRESETS.items():
        candidate = guard_default_settings()
        candidate.update(preset_values)
        normalized_candidate = normalize_guard_profile(candidate)
        if all(guard_cfg.get(key) == value for key, value in normalized_candidate.items()):
            return preset_name
    return "custom"


def _serialize_runtime_stats(raw_stats: Mapping[str, Any] | None) -> dict[str, Any]:
    stats = dict(raw_stats or {})
    last_trigger_at = stats.get("last_trigger_at")
    if isinstance(last_trigger_at, datetime):
        last_trigger_text = last_trigger_at.astimezone(timezone.utc).isoformat()
    elif isinstance(last_trigger_at, str):
        last_trigger_text = last_trigger_at
    else:
        last_trigger_text = None

    return {
        "triggers_total": int(stats.get("triggers_total", 0) or 0),
        "suppressed_total": int(stats.get("suppressed_total", 0) or 0),
        "last_trigger_at": last_trigger_text,
        "last_trigger_reasons": list(stats.get("last_trigger_reasons", []) or []),
        "last_trigger_severity": str(stats.get("last_trigger_severity") or "none"),
        "last_trigger_actor_id": _coerce_optional_int(stats.get("last_trigger_actor_id")),
    }


def _count_active_votes(guild_id: int, vote_store: Mapping[str, Any]) -> int:
    prefix = f"{guild_id}-"
    return sum(1 for vote_id in vote_store if str(vote_id).startswith(prefix))


def _count_pending_reminders(
    guild_id: int,
    reminders: Sequence[Mapping[str, Any]],
    parse_datetime_utc: Callable[[Any], datetime | None],
) -> int:
    now = datetime.now(timezone.utc)
    total = 0
    for reminder in reminders:
        if reminder.get("guild_id") != guild_id:
            continue
        due_at = parse_datetime_utc(reminder.get("due_at"))
        if due_at and due_at > now:
            total += 1
    return total


def _count_recent_cases(
    guild_id: int,
    modlog: Mapping[str, Sequence[Mapping[str, Any]]],
    parse_datetime_utc: Callable[[Any], datetime | None],
) -> int:
    entries = modlog.get(str(guild_id), [])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    total = 0
    for entry in entries:
        created_at = parse_datetime_utc(entry.get("created_at"))
        if created_at and created_at >= cutoff:
            total += 1
    return total


def build_guild_overview(
    guild: discord.Guild,
    guild_cfg: Mapping[str, Any],
    *,
    guard_runtime_stats: Mapping[int, Mapping[str, Any]],
    reminders: Sequence[Mapping[str, Any]],
    modlog: Mapping[str, Sequence[Mapping[str, Any]]],
    vote_store: Mapping[str, Any],
    parse_datetime_utc: Callable[[Any], datetime | None],
) -> dict[str, Any]:
    runtime_stats = _serialize_runtime_stats(guard_runtime_stats.get(guild.id))
    return {
        "id": guild.id,
        "name": guild.name,
        "icon_url": _safe_icon_url(guild),
        "member_count": int(getattr(guild, "member_count", 0) or 0),
        "guard_enabled": bool(guild_cfg.get("guard_enabled")),
        "guard_preset": _match_guard_preset_name(guild_cfg),
        "active_votes": _count_active_votes(guild.id, vote_store),
        "pending_reminders": _count_pending_reminders(guild.id, reminders, parse_datetime_utc),
        "recent_cases_24h": _count_recent_cases(guild.id, modlog, parse_datetime_utc),
        "runtime_stats": runtime_stats,
    }


def build_guild_detail(
    guild: discord.Guild,
    guild_cfg: Mapping[str, Any],
    *,
    guard_runtime_stats: Mapping[int, Mapping[str, Any]],
    reminders: Sequence[Mapping[str, Any]],
    modlog: Mapping[str, Sequence[Mapping[str, Any]]],
    vote_store: Mapping[str, Any],
    parse_datetime_utc: Callable[[Any], datetime | None],
    normalize_guard_settings: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    overview = build_guild_overview(
        guild,
        guild_cfg,
        guard_runtime_stats=guard_runtime_stats,
        reminders=reminders,
        modlog=modlog,
        vote_store=vote_store,
        parse_datetime_utc=parse_datetime_utc,
    )
    normalized_guard = normalize_guard_settings(guild_cfg)
    text_channels = [
        _serialize_channel(channel)
        for channel in sorted(
            getattr(guild, "text_channels", []),
            key=lambda item: (int(getattr(item, "position", 0)), str(getattr(item, "name", "")).lower()),
        )
        if _is_text_channel(channel)
    ]
    roles = [
        _serialize_role(role)
        for role in sorted(
            getattr(guild, "roles", []),
            key=lambda item: (int(getattr(item, "position", 0)), str(getattr(item, "name", "")).lower()),
            reverse=True,
        )
        if not getattr(role, "is_default", lambda: False)()
    ]
    detail = dict(overview)
    detail["settings"] = {
        "welcome_channel_id": _coerce_optional_int(guild_cfg.get("welcome_channel_id")),
        "welcome_role_id": _coerce_optional_int(guild_cfg.get("welcome_role_id")),
        "welcome_message": str(guild_cfg.get("welcome_message") or ""),
        "ops_channel_id": _coerce_optional_int(guild_cfg.get("ops_channel_id")),
        "log_channel_id": _coerce_optional_int(guild_cfg.get("log_channel_id")),
        "lockdown_role_id": _coerce_optional_int(guild_cfg.get("lockdown_role_id")),
        "mod_role_ids": list(guild_cfg.get("mod_role_ids", []) or []),
        "guard_preset": _match_guard_preset_name(normalized_guard),
        "guard": normalized_guard,
    }
    detail["channels"] = text_channels
    detail["roles"] = roles
    return detail


def apply_guild_control_update(
    guild: discord.Guild,
    guild_cfg: dict[str, Any],
    payload: Any,
    *,
    normalize_guard_settings: Callable[[Any], dict[str, Any]],
    resolve_guard_preset_name: Callable[[str | None], str | None],
    apply_guard_preset: Callable[[dict[str, Any], str], bool],
) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {"payload": "Expected a JSON object."}

    errors: dict[str, str] = {}
    updates: dict[str, Any] = {}

    def parse_text_channel_id(field_name: str) -> None:
        if field_name not in payload:
            return
        raw_value = payload.get(field_name)
        if raw_value is None or raw_value == "" or raw_value == "null":
            updates[field_name] = None
            return
        channel_id = _coerce_optional_int(raw_value)
        if channel_id is None:
            errors[field_name] = "Expected a channel ID or null."
            return
        channel = guild.get_channel(channel_id)
        if channel is None or not _is_text_channel(channel):
            errors[field_name] = "Channel must be a text channel in this server."
            return
        updates[field_name] = channel_id

    def parse_role_id(field_name: str) -> None:
        if field_name not in payload:
            return
        raw_value = payload.get(field_name)
        if raw_value is None or raw_value == "" or raw_value == "null":
            updates[field_name] = None
            return
        role_id = _coerce_optional_int(raw_value)
        if role_id is None:
            errors[field_name] = "Expected a role ID or null."
            return
        role = guild.get_role(role_id)
        if role is None:
            errors[field_name] = "Role must exist in this server."
            return
        updates[field_name] = role_id

    parse_text_channel_id("welcome_channel_id")
    parse_text_channel_id("ops_channel_id")
    parse_text_channel_id("log_channel_id")
    parse_role_id("welcome_role_id")
    parse_role_id("lockdown_role_id")

    if "welcome_message" in payload:
        raw_message = payload.get("welcome_message")
        if raw_message is None or raw_message == "null":
            updates["welcome_message"] = None
        else:
            message = str(raw_message).strip()
            updates["welcome_message"] = message[:500] if message else None

    if "mod_role_ids" in payload:
        role_ids = _coerce_role_id_list(payload.get("mod_role_ids"))
        if role_ids is None:
            errors["mod_role_ids"] = "Expected a list of role IDs."
        else:
            missing = [role_id for role_id in role_ids if guild.get_role(role_id) is None]
            if missing:
                errors["mod_role_ids"] = "All mod roles must exist in this server."
            else:
                updates["mod_role_ids"] = role_ids

    guard_payload = payload.get("guard")
    if guard_payload is not None and not isinstance(guard_payload, dict):
        errors["guard"] = "Expected a guard settings object."

    preset_name: str | None = None
    if "guard_preset" in payload:
        raw_preset = str(payload.get("guard_preset") or "").strip().lower()
        if raw_preset and raw_preset != "custom":
            preset_name = resolve_guard_preset_name(raw_preset)
            if preset_name is None:
                errors["guard_preset"] = "Unknown guard preset."

    if errors:
        return errors

    guild_cfg.update(updates)

    guard_source = dict(guild_cfg)
    if preset_name:
        apply_guard_preset(guard_source, preset_name)
    if isinstance(guard_payload, dict):
        guard_source.update(guard_payload)
    guild_cfg.update(normalize_guard_settings(guard_source))
    return {}


def create_control_center_app(
    *,
    bot: discord.Client,
    get_guild_config: Callable[[int], dict[str, Any]],
    save_settings: Callable[[], None],
    normalize_guard_settings: Callable[[Any], dict[str, Any]],
    resolve_guard_preset_name: Callable[[str | None], str | None],
    apply_guard_preset: Callable[[dict[str, Any], str], bool],
    guard_runtime_stats: Mapping[int, Mapping[str, Any]],
    reminders: Sequence[Mapping[str, Any]],
    modlog: Mapping[str, Sequence[Mapping[str, Any]]],
    vote_store: Mapping[str, Any],
    parse_datetime_utc: Callable[[Any], datetime | None],
    control_token: str,
    static_dir: str | Path,
) -> web.Application:
    static_root = Path(static_dir)

    @web.middleware
    async def auth_middleware(request: web.Request, handler: Callable[[web.Request], Any]) -> web.StreamResponse:
        if not request.path.startswith("/api/"):
            return await handler(request)
        if not control_token:
            return web.json_response({"error": "Control center token is not configured."}, status=503)

        supplied = request.headers.get(AUTH_HEADER, "").strip()
        if not supplied:
            authorization = request.headers.get("Authorization", "").strip()
            if authorization.lower().startswith("bearer "):
                supplied = authorization[7:].strip()
        if supplied != control_token:
            return web.json_response({"error": "Unauthorized."}, status=401)
        return await handler(request)

    app = web.Application(middlewares=[auth_middleware])

    async def index(_: web.Request) -> web.StreamResponse:
        return web.FileResponse(static_root / "index.html")

    async def guild_list(_: web.Request) -> web.StreamResponse:
        guilds = sorted(bot.guilds, key=lambda item: item.name.lower())
        payload = {
            "bot": {
                "name": getattr(getattr(bot, "user", None), "name", "Vanguard"),
                "id": getattr(getattr(bot, "user", None), "id", None),
                "guild_count": len(guilds),
            },
            "guilds": [
                build_guild_overview(
                    guild,
                    get_guild_config(guild.id),
                    guard_runtime_stats=guard_runtime_stats,
                    reminders=reminders,
                    modlog=modlog,
                    vote_store=vote_store,
                    parse_datetime_utc=parse_datetime_utc,
                )
                for guild in guilds
            ],
        }
        return web.json_response(payload)

    async def guild_detail(request: web.Request) -> web.StreamResponse:
        guild_id = _coerce_optional_int(request.match_info.get("guild_id"))
        guild = bot.get_guild(guild_id or 0)
        if guild is None:
            return web.json_response({"error": "Guild not found."}, status=404)
        payload = build_guild_detail(
            guild,
            get_guild_config(guild.id),
            guard_runtime_stats=guard_runtime_stats,
            reminders=reminders,
            modlog=modlog,
            vote_store=vote_store,
            parse_datetime_utc=parse_datetime_utc,
            normalize_guard_settings=normalize_guard_settings,
        )
        return web.json_response(payload)

    async def update_guild(request: web.Request) -> web.StreamResponse:
        guild_id = _coerce_optional_int(request.match_info.get("guild_id"))
        guild = bot.get_guild(guild_id or 0)
        if guild is None:
            return web.json_response({"error": "Guild not found."}, status=404)
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "Request body must be valid JSON."}, status=400)

        guild_cfg = get_guild_config(guild.id)
        errors = apply_guild_control_update(
            guild,
            guild_cfg,
            payload,
            normalize_guard_settings=normalize_guard_settings,
            resolve_guard_preset_name=resolve_guard_preset_name,
            apply_guard_preset=apply_guard_preset,
        )
        if errors:
            return web.json_response({"errors": errors}, status=400)

        save_settings()
        response_payload = build_guild_detail(
            guild,
            guild_cfg,
            guard_runtime_stats=guard_runtime_stats,
            reminders=reminders,
            modlog=modlog,
            vote_store=vote_store,
            parse_datetime_utc=parse_datetime_utc,
            normalize_guard_settings=normalize_guard_settings,
        )
        return web.json_response(response_payload)

    app.router.add_get("/", index)
    app.router.add_get("/api/guilds", guild_list)
    app.router.add_get("/api/guilds/{guild_id}", guild_detail)
    app.router.add_put("/api/guilds/{guild_id}", update_guild)
    app.router.add_static("/static/", static_root, show_index=False)
    return app


async def start_control_center_site(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return runner
