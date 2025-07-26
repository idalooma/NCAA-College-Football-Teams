import discord
from discord.ext import commands
import json

# Load NCAA teams data from JSON
with open('NCAA_FBS_conferences.json', 'r', encoding='utf-8') as f:
    ncaa_data = json.load(f)

# Flatten teams into a list of dicts with ScrapedName and LogoURL
teams = []
for conference_teams in ncaa_data.values():
    for team in conference_teams:
        teams.append({
            'ScrapedName': team.get('ScrapedName'),
            'LogoURL': team.get('LogoURL')
        })

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

WELCOME_CHANNEL = 'welcome'  # Change to your actual channel name
RULES_CHANNEL = 'rules'      # Change to your actual channel name
TEAM_SELECTION_CHANNEL = 'team-selection'  # Change to your actual channel name
BOT_LOGS_CHANNEL = 'bot-logs'  # New bot logs channel
LEAGUE_MEMBER_ROLE = 'League Member'
ADMIN_ROLE = 'Admin'  # Change to your actual admin role name
MEDIA_ROLE= "Media Team"
@bot.event
async def on_member_join(member):
    # Send welcome message
    guild = member.guild
    bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
    # On join, only allow welcome, rules, and bot-logs channels to be visible
    allowed_channels = [WELCOME_CHANNEL, RULES_CHANNEL, BOT_LOGS_CHANNEL]
    for ch in guild.text_channels:
        if ch.name in allowed_channels:
            await ch.set_permissions(member, view_channel=True, send_messages=False)
        else:
            await ch.set_permissions(member, view_channel=False)
    if bot_logs_channel:
        await bot_logs_channel.send(f"{member.mention} joined the server. Welcome message sent.")

@bot.command()
async def post_rules(ctx):
    """Post the rules message and add reaction for role assignment."""
    if ctx.channel.name != RULES_CHANNEL:
        await ctx.send(f"Please use this command in #{RULES_CHANNEL}.")
        return
    msg = await ctx.send("Please read the rules and react with ✅ to get access to the league channels.\nFull rules: https://docs.google.com/document/d/1O7-63eLjAuyNGR3VeqJu36Y-rFt6gT1FndROiMtSnn8/edit?usp=sharing")
    await msg.add_reaction("✅")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name != "✅":
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    channel = guild.get_channel(payload.channel_id)
    bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
    if channel.name == RULES_CHANNEL:
        role = discord.utils.get(guild.roles, name=LEAGUE_MEMBER_ROLE)
        if role and member:
            await member.add_roles(role)
            # Only unlock #team-selection for the user (read-only except admin)
            for ch in guild.text_channels:
                if ch.name == TEAM_SELECTION_CHANNEL:
                    await ch.set_permissions(member, view_channel=True, send_messages=False)
                elif ch.name not in [WELCOME_CHANNEL, RULES_CHANNEL, BOT_LOGS_CHANNEL]:
                    await ch.set_permissions(member, view_channel=False)
            if bot_logs_channel:
                await bot_logs_channel.send(f"{member.mention} has accepted the rules and can now select a team in #{TEAM_SELECTION_CHANNEL}!")

            # Send team selection dropdown to user's DM
            try:
                # Group teams by conference
                conference_teams = {}
                for conference, teams_list in ncaa_data.items():
                    conference_teams[conference] = teams_list

                max_options = 25
                for conference, teams_list in conference_teams.items():
                    for i in range(0, len(teams_list), max_options):
                        options = []
                        for team in teams_list[i:i+max_options]:
                            options.append(discord.SelectOption(label=team['ScrapedName'], description=team['ScrapedName'], value=team['ScrapedName']))
                        view = discord.ui.View(timeout=None)
                        view.add_item(TeamDropdown(options))
                        await member.send(f"Choose your {conference} conference team:", view=view)
                if bot_logs_channel:
                    await bot_logs_channel.send(f"Sent team selection dropdown to {member.mention}'s DM.")
            except Exception as e:
                if bot_logs_channel:
                    await bot_logs_channel.send(f"Failed to send team selection dropdown to {member.mention}'s DM: {e}")


# Interactive team selection using discord.ui.Select

# Discord dropdowns can only have 25 options max
class TeamSelect(discord.ui.View):
    def __init__(self, teams):
        super().__init__(timeout=None)
        max_options = 25
        for i in range(0, len(teams), max_options):
            options = []
            for team in teams[i:i+max_options]:
                options.append(discord.SelectOption(label=team['ScrapedName'], description=team['ScrapedName'], value=team['ScrapedName']))
            self.add_item(TeamDropdown(options))

class TeamDropdown(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Choose your NCAA team...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        team_name = self.values[0]
        member = interaction.user
        guild = interaction.guild
        # If used in DM, interaction.guild is None
        if guild is None:
            # Try to find the guild from mutual guilds
            # You may want to restrict to your bot's main guild if you have multiple
            if hasattr(member, 'mutual_guilds'):
                # discord.Member has mutual_guilds, discord.User does not
                possible_guilds = member.mutual_guilds
            else:
                possible_guilds = [g for g in bot.guilds if g.get_member(member.id)]
            if possible_guilds:
                guild = possible_guilds[0]
                member = guild.get_member(member.id)
            else:
                await interaction.response.send_message("Could not find your server membership. Please use this in the server.", ephemeral=True)
                return



        # Always get bot_logs_channel before any try/except
        bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)

        role = discord.utils.get(guild.roles, name=team_name)
        if not role:
            try:
                role = await guild.create_role(name=team_name)
            except Exception as e:
                error_msg = f"Failed to create role '{team_name}' for user {member} (ID: {member.id}): {e}"
                if bot_logs_channel:
                    await bot_logs_channel.send(error_msg)
                await create_ticket(guild, member, error_msg)
                await interaction.response.send_message(
                    f"Sorry, I couldn't create the role for '{team_name}'. A support ticket has been opened.", ephemeral=True)
                return
        try:
            await member.add_roles(role)
        except Exception as e:
            error_msg = f"Failed to add role '{team_name}' to user {member} (ID: {member.id}): {e}"
            if bot_logs_channel:
                await bot_logs_channel.send(error_msg)
            await create_ticket(guild, member, error_msg)
            await interaction.response.send_message(
                f"Sorry, I couldn't assign the role '{team_name}' to you. A support ticket has been opened.", ephemeral=True)
            return

        bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
        class NicknameModal(discord.ui.Modal, title="Set Your Nickname"):
            # Truncate default value to 32 characters
            default_nick = f"{member.name} | {team_name}"
            if len(default_nick) > 32:
                default_nick = default_nick[:32]
            nickname = discord.ui.TextInput(
                label="Nickname (must include team name)",
                default=default_nick,
                min_length=3,
                max_length=32
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                new_nick = self.nickname.value.strip()
                team_words = set(team_name.lower().split())
                nick_words = set(new_nick.lower().split())
                if not team_words.intersection(nick_words):
                    await modal_interaction.response.send_message(f"Your nickname must include at least one word from '{team_name}'. Please try again.", ephemeral=True)
                    return
                for m in guild.members:
                    if m.nick and m.nick.lower() == new_nick.lower() and m.id != member.id:
                        await modal_interaction.response.send_message("This nickname is already taken by another member. Please choose a different one.", ephemeral=True)
                        return
                await modal_interaction.response.defer(ephemeral=True)
                error_message = None
                try:
                    await member.edit(nick=new_nick)
                    # Channel permission rules after nickname set
                    media_channels = ["247sports-recruits-crystal-ball", "pre-season-all-americans", "trophy-room"]
                    read_only_channels = [WELCOME_CHANNEL, RULES_CHANNEL, BOT_LOGS_CHANNEL, TEAM_SELECTION_CHANNEL]
                    for ch in guild.text_channels:
                        # welcome, rules, bot-logs, team-selection: always read-only
                        if ch.name in read_only_channels:
                            await ch.set_permissions(member, view_channel=True, send_messages=False)
                        # Media channels: view/read, only Admin/Media Team can send
                        elif ch.name in media_channels:
                            await ch.set_permissions(member, view_channel=True, send_messages=False)
                        # Any channel with "admin" in name: hidden
                        elif "admin" in ch.name:
                            await ch.set_permissions(member, view_channel=False)
                        # All other channels: view/send
                        else:
                            await ch.set_permissions(member, view_channel=True, send_messages=True)
                    # staff only VC: only Admins can view/connect
                    staff_vc = discord.utils.get(guild.voice_channels, name="staff only VC")
                    if staff_vc:
                        await staff_vc.set_permissions(member, view_channel=False, connect=False)
                except Exception as e:
                    error_message = f"Failed to set nickname: {e}"
                if error_message:
                    if bot_logs_channel:
                        await bot_logs_channel.send(f"{member.mention} {error_message}")
                    await create_ticket(guild, member, error_message)
                    await modal_interaction.followup.send(f"There was an error setting your nickname. A support ticket has been opened.", ephemeral=True)
                else:
                    if bot_logs_channel:
                        await bot_logs_channel.send(f"{member.mention} nickname set to: {new_nick}. Access granted to all league channels.")
                    await modal_interaction.followup.send(f"Your nickname has been set to: {new_nick}. You now have access to all league channels!", ephemeral=True)

        await interaction.response.send_modal(NicknameModal())

@bot.command()
async def post_team_selection(ctx):
    """Post interactive team selection dropdown in #team-selection."""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    if ctx.channel.name != TEAM_SELECTION_CHANNEL:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{ctx.author.mention} tried to post team selection in wrong channel.")
        return
    # Group teams by conference
    conference_teams = {}
    for conference, teams_list in ncaa_data.items():
        conference_teams[conference] = teams_list

    max_options = 25
    for conference, teams_list in conference_teams.items():
        # Split teams into chunks of 25 for Discord dropdown limit
        for i in range(0, len(teams_list), max_options):
            options = []
            for team in teams_list[i:i+max_options]:
                options.append(discord.SelectOption(label=team['ScrapedName'], description=team['ScrapedName'], value=team['ScrapedName']))
            view = discord.ui.View(timeout=None)
            view.add_item(TeamDropdown(options))
            await ctx.send(f"Choose your {conference} conference team:", view=view)

# Example handler for team selection (to be expanded with discord.ui)
class ChangeNicknameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ChangeNicknameButton())

class ChangeNicknameButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Change/Reset Nickname & Team", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        import discord.errors
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        member = interaction.user
        guild = interaction.guild or None
        if guild is None:
            # Try to find the guild from mutual guilds
            if hasattr(member, 'mutual_guilds'):
                possible_guilds = member.mutual_guilds
            else:
                possible_guilds = [g for g in bot.guilds if g.get_member(member.id)]
            if possible_guilds:
                guild = possible_guilds[0]
                member = guild.get_member(member.id)
            else:
                return
        bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
        # Remove old team role if present
        old_team_role = None
        for role in member.roles:
            if role.name in [team['ScrapedName'] for team in teams]:
                old_team_role = role
                break
        if old_team_role:
            await member.remove_roles(old_team_role)
        # Send team selection dropdown to DM
        try:
            conference_teams = {}
            for conference, teams_list in ncaa_data.items():
                conference_teams[conference] = teams_list
            max_options = 25
            for conference, teams_list in conference_teams.items():
                for i in range(0, len(teams_list), max_options):
                    options = []
                    for team in teams_list[i:i+max_options]:
                        options.append(discord.SelectOption(label=team['ScrapedName'], description=team['ScrapedName'], value=team['ScrapedName']))
                    view = discord.ui.View(timeout=None)
                    view.add_item(TeamDropdown(options))
                    await member.send(f"Choose your {conference} conference team:", view=view)
            if bot_logs_channel:
                await bot_logs_channel.send(f"Sent team selection dropdown to {member.mention}'s DM.")
        except Exception as e:
            if bot_logs_channel:
                await bot_logs_channel.send(f"Failed to send team selection dropdown to {member.mention}'s DM: {e}")

@bot.command()
async def change_nickname(ctx):
    """Post a button in #team-selection to let users change/reset their nickname and team."""
    if ctx.channel.name != TEAM_SELECTION_CHANNEL:
        await ctx.send(f"Please use this command in #{TEAM_SELECTION_CHANNEL}.")
        return
    view = ChangeNicknameView()
    await ctx.send("Want to change your team or nickname? Click below!", view=view)
async def assign_team_role(member, team_name):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=team_name)
    if not role:
        # Create role if it doesn't exist
        role = await guild.create_role(name=team_name)
    await member.add_roles(role)
    # Update nickname
    await member.edit(nick=f"{team_name}")


@bot.command()
@commands.has_permissions(administrator=True)
async def assign_admin_role(ctx, member: discord.Member):
    """Assign Admin role to a user. Usage: !assign_admin_role @user"""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE)
    if not admin_role:
        if bot_logs_channel:
            await bot_logs_channel.send("Admin role does not exist. Run !setup_basic_roles first.")
        return
    if admin_role in member.roles:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{member.mention} is already an Admin.")
        return
    await member.add_roles(admin_role)
    # Grant full access to media channels
    media_channels = ["247sports-recruits-crystal-ball", "pre-season-all-americans", "trophy-room"]
    for ch_name in media_channels:
        ch = discord.utils.get(ctx.guild.text_channels, name=ch_name)
        if ch:
            await ch.set_permissions(member, view_channel=True, send_messages=True)
    # Grant access to all admin channels
    for ch in ctx.guild.text_channels:
        if "admin" in ch.name:
            await ch.set_permissions(member, view_channel=True, send_messages=True)
    # Grant access to staff only VC
    staff_vc = discord.utils.get(ctx.guild.voice_channels, name="staff only VC")
    if staff_vc:
        await staff_vc.set_permissions(member, view_channel=True, connect=True)
    if bot_logs_channel:
        await bot_logs_channel.send(f"{member.mention} has been added to Admins.")


# Command to create League Member and Admin roles
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_basic_roles(ctx):
    """Create League Member and Admin roles if they don't exist."""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    created = []
    for role_name in [LEAGUE_MEMBER_ROLE, ADMIN_ROLE, MEDIA_ROLE]:
        if not discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.guild.create_role(name=role_name)
            created.append(role_name)
    if created:
        if bot_logs_channel:
            await bot_logs_channel.send(f"Created roles: {', '.join(created)}")
    else:
        if bot_logs_channel:
            await bot_logs_channel.send("League Member and Admin roles already exist.")

# Command to create all team roles automatically
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_team_roles(ctx):
    """Create all team roles using ScrapedName from the JSON data."""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    created = []
    for team in teams:
        role_name = team['ScrapedName']
        if not discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.guild.create_role(name=role_name)
            created.append(role_name)
    if created:
        # Discord messages must be <= 2000 characters
        msg = "Created roles: "
        chunk = []
        total_len = len(msg)
        for role_name in created:
            if total_len + len(role_name) + 2 > 2000:
                if bot_logs_channel:
                    await bot_logs_channel.send(msg + ", ".join(chunk))
                chunk = []
                total_len = len(msg)
            chunk.append(role_name)
            total_len += len(role_name) + 2
        if chunk:
            if bot_logs_channel:
                await bot_logs_channel.send(msg + ", ".join(chunk))
    else:
        if bot_logs_channel:
            await bot_logs_channel.send("All team roles already exist.")


@bot.command()
@commands.has_permissions(administrator=True)
async def assign_media_role(ctx, member: discord.Member):
    """Assign Media Team role to a League Member. Usage: !assign_media_role @user"""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    league_role = discord.utils.get(ctx.guild.roles, name=LEAGUE_MEMBER_ROLE)
    media_role = discord.utils.get(ctx.guild.roles, name=MEDIA_ROLE)
    if not league_role or not media_role:
        if bot_logs_channel:
            await bot_logs_channel.send("Required roles do not exist. Run !setup_basic_roles first.")
        return
    if league_role not in member.roles:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{member.mention} is not a League Member.")
        return
    if media_role in member.roles:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{member.mention} is already in the Media Team.")
        return
    await member.add_roles(media_role)
    # Grant full access to media channels
    media_channels = ["247sports-recruits-crystal-ball", "pre-season-all-americans", "trophy-room"]
    for ch_name in media_channels:
        ch = discord.utils.get(ctx.guild.text_channels, name=ch_name)
        if ch:
            await ch.set_permissions(member, view_channel=True, send_messages=True)
    if bot_logs_channel:
        await bot_logs_channel.send(f"{member.mention} has been added to the Media Team.")

@bot.command()
@commands.has_permissions(administrator=True)
async def remove_media_role(ctx, member: discord.Member):
    """Remove Media Team role from a user and revoke media channel access."""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    media_role = discord.utils.get(ctx.guild.roles, name=MEDIA_ROLE)
    if not media_role:
        if bot_logs_channel:
            await bot_logs_channel.send("Media Team role does not exist.")
        return
    if media_role not in member.roles:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{member.mention} is not in the Media Team.")
        return
    await member.remove_roles(media_role)
    # Revoke send access to media channels
    media_channels = ["247sports-recruits-crystal-ball", "pre-season-all-americans", "trophy-room"]
    for ch_name in media_channels:
        ch = discord.utils.get(ctx.guild.text_channels, name=ch_name)
        if ch:
            await ch.set_permissions(member, send_messages=False)
    if bot_logs_channel:
        await bot_logs_channel.send(f"{member.mention} has been removed from the Media Team.")

@bot.command()
@commands.has_permissions(administrator=True)
async def remove_admin_role(ctx, member: discord.Member):
    """Remove Admin role from a user and revoke admin channel and staff only VC access."""
    bot_logs_channel = discord.utils.get(ctx.guild.text_channels, name=BOT_LOGS_CHANNEL)
    admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE)
    if not admin_role:
        if bot_logs_channel:
            await bot_logs_channel.send("Admin role does not exist.")
        return
    if admin_role not in member.roles:
        if bot_logs_channel:
            await bot_logs_channel.send(f"{member.mention} is not an Admin.")
        return
    await member.remove_roles(admin_role)
    # Revoke access to admin channels
    for ch in ctx.guild.text_channels:
        if "admin" in ch.name:
            await ch.set_permissions(member, view_channel=False, send_messages=False)
    # Revoke access to staff only VC
    staff_vc = discord.utils.get(ctx.guild.voice_channels, name="staff only VC")
    if staff_vc:
        await staff_vc.set_permissions(member, view_channel=False, connect=False)
    if bot_logs_channel:
        await bot_logs_channel.send(f"{member.mention} has been removed from Admins.")

# Command to set channel permissions
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_permissions(ctx):
    guild = ctx.guild
    # Create 'staff only VC' voice channel if it doesn't exist
    staff_vc_name = "staff only VC"
    if not discord.utils.get(guild.voice_channels, name=staff_vc_name):
        await guild.create_voice_channel(staff_vc_name)

    """Set channel permissions for welcome, rules, league, and admin-only channels."""
    everyone = guild.default_role
    league_member = discord.utils.get(guild.roles, name=LEAGUE_MEMBER_ROLE)
    admin = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if not league_member or not admin:
        if bot_logs_channel:
            await bot_logs_channel.send("Please run !setup_basic_roles first.")
        return
    changed = []
    # Create special media channels if they don't exist
    media_channels = [
        "trophy-room",
        "pre-season-all-americans",
        "247sports-recruits-crystal-ball"
    ]
    bot_logs_channel = discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL)
    for ch_name in media_channels:
        if not discord.utils.get(guild.text_channels, name=ch_name):
            await guild.create_text_channel(ch_name)
    # Ensure bot-logs channel exists
    if not discord.utils.get(guild.text_channels, name=BOT_LOGS_CHANNEL):
        await guild.create_text_channel(BOT_LOGS_CHANNEL)

    for channel in guild.text_channels:
        # Welcome and rules: everyone can view and read
        if channel.name in [WELCOME_CHANNEL, RULES_CHANNEL]:
            await channel.set_permissions(everyone, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(league_member, view_channel=True, read_messages=True, send_messages=False)
            media_role = discord.utils.get(guild.roles, name=MEDIA_ROLE)
            if media_role:
                await channel.set_permissions(media_role, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(admin, view_channel=True, read_messages=True, send_messages=True)
            changed.append(channel.name)
        # bot-logs: everyone can view and read, only admin can send
        elif channel.name == BOT_LOGS_CHANNEL:
            await channel.set_permissions(everyone, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(league_member, view_channel=True, read_messages=True, send_messages=False)
            media_role = discord.utils.get(guild.roles, name=MEDIA_ROLE)
            if media_role:
                await channel.set_permissions(media_role, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(admin, view_channel=True, read_messages=True, send_messages=True)
            changed.append(channel.name)
        # team-selection: everyone can view and read, only admin can send
        elif channel.name == TEAM_SELECTION_CHANNEL:
            await channel.set_permissions(everyone, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(league_member, view_channel=True, read_messages=True, send_messages=False)
            media_role = discord.utils.get(guild.roles, name=MEDIA_ROLE)
            if media_role:
                await channel.set_permissions(media_role, view_channel=True, read_messages=True, send_messages=False)
            await channel.set_permissions(admin, view_channel=True, read_messages=True, send_messages=True)
            changed.append(channel.name)
        # Media channels: hidden from League Members by default, only Media Team and Admin can view/post
        elif channel.name in media_channels:
            await channel.set_permissions(everyone, view_channel=False)
            await channel.set_permissions(league_member, view_channel=False)  # Hide from League Members until nickname is set
            await channel.set_permissions(admin, view_channel=True, read_messages=True, send_messages=True)
            media_role = discord.utils.get(guild.roles, name=MEDIA_ROLE)
            if media_role:
                await channel.set_permissions(media_role, view_channel=True, read_messages=True, send_messages=True)
            changed.append(channel.name)
        else:
            # All other channels hidden from @everyone by default
            await channel.set_permissions(everyone, view_channel=False)
            # Admin-only channels: only admins can view/send
            if 'admin' in channel.name:
                await channel.set_permissions(league_member, view_channel=False)
                media_role = discord.utils.get(guild.roles, name=MEDIA_ROLE)
                if media_role:
                    await channel.set_permissions(media_role, view_channel=False)
                await channel.set_permissions(admin, view_channel=True, send_messages=True)
            # #team-selection: only League Members and Admins
            elif channel.name == TEAM_SELECTION_CHANNEL:
                await channel.set_permissions(league_member, view_channel=True, send_messages=True)
                await channel.set_permissions(admin, view_channel=True, send_messages=True)
            # Other channels: only League Members and Admins
            else:
                await channel.set_permissions(league_member, view_channel=False)
                await channel.set_permissions(admin, view_channel=False)
            changed.append(channel.name)

    # Set permissions for 'staff only VC' voice channel
    staff_vc = discord.utils.get(guild.voice_channels, name=staff_vc_name)
    if staff_vc:
        await staff_vc.set_permissions(everyone, view_channel=False, connect=False)
        await staff_vc.set_permissions(admin, view_channel=True, connect=True)
        changed.append(staff_vc.name)
    if bot_logs_channel:
        await bot_logs_channel.send(f"Permissions set for channels: {', '.join(changed)}")

# Admin command to close a ticket
@bot.command()
@commands.has_permissions(administrator=True)
async def close_ticket(ctx, member: discord.Member):
    """Close a user's ticket channel. Usage: !close_ticket @user"""
    ticket_channel_name = f"ticket-{member.id}"
    ticket_channel = discord.utils.get(ctx.guild.text_channels, name=ticket_channel_name)
    if not ticket_channel:
        await ctx.send(f"No open ticket found for {member.mention}.")
        return
    await ticket_channel.delete()
    await ctx.send(f"Ticket for {member.mention} has been closed.")

# Helper: Create a ticket channel for a user and notify admins
async def create_ticket(guild, user, error_message):
    ticket_channel_name = f"ticket-{user.id}"
    # Check if ticket already exists
    existing = discord.utils.get(guild.text_channels, name=ticket_channel_name)
    if existing:
        await existing.send(f"Another error occurred: {error_message}")
        return existing
    # Create channel, only user and admins can see
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
    }
    admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
    ticket_channel = await guild.create_text_channel(ticket_channel_name, overwrites=overwrites, topic=f"Support ticket for {user.display_name}")
    await ticket_channel.send(f"Hello {user.mention}, a ticket has been created for your error:\n> {error_message}\nAn admin will assist you here.")
    return ticket_channel
# To run the bot, uncomment and add your token:
bot.run('')
