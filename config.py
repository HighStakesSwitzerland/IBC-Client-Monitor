discord_webhook = "" #example: "https://discord.com/api/webhooks/1064946556407658/jytEe1xy8mJj8JXuGK8L2voxMn6AlzOTsTBX8wk_Y2NoeM78CCcs0ykFmDSHcLh73NeD"
role_id = ""  #example : if it is a role, "<@&12345641267>" (mind the <@&>)
            # If it's a user, "<@123456789789>" -- only with <@>
            #Multiple roles or users can be specified. Must be separated with space, not a comma.

monitored_chains = {'elystestnet-1': []} #The value is a list of monitored connections, e.g. ["connection-0", "connection-6"].
                                         # If the value is blank, all connections will be scanned. Otherwise, only the specified connections.


#rest servers for all monitored chains AND the counterpart clients must be specified here.

rest_servers = [
        {'chain_id': 'elystestnet-1', 'api':'https://api.testnet.elys.network'},
        {'chain_id': 'axelar-testnet-lisbon-3', 'api': 'https://lcd-axelar-testnet.imperator.co/'},
        {'chain_id': 'theta-testnet-001', 'api': 'https://rest.sentry-01.theta-testnet.polypore.xyz'},
        {'chain_id': 'evmos_9000-4', 'api': 'https://evmos-testnet-api.polkachu.com'},
        {'chain_id': 'uni-6', 'api': 'https://juno-testnet-api.polkachu.com'},
        {'chain_id': 'grand-1', 'api': 'https://noble-testnet-api.polkachu.com'},
        {'chain_id': 'sandbox-01', 'api': 'https://api.sandbox-01.aksh.pw'},
        {'chain_id': 'osmo-test-5', 'api': 'https://lcd.osmotest5.osmosis.zone'}
        ]
