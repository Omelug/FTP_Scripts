import json
import os
import sys

folder_path = os.path.dirname(os.path.abspath(__file__))


if not os.path.exists("ftp_secret.py"):
    with open("ftp_secret.py", 'w+') as f:
        print("DATABASE_URL_ASYNC = 'postgresql+asyncpg://<database username>:<password>@localhost:5432/<db_name>'", file=f)
        print("Please, edit ftp_secret.py")
    exit(0)
else:
    from ftp_secret import DATABASE_URL_ASYNC

DEFAULT_CONFIG = {
        "ftp_hub": {
            "output_folder": f"{folder_path}/output/",
            "input_folder": f"{folder_path}/input/",
            "ranges": f"./ranges.txt",
            "crack_file": "./ftp_default_user_pass_list.txt",
            "old_delay_days": 7,
            "color_output": True
        },
        "ftp_forest": {
            "save_trees": True,
            "connect_timeout": 30,
            "forest_timeout": 3600, #hour
            "max_workers": 300,
            "max_tree_level": 50
        },
        "ftp_db": {
            "DATABASE_URL_ASYNC": DATABASE_URL_ASYNC,
            "db_path": f"{folder_path}/ftp_hub.db"
        }
    }

global CONFIG

def generate_default():
    with open("config.json", 'w') as f:
        json.dump(CONFIG, f, indent=4)

def load_config(config_file="config.json"):
    global CONFIG
    CONFIG = DEFAULT_CONFIG.copy()
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            file_config = json.load(f)
        CONFIG.update(file_config)
load_config()

if __name__ == "__main__":
    if '--generate_default' in sys.argv:
        generate_default()
