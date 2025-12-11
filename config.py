import json
import os
import sys

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Please create it from the template.")
        sys.exit(1)
        
    with open(CONFIG_FILE, 'r') as f:
        try:
            config = json.load(f)
            required_keys = ["bot_token", "owner_id", "arbcom_group_id", "archive_channel_id"]
            missing = [key for key in required_keys if key not in config]
            
            if missing:
                print(f"Error: Missing configuration keys: {', '.join(missing)}")
                sys.exit(1)
                
            return config
        except json.JSONDecodeError:
            print(f"Error: Failed to decode {CONFIG_FILE}. Please ensure it is valid JSON.")
            sys.exit(1)
