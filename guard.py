# Copyright (c) 2026 Continental. All rights reserved.
# Licensed under the Vanguard Proprietary Source-Available License (see /LICENSE).

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

import discord
from discord.ext import commands

GUARD_COOLDOWN_SECONDS = 300

message_rate_tracker: dict[int, deque[datetime]] = defaultdict(deque)
guard_last_trigger: dict[int, datetime] = {}

RequireModContextCallback = Callable[
    [commands.Context],
    Awaitable[tuple[discord.Guild, dict[str, Any]] | None],
]
SaveSettingsCallback = Callable[[], None]
SendOpsLogCallback = Callable[[discord.Guild, str], Awaitable[None]]
LogModerationActionCallback = Callable[..., int]


def count_guard_window(guild_id: int, window_seconds: int, now: datetime) -> int:
    tracker = message_rate_tracker[guild_id]
    cutoff = now - timedelta(seconds=window_seconds)
    while tracker and tracker[0] < cutoff:
        tracker.popleft()
    return len(tracker)


def should_trigger_guard(guild_id: int, now: datetime) -> bool:
    last = guard_last_trigger.get(guild_id)
    if not last:
        return True
    return (now - last).total_seconds() >= GUARD_COOLDOWN_SECONDS


async def handle_guard_message(
    *,
    bot: commands.Bot,
    message: discord.Message,
    guild_cfg: dict[str, Any],
    log_moderation_action: LogModerationActionCallback,
    send_ops_log: SendOpsLogCallback,
) -> None:
    if not isinstance(message.author, discord.Member):
        return
    guild = message.guild
    if guild is None:
        return
    if not guild_cfg.get("guard_enabled", False):
        return

    now = datetime.now(timezone.utc)
    new_account_hours = guild_cfg.get("guard_new_account_hours", 24)
    account_age = now - message.author.created_at.astimezone(timezone.utc)
    if account_age > timedelta(hours=new_account_hours):
        return

    message_rate_tracker[guild.id].append(now)
    window_seconds = guild_cfg.get("guard_window_seconds", 30)
    threshold = guild_cfg.get("guard_threshold", 8)
    current_rate = count_guard_window(guild.id, window_seconds, now)
    if current_rate < threshold or not should_trigger_guard(guild.id, now):
        return

    guard_last_trigger[guild.id] = now
    details = (
        f"Detected {current_rate} messages from new accounts in "
        f"{window_seconds}s window."
    )
    alert_channel = message.channel
    configured_alert = guild.get_channel(guild_cfg.get("ops_channel_id"))
    if configured_alert and hasattr(configured_alert, "send"):
        alert_channel = configured_alert

    slowmode_seconds = guild_cfg.get("guard_slowmode_seconds", 30)
    if (
        isinstance(message.channel, discord.TextChannel)
        and slowmode_seconds >= 0
    ):
        try:
            await message.channel.edit(slowmode_delay=slowmode_seconds)
        except Exception:
            pass

    alert_text = (
        "🚨 **Guard Triggered**\n"
        f"{details}\n"
        f"Applied slowmode: `{slowmode_seconds}s` in {message.channel.mention}."
    )
    try:
        if hasattr(alert_channel, "send"):
            await alert_channel.send(alert_text)
    except Exception:
        pass

    case_id = log_moderation_action(
        guild_id=guild.id,
        action="guard_trigger",
        actor_id=bot.user.id if bot.user else 0,
        reason="Automated guard defense",
        details=details,
        undoable=False,
    )
    await send_ops_log(
        guild,
        f"🛡️ Case `{case_id}` guard trigger in {message.channel.mention}: {details}",
    )


def setup_guard_module(
    bot: commands.Bot,
    *,
    require_mod_context: RequireModContextCallback,
    save_settings: SaveSettingsCallback,
) -> None:
    @bot.hybrid_command(name="guard")
    async def guard(
        ctx: commands.Context,
        enabled: bool | None = None,
        threshold: int | None = None,
        window_seconds: int | None = None,
        slowmode_seconds: int | None = None,
        new_account_hours: int | None = None,
    ):
        """Configure anti-raid guard thresholds."""
        result = await require_mod_context(ctx)
        if not result:
            return
        guild, guild_cfg = result

        if enabled is not None:
            guild_cfg["guard_enabled"] = enabled
        if threshold is not None:
            guild_cfg["guard_threshold"] = max(3, min(100, threshold))
        if window_seconds is not None:
            guild_cfg["guard_window_seconds"] = max(5, min(300, window_seconds))
        if slowmode_seconds is not None:
            guild_cfg["guard_slowmode_seconds"] = max(0, min(21600, slowmode_seconds))
        if new_account_hours is not None:
            guild_cfg["guard_new_account_hours"] = max(1, min(168, new_account_hours))

        save_settings()
        await ctx.send(
            f"🛡️ Guard for **{guild.name}**\n"
            f"- Enabled: `{guild_cfg.get('guard_enabled', False)}`\n"
            f"- Threshold: `{guild_cfg.get('guard_threshold', 8)}`\n"
            f"- Window: `{guild_cfg.get('guard_window_seconds', 30)}s`\n"
            f"- New account age: `{guild_cfg.get('guard_new_account_hours', 24)}h`\n"
            f"- Auto slowmode: `{guild_cfg.get('guard_slowmode_seconds', 30)}s`"
        )
