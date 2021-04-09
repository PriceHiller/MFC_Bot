import json
import aiofiles


class Config:

    def __init__(self, config_path):
        self.config_path = config_path
        self.config_dict = json.loads(open(config_path).read())
        self.prefix = self.config_dict["MFC-Guild"]["Prefix"]

    async def write(self, new_data: dict):
        async with aiofiles.open(self.config_path, "w+", encoding="UTF-8") as f:
            await f.write(json.dumps(new_data, indent=4, ensure_ascii=False, allow_nan=True))

    async def read(self) -> dict:
        async with aiofiles.open(self.config_path, encoding="UTF-8") as f:
            return json.loads(await f.read())
