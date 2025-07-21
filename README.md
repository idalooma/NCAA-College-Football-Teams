# NCAA Discord Bot Setup & Usage Guide

## Overview
This bot automates role assignment, permissions, and team selection for your NCAA Football League Discord server. It uses your team data and custom emojis for a seamless experience.

---

## Manual Server Setup
1. **Create Your Discord Server**
   - Click the "+" in Discord and select "Create My Own".
2. **Create Channels**
   - #welcome
   - #rules
   - #team-selection
   - #general
   - #scores
   - #admin-chat
   - Trophy Room
   - Pre Season All Americans
   - 247Sports Recruits Crystal Ball
   - staff only VC (voice channel for admins only)
3. **Invite Your Bot**
   - Create a bot in the Discord Developer Portal.
   - Copy your bot token and add it to your script.
   - Use the OAuth2 URL to invite your bot to the server.

---

## Custom Emoji Setup (Team Logos)
1. **Download all team logos** from your JSON's LogoURL fields.
2. **Upload each logo as a custom emoji** in Server Settings > Emoji.
   - Name each emoji after the team (e.g., `notredame`, `lsu`).
   - Discord will show the code as `:notredame:`.
3. **Update your JSON file**
   - Replace each team's LogoURL with its emoji code (e.g., `:notredame:`).

---

## Bot Commands
- `!setup_basic_roles` — Creates "League Member", "Admin", and "Media Team" roles.
- `!setup_team_roles` — Creates all team roles from your JSON.
- `!setup_permissions` — Sets channel permissions for all channels, creates special media channels and a staff-only voice channel.
- `!post_rules` — Posts the rules message in #rules.
- `!post_team_selection` — Posts interactive team selection dropdowns in #team-selection, grouped by conference.
- `!assign_media_role @user` — Assigns the Media Team role to a League Member (user keeps both roles).
- `!assign_admin_role @user` — Assigns the Admin role to a user (makes them an admin).
- `!remove_media_role @user` — Removes the Media Team role from a user and revokes their access to media channels.
- `!remove_admin_role @user` — Removes the Admin role from a user and revokes their access to admin channels and staff-only voice channel.

---

## Channel & Role Behavior
- **#welcome** and **#rules**: Only Admins can send messages; all other roles can view/read only.
- **#team-selection**: League Members and Admins can view and select teams.
- **Media Channels** (`Trophy Room`, `Pre Season All Americans`, `247Sports Recruits Crystal Ball`): Media Team and Admins can post; League Members can view/read only.
- **staff only VC**: Voice channel for Admins only (view/connect).
- **Other channels**: Access is managed by the bot based on role and team selection.

---

## User Experience
1. **User joins the server**
   - Sees only #welcome and #rules.
2. **User reads and reacts to rules**
   - Bot assigns "League Member" role and unlocks other channels.
3. **User goes to #team-selection**
   - Bot displays dropdowns for each conference, with team names and logo emojis.
   - User selects their team.
   - Bot assigns the team role and updates the user's nickname to include the logo emoji and team name.

---

## Notes
- Only custom emojis (not image URLs) can be used in nicknames and dropdowns.
- Regular servers support up to 50 custom emojis; boost for more.
- Make sure your JSON uses emoji codes for the LogoURL field.

---

## Troubleshooting
- If you hit Discord limits (dropdowns, emojis), split your setup or boost your server.
- If the bot doesn't respond, check permissions and that your token is correct.

---

## Example JSON Entry
```json
{
  "School": "Notre Dame",
  "ScrapedName": "Notre Dame Fighting Irish",
  "LogoURL": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/ncaa/500/87.png&scale=crop&cquality=40&location=origin&w=80&h=80"
}
```

---

## Contact
For help or customization, reach out to your bot developer.
