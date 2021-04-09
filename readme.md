# Todo

- [ ] Convert all JSON models within config.json to a pydantic schema

# MFC Discord Bot

## Running the bot

Ensure you have seen **Configuration**. 

Once all required settings are configured run the bot via: `python -m bot`


## Configuration

All config values are passed via environment variables. See **Environment Variables**.

It is recommended to define a `.env` file in the `bot` directory with the bot token argument:
```ini
discord_bot_token="someDiscordBotToken"
```

A requirements file is included to install all dependencies, to do so execute:

```bash
python -m pip install -r requirements.txt
```


## Logging

For logging to work you *must* define a `log_config.yaml` file within the `bot` directory based on the the python
logging [dictConfig](https://docs.python.org/3/library/logging.config.html#dictionary-schema-details) *or* set the 
appropriate log path in your environment, see **Environment Variables**. 

Within your own `log_config.yaml`, assuming you don't use the default, ensure you set `disable_existing_loggers` to
**false**, otherwise the log messages emitted by [discord.py](https://discordpy.readthedocs.io/en/latest/index.html)
will not be logged.

An example config in yaml, and the one that ships by default:

```yaml
version: 1
disable_existing_loggers: false # Important, otherwise the discord.py logs will not be logged. Keep this as false
formatters:
    standard:
        format: '[%(asctime)s][%(threadName)s][%(name)s.%(funcName)s:%(lineno)d][%(levelname)s] %(message)s'
handlers:
    default_stream_handler:
        class: logging.StreamHandler
        formatter: standard
        level: INFO
        stream: ext://sys.stdout
    default_file_handler:
        backupCount: 5
        class: logging.handlers.RotatingFileHandler
        filename: Bot.log
        formatter: standard
        level: DEBUG
    error_file_handler:
        backupCount: 5
        class: logging.handlers.RotatingFileHandler
        delay: true
        filename: bot_error.log
        formatter: standard
        level: ERROR
loggers:
    '': # The root logger, best to leave it undefined (don't enter a string)
        handlers:
            - default_stream_handler
            - default_file_handler
            - error_file_handler
        level: DEBUG
        propagate: false
```


## Environment Variables

It is highly encouraged that a `.env` file is defined in the `bot` directory with your variables. If you do not do this,
you will need to export all of your variables into your local environment *before* running the bot.


### Discord Bot

All discord bot environment variables are preceded by `discord_bot_`

| Variable Name      | Example Value                                                | Description 
| :---               | :---                                                         | :---        
| discord_bot_token  | Nzk3MDk0MTY2MjA2NzQyNTI5.P_2ajsp.clF0tD4CA0Nb-_MConBS9KVPsrE | Your discord bot's token, found at the [discord developer portal](https://discord.com/developers/applications)
| discord_bot_prefix | !                                                            | The prefix used to invoke bot commands, e.g. `!help`

### API

All api environment variables are preceded by `api_`

| Variable Name | Example Value  | Description
| :---          | :---           | :---
| api_url       | 127.0.0.1:5000 | The HTTP(S) url of the MFC API
| api_token     | wd23sawWAsjdae | The login (authorization) jwt token granted by the api


### Logging

All logging environment variables are preceded by `log_`

| Variable Name   | Example Value                           | Description
| :---            | :---                                    | :---
| log_config_path | /Users/user/MFC_Bot/bot/log_config.yaml | The path (including the name of the file) of your log config.
