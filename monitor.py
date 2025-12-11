import json
import threading
import time
import sseclient
import requests
import asyncio
from config import load_config

config = load_config()
PAGE_TITLES = [
    "Wikipedia:仲裁/請求",
    "Wikipedia:仲裁/請求/動議",
    "Wikipedia:仲裁/請求/案件"
]
STREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"

def monitor_loop(bot_app, loop):
    """
    Background loop to monitor Wikipedia edits.
    """
    print("Starting Wikipedia monitor...")
    while True:
        try:
            # Use requests with stream=True for better stability
            headers = {'User-Agent': 'ArbitrationBot/1.0 (https://github.com/yourusername/bot; your@email.com)'}
            response = requests.get(STREAM_URL, stream=True, timeout=30, headers=headers)
            client = sseclient.SSEClient(response)
            for event in client.events():
                if event.event == 'message':
                    try:
                        data = json.loads(event.data)
                        process_event(data, bot_app, loop)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Monitor connection lost: {e}. Reconnecting in 30s...")
            time.sleep(30)

def process_event(data, bot_app, loop):
    if data.get('wiki') != 'zhwiki':
        return
    if data.get('type') != 'edit':
        return
    
    title = data.get('title')
    if title not in PAGE_TITLES:
        return
        
    # Found a match
    user = data.get('user')
    timestamp = data.get('timestamp') # Unix timestamp
    comment = data.get('comment', 'No summary')
    diff_url = data.get('server_url', '') + '/w/index.php?diff=' + str(data.get('revision', {}).get('new'))
    
    msg = (
        f"🔔 <b>新仲裁請求 / 編輯</b>\n\n"
        f"<b>頁面：</b> <a href=\"{data.get('server_url')}/wiki/{title}\">{title}</a>\n"
        f"<b>用戶：</b> {user}\n"
        f"<b>摘要：</b> {comment}\n"
        f"<a href=\"{diff_url}\">查看差異</a>"
    )
    
    # Send message safely from thread
    asyncio.run_coroutine_threadsafe(
        bot_app.bot.send_message(
            chat_id=config['arbcom_group_id'],
            text=msg,
            parse_mode='HTML'
        ),
        loop
    )

def start_monitor(application, loop):
    """
    Starts the monitor in a separate thread.
    """
    thread = threading.Thread(target=monitor_loop, args=(application, loop), daemon=True)
    thread.start()
