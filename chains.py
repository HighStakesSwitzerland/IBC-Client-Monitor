#rest servers for all monitored chains AND the counterpart clients must be specified here.

#while possible to get the exponent and main denom from the API, it's also a freaking pain in the neck. Much faster to hardcode here.

chain_data = [
{'chain_id': 'injective-888', 'api': 'https://injective-testnet-api.polkachu.com', 'chain_name': 'INJECTIVE', 'exponent': 18, 'denom': 'inj', 'full_denom': 'INJ'},
{'chain_id': 'elystestnet-1', 'api':'https://api.testnet.elys.network', 'chain_name': 'ELYS', 'exponent': 6, 'denom': 'uelys', 'full_denom': 'ELYS'},
{'chain_id': 'axelar-testnet-lisbon-3', 'api': 'https://lcd-axelar-testnet.imperator.co', 'chain_name': 'AXELAR', 'exponent': 6, 'denom': 'uaxl', 'full_denom': 'AXL'},
{'chain_id': 'theta-testnet-001', 'api': 'https://rest.sentry-01.theta-testnet.polypore.xyz', 'chain_name': 'COSMOS', 'exponent': 6, 'denom': 'uatom', 'full_denom': 'ATOM'},
{'chain_id': 'evmos_9000-4', 'api': 'https://evmos-testnet-api.polkachu.com', 'chain_name': 'EVMOS', 'exponent': 18, 'denom': 'aevmos', 'full_denom': 'EVMOS'},
{'chain_id': 'uni-6', 'api': 'https://juno-testnet-api.polkachu.com', 'chain_name': 'JUNO', 'exponent': 6, 'denom': 'ujuno', 'full_denom': 'JUNO'},
{'chain_id': 'grand-1', 'api': 'https://noble-testnet-api.polkachu.com', 'chain_name': 'NOBLE', 'exponent': 6, 'full_denom': 'NOBLE'},
{'chain_id': 'sandbox-01', 'api': 'https://api.sandbox-01.aksh.pw', 'chain_name': 'AKASH', 'exponent': 6, 'denom': 'uakt', 'full_denom': 'AKT'},
{'chain_id': 'mocha-4', 'api': 'https://api-mocha.pops.one', 'chain_name': 'CELESTIA', 'exponent': 6, 'denom': 'utia', 'full_denom': 'TIA'},
{'chain_id': 'osmo-test-5', 'api': 'https://lcd.osmotest5.osmosis.zone', 'chain_name': 'OSMOSIS', 'exponent': 6, 'denom': 'uosmos', 'full_denom': 'OSMO'},
{'chain_id': 'dydx-testnet-4', 'api': 'https://dydx-testnet-api.polkachu.com', 'chain_name': 'DYDX', 'exponent': 18, 'denom': 'adydx', 'full_denom': 'DYDX'},
{'chain_id': 'constantine-3', 'api': 'https://archway-testnet-api.polkachu.com', 'chain_name': 'ARCHWAY', 'exponent': 18, 'denom': 'const', 'full_denom': 'CONST'},
{'chain_id': 'blumbus_111-1', 'api': 'https://dymension-api-blumbus.ibs.team', 'chain_name': 'DYMENSION_BLUMBUS', 'exponent': 18, 'denom': 'adym', 'full_denom': 'DYM'},
{'chain_id': 'froopyland_100-1', 'api': 'https://dymension-testnet-api.polkachu.com', 'chain_name': 'DYMENSION_FROOPYLAND', 'exponent': 18, 'denom': 'adym', 'full_denom': 'DYM'},
{'chain_id': 'dorado-1', 'api': 'https://rest-dorado.fetch.ai', 'chain_name': 'FETCHAI', 'exponent': 18, 'denom': 'atestfet', 'full_denom': 'TESTFET'},
{'chain_id': 'stride-testnet-1', 'api': 'https://stride-testnet-api.polkachu.com', 'chain_name': 'STRIDE', 'exponent': 6, 'denom': 'ustrd', 'full_denom': 'STRD'},
{'chain_id': 'narwhal-2', 'api': 'https://migaloo-testnet-api.polkachu.com', 'chain_name': 'MIGALOO', 'exponent': 6, 'denom': 'uwhale', 'full_denom': 'WHALE'},
{'chain_id': 'babajaga-1', 'api': 'https://lcd-testnet.c4e.io', 'chain_name': 'C4E', 'exponent': 6, 'denom': 'uc4e', 'full_denom': 'C4E'},
{'chain_id': 'kava_2221-16000', 'api': 'https://kava-testnet-api.ibs.team', 'chain_name': 'KAVA', 'exponent': 6, 'denom': 'ukava', 'full_denom': 'KAVA'},
{'chain_id': 'test-core-2', 'api': 'https://persistence-testnet-api.polkachu.com', 'chain_name': 'PERSISTENCE', 'exponent': 6, 'denom': 'uxprt', 'full_denom': 'XPRT'},
{'chain_id': 'elgafar-1', 'api': 'https://stargaze-testnet-api.ibs.team', 'chain_name': 'STARGAZE', 'exponent': 6, 'denom': 'ustars', 'full_denom': 'STARS'}
]
