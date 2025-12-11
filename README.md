# Telegram Bot

A Python-based Telegram bot with SQLite database integration, featuring motion tracking, voting systems, and arbitration tools.

## Features
- **Motion System**: Create, vote, and manage motions.
- **Arbitration**: Add/remove arbitrators and manage permissions.
- **Logging**: detailed voting logs.
- **Multilingual Support**: Supports Traditional Chinese (zh-hant).

## Requirements
- Python 3.8+
- SQLite3
- A Telegram Bot Token (from @BotFather)

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure the Bot
1. Copy the example config file:
   ```bash
   cp config.json.example config.json
   ```
2. Open `config.json` and fill in your details:
   - `bot_token`: Your Telegram Bot Token.
   - `owner_id`: Your Telegram User ID.
   - `arbcom_group_id`: ID of the arbitration committee group.
   - `archive_channel_id`: ID of the channel for logs.

## VPS Deployment

To keep the bot running 24/7 on a VPS, it is recommended to use `systemd`.

### 1. Create a Systemd Service
Create a service file at `/etc/systemd/system/telegrambot.service`:

```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
User=root
# Change this to your project directory
WorkingDirectory=/path/to/your/bot/directory
# Path to python in your virtualenv
ExecStart=/path/to/your/bot/directory/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegrambot
sudo systemctl start telegrambot
```

### 3. Check Status
```bash
sudo systemctl status telegrambot
```
