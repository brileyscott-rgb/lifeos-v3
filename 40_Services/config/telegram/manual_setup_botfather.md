# Manual BotFather Setup Instructions

These steps are done once, manually, outside this scaffold. No token is created or stored here.

## Steps

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts:
   - Bot name: `LifeOS Bot` (or your preferred name)
   - Bot username: `lifeos_v3_bot` (or similar; must end in `bot`)
3. BotFather will reply with an API token:
   ```
   FAKE_EXAMPLE_REPLACE_WITH_REAL_BOTFATHER_TOKEN
   ```
4. **Copy the token immediately.** It is only shown once by BotFather.
5. Save the token locally in an ignored file:
   ```bash
   cp /home/lifeos/40_Services/config/telegram/.env.example \
      /home/lifeos/40_Services/config/telegram/.env
   # Edit .env and paste the token as TELEGRAM_BOT_TOKEN
   ```
6. Get your Telegram user ID:
   - Send any message to `@userinfobot`
   - It will reply with your numeric user ID
   - Set this as `TELEGRAM_ALLOWED_USER_ID` in `.env`
7. Set the bot commands for auto-complete:
   ```text
   /setcommands
   ```
   Paste:
   ```
   capture - Quick capture a note
   link - Save a link with optional note
   idea - Log an idea
   project - Post a project update
   approve - Approve a pending capture
   reject - Reject a pending capture
   status - Request system status
   help - Show available commands
   ```

## What Happens Next

After token setup, the bot exists but does nothing until a bot handler (Python script or n8n workflow) is activated and approved. Do not start a bot handler without explicit LifeOS approval.
