import os
import yaml

def load_config(filepath='config/config.yaml'):
    # Construct the absolute path to the config file
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, '..', filepath)
    
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()