# Telegram Security Notes

## Token Handling

- The Telegram bot token is a **secret**. It must never be committed to Git.
- Store the real token only in an ignored `.env` file under `40_Services/config/telegram/.env` or in `40_Services/secrets/`.
- `.env.example` contains placeholder values only. Never write a real token there.
- The token grants API access. Anyone with the token can control the bot.

## User ID Restriction

- The `TELEGRAM_ALLOWED_USER_ID` environment variable should restrict the bot to respond only to your Telegram user ID.
- This prevents unauthorized users from interacting with the LifeOS bot if the token is exposed.

## Data Sensitivity

- All messages sent to the bot are logged as raw capture files under `30_Capture/`.
- Do not send passwords, SSH keys, API keys, financial info, or highly personal data via Telegram.
- If sensitive data is accidentally captured, the pending_review queue allows deletion before vault integration.

## Network

- The bot will listen for Telegram webhooks or poll the Telegram API.
- No inbound ports need to be exposed if using long-polling (python-telegram-bot or similar).
- For webhook mode, a public HTTPS endpoint is required. This should use a reverse proxy with TLS.

## Future Automation

- n8n Telegram triggers must use restricted webhook secrets, not raw bot tokens.
- n8n credentials must be stored in the n8n encrypted database, never in plaintext workflow JSON.
- Monitor failed workflow alerts for suspicious activity.
