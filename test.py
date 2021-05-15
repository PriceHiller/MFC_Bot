stats = {
    'baa8217e-d779-4ebf-8e23-b50af4ed2a93': {'score': 6962, 'kills': 52, 'assists': 42, 'deaths': 42, 'kda-r': 2.24,
                                             'kd': 1.24},
    '42f44003-9c4e-4603-99c3-74718e9d0cea': {'score': 8670, 'kills': 56, 'assists': 76, 'deaths': 46, 'kda-r': 2.87,
                                             'kd': 1.22},
    '4ed7ed5e-3a31-4a7b-a3b5-64ac4f46b108': {'score': 8468, 'kills': 76, 'assists': 40, 'deaths': 24, 'kda-r': 4.83,
                                             'kd': 3.17},
    '0128b790-795e-4bb6-a70b-ef9c4e0ba47b': {'score': 8366, 'kills': 72, 'assists': 30, 'deaths': 24, 'kda-r': 4.25,
                                             'kd': 3.0},
    '61a1c7f3-aec1-416b-a9a5-452e94eb2300': {'score': 8776, 'kills': 72, 'assists': 48, 'deaths': 42, 'kda-r': 2.86,
                                             'kd': 1.71},
    'a80656e3-377b-4358-a3e4-1af364ceea96': {'score': 0, 'kills': 0, 'assists': 0, 'deaths': 4, 'kda-r': 0.0,
                                             'kd': 0.0},
    '9c61b425-62ae-4686-960b-761bb3d6b07a': {'score': 276, 'kills': 2, 'assists': 2, 'deaths': 4, 'kda-r': 1.0,
                                             'kd': 0.5},
    '7b908593-975f-4d8b-b5ac-3dc0e3f49133': {'score': 200, 'kills': 2, 'assists': 0, 'deaths': 4, 'kda-r': 0.5,
                                             'kd': 0.5}}


key_name = "kd"
for player_api_data in reversed(sorted(stats.items(), key=lambda stat: stat[1][key_name])):
    api_id = player_api_data[1]
    data = player_api_data[-1]
    print(data)