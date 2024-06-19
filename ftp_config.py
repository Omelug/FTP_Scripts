import json
import os

folder_path = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "ftp_hub": {
        "output_folder": f"{folder_path}/output/",
        "input_folder": f"{folder_path}/input/",
        "ranges": f"./ranges.txt",
        "old_delay_days": 7,
        "color_output": True
    },
    "ftp_forest": {
        "save_trees": True,
        "connect_timeout": 5,
        "forest_timeout": 30,
        "max_workers": 150
    },
    "ftp_db": {
        "db_path": f"{folder_path}/ftp_hub.db"
    }
}
global CONFIG


def load_config(config_file="config.json"):
    global CONFIG
    CONFIG = DEFAULT_CONFIG.copy()
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            file_config = json.load(f)
        CONFIG.update(file_config)

load_config()

if __name__ == "__main__":
    load_config()
