import json

class Config:

    def __init__(self, config_path):
        self.config_dict = json.loads(open(config_path).read())
        self.prefix = self.config_dict["MFC-Guild"]["Prefix"]
