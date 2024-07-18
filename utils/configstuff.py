import json, os, time

class ConfigHandler:
    def __init__(self, server_id):
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', f'{server_id}.json')
        self.config = self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            return {}
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_config(self, new_config):
        self.config.update(new_config)
        self.save_config()
    
    def get_config(self):
        return self.config


def load_servers():
    with open('../guilds.json', 'r') as f:
        guilds_data = json.load(f)
    print(guilds_data)
    return guilds_data