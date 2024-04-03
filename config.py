discord_webhook = "" #example: "https://discord.com/api/webhooks/1064946556407658/jytEe1xy8mJj8JXuGK8L2voxMn6AlzOTsTBX8wk_Y2NoeM78CCcs0ykFmDSHcLh73NeD"
bot_token = "" #needed for the bot to be queried from within the channel
role_id = ""  #example : if it is a role, "<@&12345641267>" (mind the <@&>)
            # If it's a user, "<@123456789789>" -- only with <@>
            #Multiple roles or users can be specified. Must be separated with space, not a comma.

monitored_chains = {'elystestnet-1': []} #The value is a list of monitored connections, e.g. ["connection-0", "connection-6"].
                                         # If the value is blank, all connections will be scanned. Otherwise, only the specified connections.


#rest servers for all monitored chains AND the counterpart clients must be specified here.

#while possible to get the exponent and main denom from the API, it's also a freaking pain in the neck. Much faster to hardcode here.

chain_data = [
{'chain_id': 'injective-888', 'api': 'https://injective-testnet-api.polkachu.com', 'chain_name': 'INJECTIVE', 'wallets': [], 'exponent': 18, 'denom': 'inj', 'full_denom': 'INJ'},
{'chain_id': 'elystestnet-1', 'api':'https://api.testnet.elys.network', 'chain_name': 'ELYS', 'wallets': ['elys1ef5h93s07zm7qsdgexc6dh86vyyx9scty055jr','elys129stf3ctn47dm34nlhr9e3vqmnn8ayur7grkz9','elys1q6r94x5cmgapcetvuswuv9405gy6zcmgtedl9t'], 'exponent': 6, 'denom': 'uelys', 'full_denom': 'ELYS'},
{'chain_id': 'axelar-testnet-lisbon-3', 'api': 'https://lcd-axelar-testnet.imperator.co', 'chain_name': 'AXELAR', 'wallets': [], 'exponent': 6, 'denom': 'uaxl', 'full_denom': 'AXL'},
{'chain_id': 'theta-testnet-001', 'api': 'https://rest.sentry-01.theta-testnet.polypore.xyz', 'chain_name': 'COSMOS', 'wallets': ['cosmos1h2x8gz67c67hsav4vt7hplacqd2xjk3qzz39dl'], 'exponent': 6, 'denom': 'uatom', 'full_denom': 'ATOM'},
{'chain_id': 'evmos_9000-4', 'api': 'https://evmos-testnet-api.polkachu.com', 'chain_name': 'EVMOS', 'wallets': [], 'exponent': 18, 'denom': 'aevmos', 'full_denom': 'EVMOS'},
{'chain_id': 'uni-6', 'api': 'https://juno-testnet-api.polkachu.com', 'chain_name': 'JUNO', 'wallets': [], 'exponent': 6, 'denom': 'ujuno', 'full_denom': 'JUNO'},
{'chain_id': 'grand-1', 'api': 'https://noble-testnet-api.polkachu.com', 'chain_name': 'NOBLE', 'wallets': [], 'exponent': 6, 'full_denom': 'NOBLE'},
{'chain_id': 'sandbox-01', 'api': 'https://api.sandbox-01.aksh.pw', 'chain_name': 'AKASH', 'wallets': [], 'exponent': 6, 'denom': 'uakt', 'full_denom': 'AKT'},
{'chain_id': 'mocha-4', 'api': 'https://api-mocha.pops.one', 'chain_name': 'CELESTIA', 'wallets': [], 'exponent': 6, 'denom': 'utia', 'full_denom': 'TIA'},
{'chain_id': 'osmo-test-5', 'api': 'https://lcd.osmotest5.osmosis.zone', 'chain_name': 'OSMOSIS', 'wallets': [], 'exponent': 6, 'denom': 'uosmos', 'full_denom': 'OSMO'},
{'chain_id': 'dydx-testnet-4', 'api': 'https://dydx-testnet-api.polkachu.com', 'chain_name': 'DYDX', 'wallets': [], 'exponent': 18, 'denom': 'adydx', 'full_denom': 'DYDX'},
{'chain_id': 'constantine-3', 'api': 'https://archway-testnet-rpc.polkachu.com', 'chain_name': 'ARCHWAY', 'wallets': [], 'exponent': 18, 'denom': 'const', 'full_denom': 'CONST'},
{'chain_id': 'blumbus_111-1', 'api': 'https://blumbus.api.silknodes.io', 'chain_name': 'DYMENSION_BLUMBUS', 'wallets': ['dym1xp0epknkzj5nf0w0l6r3y3txy2e6z0mnfzetw4','dym1amsjnqptaejqzzxw04scn4x0xlthrmxnrjvfpt'], 'exponent': 18, 'denom': 'adym', 'full_denom': 'DYM'},
{'chain_id': 'froopyland_100-1', 'api': 'https://dymension-testnet-api.polkachu.com', 'chain_name': 'DYMENSION_FROOPYLAND', 'wallets': [], 'exponent': 18, 'denom': 'adym', 'full_denom': 'DYM'},
{'chain_id': 'dorado-1', 'api': 'https://rest-dorado.fetch.ai', 'chain_name': 'FETCHAI', 'wallets': [], 'exponent': 18, 'denom': 'afet', 'full_denom': 'FET'},
{'chain_id': 'stride-testnet-1', 'api': 'https://stride-testnet-api.polkachu.com', 'chain_name': 'STRIDE', 'wallets': [], 'exponent': 6, 'denom': 'ustrd', 'full_denom': 'STRD'},
{'chain_id': 'narwhal-2', 'api': 'https://migaloo-testnet-rpc.polkachu.com', 'chain_name': 'MIGALOO', 'wallets': [], 'exponent': 6, 'denom': 'uwhale', 'full_denom': 'WHALE'},
{'chain_id': 'babajaga-1', 'api': 'https://lcd-testnet.c4e.io', 'chain_name': 'C4E', 'wallets': [], 'exponent': 6, 'denom': 'uc4e', 'full_denom': 'C4E'},
{'chain_id': 'kava_2221-16000', 'api': 'https://kava-testnet-api.ibs.team', 'chain_name': 'KAVA', 'wallets': [], 'exponent': 6, 'denom': 'ukava', 'full_denom': 'KAVA'}
]

expiry_alert_threshold = 0.80 #% of the trusting period under which an alert is sent. 0.5 = the client hasn't been updated for half of its trusting period

balance_alert_threshold = 0.4 #remaining balance on a wallet to trigger an alert. (arbitrary amount, might be too high for Injective for example)
