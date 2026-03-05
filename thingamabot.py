import discord
from discord.ext import commands
import json
import os
from mcstatus import JavaServer
from discord.ext import commands
import requests
from discord import Embed
from vote import setup_vote_module



intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
intents = discord.Intents.default()
intents.message_content = True

setup_vote_module(bot)



AI_SERVER_URL = "http://localhost:3001/ask"  # replace with your local AI server URL
@bot.command()
async def vanguard(ctx, *, question: str):
    """Ask the AI a question and get a response"""
    async with ctx.typing():  # shows typing indicator
        payload = {
            "question": question,
            "username": str(ctx.author),   # Discord username#discriminator
            "userId": str(ctx.author.id)   # Discord user ID as string
        }

        try:
            response = requests.post(AI_SERVER_URL, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "Ingen respons från AI.")
            else:
                title_text = "Vanguard AI encountered an issue. Please contact an Admin. Try again later."
                answer = ""
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            title_text = "Vanguard AI is currently offline or unreachable. Please contact an Admin to resolve the issue. Try again later."
            answer = ""
        except Exception:
            title_text = "An unexpected error occurred with Vanguard AI. Please contact an Admin. Try again later."
            answer = ""
        else:
            title_text = "Vanguard AI Response"

    embed = discord.Embed(
        title=title_text,
        description=answer,
        color=discord.Color.red()
    )
    embed.set_footer(text="Powered by Vanguard AI")
    await ctx.send(embed=embed)
    
# Owner-only decorator
def is_owner():
    def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)
    
import re
import requests

FUCK_URL = "http://localhost:3001/fuck"
UNFUCK_URL = "http://localhost:3001/unfuck"

id_re = re.compile(r'(\d{17,20})')  # matches usual Discord IDs

def extract_id(target: str):
    """Return numeric ID from a mention or raw ID, or None."""
    if not target:
        return None
    # If it's already just digits, return it
    if target.isdigit():
        return target
    # Try to find digits inside a mention like <@123...> or <@!123...>
    m = id_re.search(target)
    if m:
        return m.group(1)
    return None

@bot.command()
@is_owner()
async def fuck(ctx, target: str):
    """Mark a user as 'fucked' by ID or mention."""
    user_id = extract_id(target)
    if not user_id:
        await ctx.send("⚠️ Provide a mention (`@user`) or the raw numeric ID.")
        return

    payload = {"userId": str(user_id)}
    try:
        r = requests.post(FUCK_URL, json=payload, timeout=6)
    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ Request error: `{e}` — check that the AI server is running and that `FUCK_URL` is correct/reachable from this bot.")
        return

    # helpful debug on non-200
    if r.status_code != 200:
        await ctx.send(
            f"⚠️ Could not mark <@{user_id}> as fucked. "
            f"Status: {r.status_code}. Response: ```{r.text}```"
        )
        return

    # success: try to resolve the member in this guild for a nice mention
    mention = f"<@{user_id}>"
    try:
        member = await ctx.guild.fetch_member(int(user_id))
        mention = member.mention
    except Exception:
        # if fetch fails, keep fallback mention
        pass

    # If backend returns a JSON message, show it
    backend_msg = ""
    try:
        backend_msg = r.json().get("message", "")
    except Exception:
        backend_msg = r.text

    await ctx.send(f"✅ {mention} is now marked as fucked. `{backend_msg}`")


@bot.command()
@is_owner()
async def unfuck(ctx, target: str):
    """Remove a user from 'fucked' status by ID or mention."""
    user_id = extract_id(target)
    if not user_id:
        await ctx.send("⚠️ Provide a mention (`@user`) or the raw numeric ID.")
        return

    payload = {"userId": str(user_id)}
    try:
        r = requests.post(UNFUCK_URL, json=payload, timeout=6)
    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ Request error: `{e}` — check that the AI server is running and that `UNFUCK_URL` is correct/reachable from this bot.")
        return

    if r.status_code != 200:
        await ctx.send(
            f"⚠️ Could not unfuck <@{user_id}>. Status: {r.status_code}. Response: ```{r.text}```"
        )
        return

    mention = f"<@{user_id}>"
    try:
        member = await ctx.guild.fetch_member(int(user_id))
        mention = member.mention
    except Exception:
        pass

    backend_msg = ""
    try:
        backend_msg = r.json().get("message", "")
    except Exception:
        backend_msg = r.text

    await ctx.send(f"✅ {mention} is now unfucked. `{backend_msg}`")


WELCOME_CHANNEL_ID = 1409932263482855486  # replace with your channel ID
WELCOME_ROLE_NAME = "None"             # optional: auto-assign role on join (or set to None)

@bot.event
async def on_ready():
    print(f"[READY] Logged in as {bot.user} ({bot.user.id})")

def make_welcome_embed(member):
    name = member.display_name
    guild_name = member.guild.name
    avatar_url = None
    try:
        avatar_url = member.display_avatar.url
    except Exception:
        avatar_url = None

    embed = discord.Embed(
        title="✨ Välkommen! ✨",
        description=f"Hej {member.mention}, kul att du har gått med i **{guild_name}**! 🎉",
        color=discord.Color.red()
    )
    embed.add_field(
        name="📜 Regler",
        value="Se till att läsa våra regler med `!rules` innan du börjar skriva.",
        inline=False
    )
    embed.add_field(
        name="💬 Tips",
        value="Håll dig till rätt kanal för rätt ämne, och var schysst mot andra! 🙌",
        inline=False
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="Vi är glada att ha dig här!")
    return embed

@bot.event
async def on_member_join(member):
    try:
        print(f"[DEBUG] on_member_join fired for {member} ({member.id}) in guild {member.guild.name}")
        
        # Try channel by ID first
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        # fallback to guild.system_channel if not configured
        if channel is None:
            channel = member.guild.system_channel
            print(f"[DEBUG] welcome channel by ID not found; using system_channel")
        
        if channel is None:
            # As a final fallback, try the first text channel the bot can send messages in
            for ch in member.guild.text_channels:
                perms = ch.permissions_for(member.guild.me)
                if perms.send_messages and perms.embed_links:
                    channel = ch
                    print(f"[DEBUG] fallback found channel {ch.name} ({ch.id})")
                    break

        if channel is None:
            print("[WARN] No suitable channel to send welcome message (no permissions)")
            return

        # Build and send embed
        embed = make_welcome_embed(member)
        await channel.send(embed=embed)
        print(f"[INFO] Sent welcome embed to channel {channel.name} ({channel.id})")

        # Optional: auto-assign a role
        if WELCOME_ROLE_NAME:
            role = discord.utils.get(member.guild.roles, name=WELCOME_ROLE_NAME)
            if role:
                await member.add_roles(role, reason="Auto-assign on join")
                print(f"[INFO] Assigned role {WELCOME_ROLE_NAME} to {member}")
            else:
                print(f"[WARN] Role named {WELCOME_ROLE_NAME} not found.")

        # Ping admins
        ADMIN_ROLE_NAMES = ["Admin"]  # replace with your actual admin/mod role names
        admin_mentions = []
        for role_name in ADMIN_ROLE_NAMES:
            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                admin_mentions.append(role.mention)

        if admin_mentions:
            await channel.send(f"⚠️ Attention {', '.join(admin_mentions)}! New member {member.mention} has joined.")

    except Exception as e:
        print(f"[ERROR] Exception in on_member_join: {e}")



# Test command so you can simulate a welcome without rejoining
@bot.command()
async def testwelcome(ctx, target: discord.Member = None):
    target = target or ctx.author
    embed = make_welcome_embed(target)
    channel = ctx.channel
    await channel.send(embed=embed)
    await ctx.send("Test welcome sent (visible to everyone here).")



@bot.command()
async def rules(ctx):
    embed = discord.Embed(
        title="📜 Serverregler",
        description=(
            "Visa respekt – behandla alla medlemmar vänligt, inga förolämpningar, mobbning eller trakasserier.\n\n"
            "Ingen spamming – undvik flood av meddelanden, emojis eller @-pings i onödan.\n\n"
            "Håll chatten relevant – skriv i rätt kanal för rätt ämne.\n\n"
            "Ingen olämplig content – inget NSFW, våldsamt eller stötande material.\n\n"
            "Ingen reklam – dela inte länkar till externa servrar eller reklam utan tillåtelse från admin/mod.\n\n"
            "Använd skolans riktlinjer – samma regler gäller här som i klassrummet (respekt för varandra, språket, osv).\n\n"
            "Sekretess – dela inte andras personliga uppgifter eller privata bilder utan deras godkännande.\n\n"
            "Röstkanaler – var schysst, avbryt inte andra och använd push-to-talk om din mikrofon stör.\n\n"
            "Följ admins och moddar – deras beslut gäller, respektera varningar och påpekanden.\n\n"
            "Ha kul och samarbeta – servern är till för att underlätta skolarbetet och skapa gemenskap."
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="⚠️ Om du bryter mot reglerna och inte klarar att följa dem får du en timeout.")
    await ctx.send(embed=embed)


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild

    # Fetch the actual owner user object
    owner = await guild.fetch_member(guild.owner_id)

    embed = discord.Embed(
        title=f"ℹ️ Info om {guild.name}",
        color=discord.Color.red()
    )
    embed.add_field(name="👑 Ägare", value=owner.mention if owner else "Okänd", inline=False)
    embed.add_field(name="📅 Skapad", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="👥 Medlemmar", value=guild.member_count, inline=False)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)



MC_IP = "mpmc.ddns.net"  # e.g. "play.example.com"
MC_PORT = 25565  # default Minecraft port

@bot.command()
async def mcstatus(ctx):
    server = JavaServer(MC_IP, MC_PORT)
    try:
        status = server.status()
        await ctx.send(f"✅ The Minecraft server is online! Players: {status.players.online}/{status.players.max}")
    except Exception:
        await ctx.send("❌ The Minecraft server is offline or unreachable.")





# ---------- CONFIG ----------
OWNER_ID = 943154713753423984  # replace with your Discord ID (int)
SETTINGS_FILE = "settings.json"
# ----------------------------


# load/save settings
default_settings = {"owner_only": False}
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(default_settings, f)
with open(SETTINGS_FILE, "r") as f:
    settings = json.load(f)

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

# Global check: if owner_only is True, only OWNER_ID can run commands
@bot.check
async def global_owner_check(ctx):
    # allow the bot itself to run internal stuff
    if ctx.author == bot.user:
        return True
    # If not in owner-only mode, allow everything (other command-level checks still apply)
    if not settings.get("owner_only", False):
        return True
    # Owner-only mode: allow only the owner
    return ctx.author.id == OWNER_ID

# Owner-only utility decorator (to protect toggles)
def is_owner():
    def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

# --- Command to enable owner-only mode ---
@bot.command()
@is_owner()
async def obey(ctx, confirmation: str = None):
    """
    Enable owner-only mode. Must pass 'confirm' to actually activate.
    Usage: !obey confirm
    """
    if confirmation != "confirm":
        await ctx.send("This will make the bot owner-only. To confirm, run `!obey confirm`.")
        return

    settings["owner_only"] = True
    save_settings()
    await ctx.send("🔐 Owner-only mode ENABLED. Only my owner may use commands now.")

# --- Command to disable owner-only mode ---
@bot.command()
@is_owner()
async def release(ctx, confirmation: str = None):
    """
    Disable owner-only mode. Must pass 'confirm' to actually deactivate.
    Usage: !release confirm
    """
    if confirmation != "confirm":
        await ctx.send("To disable owner-only mode, run `!release confirm`.")
        return

    settings["owner_only"] = False
    save_settings()
    await ctx.send("🔓 Owner-only mode DISABLED. Commands are available again.")




LOCKDOWN_ROLE_NAME = "Classmate"
MOD_ROLES = ["Admin"]

# Emergency Lockdown
@bot.command()
async def lockdown(ctx):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("⛔ You do not have permission to activate the lockdown.")
        return

    # Replace with the actual role name you want to lock down
    target_role = discord.utils.get(ctx.guild.roles, name="Classmate")  
    if not target_role:
        await ctx.send("⚠️ Target role not found.")
        return

    for channel in ctx.guild.text_channels:
        overwrite = channel.overwrites_for(target_role)
        overwrite.send_messages = False
        await channel.set_permissions(target_role, overwrite=overwrite)

    embed = discord.Embed(
        title="🚨 EMERGENCY LOCKDOWN 🚨",
        description="All member communication has been disabled.\nOnly mods/admins may speak.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Activated by {ctx.author.display_name}")
    await ctx.send(embed=embed)

# Unlock
@bot.command()
async def unlock(ctx):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("⛔ You do not have permission to lift the lockdown.")
        return

    target_role = discord.utils.get(ctx.guild.roles, name="Classmate")
    if not target_role:
        await ctx.send("⚠️ Target role not found.")
        return

    for channel in ctx.guild.text_channels:
        overwrite = channel.overwrites_for(target_role)
        overwrite.send_messages = True
        await channel.set_permissions(target_role, overwrite=overwrite)

    embed = discord.Embed(
        title="✅ LOCKDOWN LIFTED",
        description="Members can now communicate normally.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Lifted by {ctx.author.display_name}")
    await ctx.send(embed=embed)
    
    
@bot.command(name="voteinfo")
async def voteinfo(ctx, vote_id: str):
    """Show who voted for what in a specific vote."""
    vote = votes.get(vote_id)
    if not vote:
        return await ctx.send("❌ Vote not found.")

    lines = []
    for user_id, choice in vote["votes"].items():
        user = ctx.guild.get_member(int(user_id))
        username = user.display_name if user else f"Unknown ({user_id})"
        lines.append(f"{username}: {choice}")

    if not lines:
        await ctx.send("No votes yet.")
    else:
        await ctx.send("**Vote results so far:**\n" + "\n".join(lines))




bot.run('REDACTED_TOKEN');
