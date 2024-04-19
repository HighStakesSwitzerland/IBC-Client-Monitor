import asyncio
from os import path
from pprint import pformat
from syslog import LOG_INFO, LOG_WARNING
from threading import Thread
from time import sleep
from requests import get
from requests.exceptions import ReadTimeout
from datetime import datetime, timezone
from urllib.parse import quote
from discord import Intents
from discord.ext import commands


from config import *
from chains import *
from discord_message import *
try:
    from tracked_wallets import tracked_wallets
except: #file doesn't exist or whatever issue: start with a fresh dict.
    tracked_wallets = {}

local_directory = path.dirname(path.abspath(__file__)) #seems needed on the production server, otherwise the tracked_wallets file is created under /



class ClientMonitorAll:

    def __init__(self):

        self.ibc_data = {}
        self.wallet_balances = {}
        self.update_time_data = None
        self.update_time_wallets = None

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(self.update_ibc_data())
        loop.run_forever()

    async def update_ibc_data(self):

        while True:
            self.check_wallet_balances()

            for chain_id in monitored_chains:
                #get the client ids + their counterpart chain and client
                ibc_data = self.get_ibc_data(chain_id, connections=monitored_chains[chain_id])

                #next, check the status of each client. If it's active, check the last update and trusting period.

                self.update_time_data = datetime.now(timezone.utc).timestamp() #current time to calculate how long ago the client was updated.

                for i in ibc_data:
                    revision_height, trusting_period, chain_name = self.check_client(chain_id, i['client_id'])
                    #the above will be None if the client is expired. No alert in this instance.
                    if revision_height:
                        self.check_client_update_status(revision_height, trusting_period,
                                                        self.update_time_data, chain_id, i['counterparty']['chain_id'], i['client_id'], i['chain_name'])
                        #and check the counterpart client
                        #IMPORTANT: the "chain_id" and  "i['counterparty']['client_id']" are inverted here.
                        revision_height, trusting_period, chain_name = self.check_client(i['counterparty']['chain_id'], i['counterparty']['client_id'])
                        if revision_height:
                            self.check_client_update_status(revision_height, trusting_period,
                                                            self.update_time_data, i['counterparty']['chain_id'], chain_id,  i['counterparty']['client_id'], chain_name)

            await asyncio.sleep(update_frequency*3600)

    def get_ibc_data(self, chain_id, connections=None):

        key = ""
        ibc_data = []
        rest_server = [j['api'] for j in chain_data if j['chain_id'] == chain_id][0]

        if not connections: #no connections specified = scan them all

            while True:
                try:
                    query = f"{rest_server}/ibc/core/connection/v1/connections?pagination.key={quote(key)}"
                    data = get(query, timeout=2).json()

                    pagination_total = int(data['pagination']['total']) if data['pagination']['total'] else 0
                    if pagination_total > 100:
                        discord_message(title="Configuration issue",
                    description=f"There are {pagination_total} IBC connections to go through. Aborting as this will likely fail.\nPlease define specific connections to monitor instead.",
                                        color=16515843)
                        break
                except Exception as e:
                    syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/connection/v1/connections?pagination.key={quote(key)}")
                    syslog(LOG_ERR, f"IBC: error in 'get_ibc_data': {rest_server}, {chain_id}: {str(e)}")
                    break

                for i in data['connections']:
                    try:
                        client_data = get(f"{rest_server}/ibc/core/client/v1/client_states/{i['client_id']}", timeout=2).json()
                        i['counterparty']['chain_id'] = client_data['client_state']['chain_id']
                        i['chain_name'] = [j['chain_name'] for j in chain_data if j['chain_id'] == client_data['client_state']['chain_id']][0]
                        ibc_data.append(i)
                    except Exception as e:
                        #typically a KeyError, getting something like "'id': 'connection-localhost', 'client_id': '09-localhost'"
                        #but could be a rest server not responding.
                        #print(f"IBC: error in 'get_ibc_data': {chain_id}: {str(e)}")
                        syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/client/v1/client_states/{i['client_id']}")
                        syslog(LOG_ERR, f"IBC: error in 'get_ibc_data': {chain_id}: {str(e)}")
                        pass

                key = data['pagination']['next_key']

                if not key:
                    break

                sleep(2)  # if using a public rest server, might be best to throttle down the queries

        else:
            for connection in connections:
                try:
                    data = get(f"{rest_server}/ibc/core/connection/v1/connections/{connection}", timeout=2).json()['connection']
                    data['id'] = connection
                    ibc_data.append(data)
                except Exception as e:
                    #print(f"IBC: Failed to check connection: {chain_id}, {connection}: {str(e)}")
                    syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/connection/v1/connections/{connection}")
                    syslog(LOG_ERR, f"IBC: Failed to check connection: {chain_id}, {connection}: {str(e)}")

        return ibc_data

    def check_client(self, chain_id, client_id):
        #check the client on the chain id
        revision_height = None
        trusting_period = None
        chain_name = None
        rest_server = None
        try:
            rest_server = [j['api'] for j in chain_data if j['chain_id'] == chain_id][0]
            #check the status:
            #print(f"{rest_server}/ibc/core/client/v1/client_status/{client_id}")
            status = get(f"{rest_server}/ibc/core/client/v1/client_status/{client_id}").json()['status']
            state = get(f"{rest_server}/ibc/core/client/v1/client_states/{client_id}").json()['client_state']
            if status == 'Active':
                #state = get(f"{rest_server}/ibc/core/client/v1/client_states/{client_id}").json()['client_state']
                revision_height = state['latest_height']['revision_height']
                trusting_period = int(state['trusting_period'][:-1]) #returns something like 518400s: drop the 's' and interpret as int
                chain_name = [j['chain_name'] for j in chain_data if j['chain_id'] == state['chain_id']][0]

            else:
                syslog(LOG_WARNING, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id} {chain_id}, {state['chain_id']}: {status}")

        except IndexError:
            syslog(LOG_ERR, f"IBC: no rest server configured for {chain_id}")

        except Exception as e:
            #print(f"IBC: Error retrieving data for {chain_id}, {client_id}: {str(e)}")
            syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id}")
            syslog(LOG_ERR, f"IBC: Error retrieving data for {chain_id}, {client_id}: {str(e)}")

        return revision_height, trusting_period, chain_name

    def check_client_update_status(self, revision_height, trusting_period, update_time_data, chain_id, counterpart_chain_id, client_id, chain_name):
        rest_server = None
        try:
            rest_server = [j['api'] for j in chain_data if j['chain_id'] == counterpart_chain_id][0]
            data = get(f"{rest_server}/cosmos/base/tendermint/v1beta1/blocks/{revision_height}").json()['block']['header']['time']
            revision_height_timestamp = datetime.timestamp(datetime.fromisoformat(data.split('.')[0]))

            # compare both timestamps
            delta = update_time_data - revision_height_timestamp

            syslog(LOG_INFO, f"IBC: {client_id} {round((trusting_period-delta)/3600, 2)} hours left")

            # if the revision height happened earlier than XX% of the trusting period, send out a Discord alert.
            if delta > trusting_period * expiry_alert_threshold and trusting_period-delta < 172800:  #alert only when less than 48h remain, otherwise it can be annoying as some bonding periods are long and 80% leaves several days.
                discord_message(title="WARNING - IBC Client Expiration",
                                     description=f"""Client **{client_id}** on {chain_name} (**{chain_id}**, **{counterpart_chain_id}**) will expire in ~{round((trusting_period-delta)/3600, 2)} hours)""", color=16776960,
                                     tag=role_id)

            self.ibc_data[f'{client_id}'] = {'chain_id': chain_id, 'counterpart_chain_id': counterpart_chain_id, 'time_to_expiry': round((trusting_period-delta)/3600, 2), 'chain_name': chain_name}

        except IndexError:
            syslog(LOG_ERR, f"IBC: no rest server configured for {counterpart_chain_id}")

        except Exception as e:
            #print(f"IBC: Error check client update status {client_id} on {chain_id}: {str(e)}")
            syslog(LOG_ERR, f"IBC: {rest_server}/cosmos/base/tendermint/v1beta1/blocks/{revision_height}")
            syslog(LOG_ERR, f"IBC: Error in check_client_update_status {client_id} on {chain_id}, {counterpart_chain_id}: {str(e)}")



    def check_wallet_balances(self):
        
        #check the registered wallet balances and add to a dict that can be queried from Discord
        #if a balance is less than "balance_alert_threshold" tokens as defined in config.py, send an alert
        self.update_time_wallets = datetime.now(timezone.utc).timestamp()
        for wallet in tracked_wallets:
            chain_id = tracked_wallets[wallet][0]
            user = tracked_wallets[wallet][1]
            alert_threshold = tracked_wallets[wallet][2]
            data = [chain for chain in chain_data if chain['chain_id'] == chain_id][0]

            try:
                balance = get(f"{data['api']}/cosmos/bank/v1beta1/balances/{wallet}/by_denom?denom={data['denom']}", timeout=3).json()['balance']['amount']
                balance = round(int(balance)/10**data['exponent'], 3)
                if balance < alert_threshold:
                    discord_message(title="LOW BALANCE", description=f"Wallet {wallet} has {balance} {data['full_denom']} left.", color=16752640, tag=user)

                self.wallet_balances[wallet] = [data['chain_name'], str(balance) + ' ' + data['full_denom']]

            except Exception as e:
                syslog(LOG_ERR, f"IBC: Error in check_wallet_balance for {wallet} on {data['chain_name']}: {str(e)}")



ClientMonitorAll = ClientMonitorAll()
Thread(target=ClientMonitorAll.start).start()

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command(name="data")
async def input(message):

    """Displays the list of currently tracked IBC client and their last known status. No arguments."""

    data = ClientMonitorAll.ibc_data
    try:
        last_update = datetime.fromtimestamp(ClientMonitorAll.update_time_data).strftime('%Y-%m-%d %H:%M')
    except: #bot just started, no timestamp yet
        last_update = "N/A"

    title="IBC clients status"
    description = f"Last updated:**{last_update} UTC**\n\n"
    for key in data:
        description += f"**{data[key]['chain_name']}**\n**{key}**:\n🔗'chain_id': **{data[key]['chain_id']}**\n🔗'counterpart_chain_id': **{data[key]['counterpart_chain_id']}**\n⏳'time_to_expiry': **{str(data[key]['time_to_expiry'])+' hours ⚠️' if data[key]['time_to_expiry'] < 50 else str(data[key]['time_to_expiry'])+' hours ✅'}**\n\n"
    embed = Embed(title=title, description=description[:(4095 - len(title))])

    await message.channel.send(embed=embed)

@bot.command(name="wallets")
async def input(message):

    """Displays the list of currently tracked wallets and their last known balance. No arguments."""

    data = ClientMonitorAll.wallet_balances
    try:
        last_update = datetime.fromtimestamp(ClientMonitorAll.update_time_wallets).strftime('%Y-%m-%d %H:%M')
    except: #bot just started, no timestamp yet
        last_update = "N/A"

    title="IBC wallets balances"
    description = f"Last updated:**{last_update} UTC**\n\n"
    for key in data:
        description += f"🔗**{data[key][0]}\n{key}**\n\nBalance: **{data[key][1]+' ⚠️' if float(data[key][1].split()[0]) < 2 else data[key][1]+' ✅'}**\n\n"
    embed = Embed(title=title, description=description[:(4095 - len(title))])

    await message.channel.send(embed=embed)


@bot.command(name="register")
async def input(message):
    """register an IBC wallet to get balance alerts.\n\nUsage: $register wallet chain_id alert_threshold\n\n
alert_threshold = remaining balance on wallet before alerting, in tokens.\n\n
e.g. $register inj1qdqwdsf4wxfcv654qsdfqsdqc5 injective-888 0.5 --> will alert when balance on wallet falls below 0.5 INJ"""

    user_id = message.message.author.id
    #parse the message
    try:
        wallet = message.message.content.split()[1]
        chain_id = message.message.content.split()[2]
        alert_threshold = float(message.message.content.split()[3])
    except Exception as e: #whatever the exception
        syslog(LOG_ERR, f"IBC: failed to track wallet: {message.message.content}: {e}")
        discord_message(title="", description="""Unable to process input.\n\nUsage: $register wallet chain_id alert_threshold\n\n
                        alert_threshold = remaining balance on wallet before alerting, in tokens.\n\n
                        e.g. **$register inj1qdqwdsf4wxfcv654qsdfqsdqc5 injective-888 0.5** --> will alert when balance on wallet falls below 0.5 INJ""",
                        color=16776960, tag=f"<@{user_id}>")
        return

    data = [chain for chain in chain_data if chain['chain_id'] == chain_id]
    if not data:
        discord_message(title="", description="Chain not found.\n\nThis chain isn't tracked or the chain id does not exist.",
                        color=16776960, tag=f"<@{user_id}>")
        return

    #Check that wallet exist
    try:
        balance = get(f"{data[0]['api']}/cosmos/bank/v1beta1/balances/{wallet}/by_denom?denom={data[0]['denom']}", timeout=3).json()['balance']['amount']
        balance = round(int(balance)/10**data[0]['exponent'], 3)

    except ReadTimeout:
        discord_message(title="",
                        description=f"{data[0]['denom']} REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, please inform an administrator ",
                        color=16776960, tag=f"<@{user_id}>")
        return
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to track wallet: {message.message.content}: {e}")
        discord_message(title="",
                        description=f"Couldn't check wallet.\n\nPlease ensure that the address is valid.",
                        color=16776960, tag=f"<@{user_id}>")
        return

    #insert the wallet / chain / user in the tracked_wallets dict
    tracked_wallets[wallet] = [chain_id, f"<@{user_id}>", alert_threshold]

    try:
        with open(path.join(local_directory, "tracked_wallets.py"), "w") as f:
            f.write(f"tracked_wallets = {str(pformat(tracked_wallets))}")

        ClientMonitorAll.wallet_balances[wallet] = [data[0]['chain_name'], str(balance) + ' ' + data[0]['full_denom']]
        discord_message(title="",
                    description=f"Tracking wallet **{wallet}** with alert threshold **{alert_threshold} {data[0]['full_denom']}**.\n\nCurrent balance is {balance} {data[0]['full_denom']}",
                    color=2161667, tag=f"<@{user_id}>")
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to track wallet: {message.message.content}: {e}")
        discord_message(title="",
                        description=f"Failed to track wallet.\nError was logged, please inform an administrator.",
                        color=16515843, tag=f"<@{user_id}>")

@bot.command(name="deregister")
async def input(message):

    """Disabling balance alerts for a previously registered wallet.\n\nUsage: $deregister wallet\n\n
Only the user that set up the alerts can disable them. Contact an administrator if this user is unreachable."""

    user_id = str(message.message.author.id)
    #parse the message
    try:
        wallet = message.message.content.split()[1]
        if wallet in [key for key in tracked_wallets]:
            if user_id in tracked_wallets[wallet][1]:
                del tracked_wallets[wallet]
                with open(path.join(local_directory, "tracked_wallets.py"), "w") as f:
                    f.write(f"tracked_wallets = {str(pformat(tracked_wallets))}")
                del ClientMonitorAll.wallet_balances[wallet]
                discord_message(title="",
                                description=f"Disabled tracking for wallet **{wallet}**.",
                                color=16752640, tag=f"<@{user_id}>")

            else:
                discord_message(title="",
                                description=f"Only the original user {tracked_wallets[wallet][1]} can deregister his wallet.\n\nContact an administrator if this user is unreachable.",
                                color=16711680, tag=f"<@{user_id}>")
        else:
            discord_message(title="",
                            description=f"Wallet **{wallet}** isn't registered.",
                            color=16711935, tag=f"<@{user_id}>")

    except Exception as e: #whatever the exception
        syslog(LOG_ERR, f"IBC: failed to deregister wallet: {message.message.content}: {e}")
        discord_message(title="", description="Unable to process input.\n\nUsage: $deregister wallet\n\n", color=16776960, tag=f"<@{user_id}>")
        return

@bot.command(name="my_wallets")
async def input(message):
    """Returns the current balance of all wallets registered to the user\n\nUsage: $my_wallets."""
    user_id = message.message.author.id
    user_wallets = [[wallet, tracked_wallets[wallet]] for wallet in tracked_wallets if str(user_id) in tracked_wallets[wallet][1]]

    if len(user_wallets) == 0:
        discord_message(title="", description="""No tracked wallets.\n\nUse the `@register` command to add them.""",
                        color=16776960, tag=f"<@{user_id}>")
        return

    description = ""
    for wallet_data in user_wallets:
        data = [chain for chain in chain_data if chain['chain_id'] == wallet_data[1][0]]
        try:
            balance = get(f"{data[0]['api']}/cosmos/bank/v1beta1/balances/{wallet_data[0]}/by_denom?denom={data[0]['denom']}",
                          timeout=3).json()['balance']['amount']
            balance = round(int(balance) / 10 ** data[0]['exponent'], 3)
            ClientMonitorAll.wallet_balances[wallet_data[0]] = [data[0]['chain_name'],
                                                        str(balance) + ' ' + data[0]['full_denom']]
            description += f"**{wallet_data[0]}**: {str(balance)} {data[0]['full_denom']}\n\n"

        except Exception as e:
            syslog(LOG_ERR, f"IBC: failed to track wallet: {message.message.content}: {e}")
            description += f"**{wallet_data[0]}**: failed to check balance. Please try again later.\n\n"

    discord_message(title="",
                    description=description,
                    color=2161667, tag=f"<@{user_id}>")


@bot.command(name="wallet")
async def input(message):
    """Returns the current balance of a registered wallet\n\nUsage: $wallet <wallet_address>\n\nWill return an error if the wallet isn't currently tracked."""

    user_id = message.message.author.id
    #parse the message
    try:
        wallet = message.message.content.split()[1]

    except Exception as e: #whatever the exception
        syslog(LOG_ERR, f"IBC: failed to check wallet: {message.message.content}: {e}")
        discord_message(title="", description="""Unable to process input.\n\nUsage: $wallet <wallet>\n\n
                        Will return the current balance of the wallet.""",
                        color=16776960, tag=f"<@{user_id}>")
        return

    try:
        wallet_data = tracked_wallets[wallet]
        data = [chain for chain in chain_data if chain['chain_id'] == wallet_data[0]]
        if not data:
            raise Exception
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to check wallet: {message.message.content}: {e}")
        discord_message(title="", description="Wallet not found.\n\nThis wallet isn't tracked.",
                            color=16776960, tag=f"<@{user_id}>")
        return

    #Check balance
    try:
        balance = get(f"{data[0]['api']}/cosmos/bank/v1beta1/balances/{wallet}/by_denom?denom={data[0]['denom']}", timeout=3).json()['balance']['amount']
        balance = round(int(balance)/10**data[0]['exponent'], 3)

    except ReadTimeout:
        discord_message(title="",
                        description=f"{data[0]['denom']} REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, please inform an administrator ",
                        color=16776960, tag=f"<@{user_id}>")
        return
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to track wallet: {message.message.content}: {e}")
        discord_message(title="",
                        description=f"Couldn't check wallet.\n\nPlease ensure that the address is valid.",
                        color=16776960, tag=f"<@{user_id}>")
        return

    ClientMonitorAll.wallet_balances[wallet] = [data[0]['chain_name'], str(balance) + ' ' + data[0]['full_denom']]
    discord_message(title="",
                    description=f"Current balance of wallet **{wallet}** is **{balance} {data[0]['full_denom']}**",
                    color=2161667, tag=f"<@{user_id}>")

@bot.command(name="register_chain")
async def input(message):
    """Add a new chain to track IBC clients and relayer wallets.\n\nUsage: $register_chain CHAIN_NAME REST_SERVER TOKEN_NAME TOKEN_DECIMALS\n\n
e.g. $register_chain COSMOS https://rest.sentry-01.theta-testnet.polypore.xyz ATOM 6\n\n
"token_decimals" is the ratio between the token and its base denom. E.g for Cosmos, 1 ATOM = 10^6 uatom, so token_decimals is 6.\n\n
**WARNING**: there is no reliable way to verify that the decimals parameter is correct. Please ensure it is the right value, otherwise the wallet balances will be wrong.\n\n
Sometimes the denom (e.g. 'uatom') can't be retrieved with the API. If so, you can force it by specifying it at the end of the command:\n\n
$register_chain COSMOS https://rest.sentry-01.theta-testnet.polypore.xyz ATOM 6 uatom"""

    user_id = message.message.author.id
    denom = None
    #parse the message
    try:
        chain_name = message.message.content.split()[1].upper()
        rest_server = message.message.content.split()[2]
        full_denom = message.message.content.split()[3].upper()
        exponent = int(message.message.content.split()[4])
        try:
            denom = message.message.content.split()[5] #if the denom can't be queried from the API, allow forcing it
        except Exception:
            pass


    except Exception as e: #whatever the exception
        syslog(LOG_ERR, f"IBC: failed to add chain: {message.message.content}: {e}")
        discord_message(title="", description="""Unable to process input.\n\nUsage: Usage: $register_chain CHAIN_NAME REST_SERVER TOKEN_NAME TOKEN_DECIMALS\n\n
                        e.g. **$register_chain COSMOS https://rest.sentry-01.theta-testnet.polypore.xyz ATOM 6**\n\n
"token_decimals" is the ratio between the token and its base denom. E.g for Cosmos, 1 ATOM = 10^6 uatom, to token_decimals is 6.\n\n
**WARNING**: there is no reliable way to verify that the decimals parameter is correct. Please ensure it is the right value, otherwise the wallet balances will be wrong.""",
                        color=16776960, tag=f"<@{user_id}>")
        return

    #check the API server and match the data
    try:
        chain_id = get(f"{rest_server}/cosmos/base/tendermint/v1beta1/node_info", timeout=5).json()['default_node_info']['network']

        if not denom:
            try:
                denom = get(f"{rest_server}/cosmos/mint/v1beta1/params", timeout=5).json()['params']['mint_denom']
            except: #some chains have their own custom endpoint with their name instead of "cosmos"... not too reliable though.
                try:
                    denom = get(f"{rest_server}/{chain_name.lower()}/mint/v1beta1/params", timeout=5).json()['params']['mint_denom']
                except:
                    raise Exception
        #exponent = get(f"{rest_server}/cosmos/bank/v1beta1/denoms_metadata/{denom}", timeout=5).json()['params']['mint_denom'] #this value isn't always available. Best to pass it as a parameter.
        if full_denom.lower() not in denom:
            raise Exception

    except ReadTimeout:
        discord_message(title="",
                        description=f"REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, try another.",
                        color=16776960, tag=f"<@{user_id}>")
        return
    except Exception as e:
        syslog(LOG_ERR, f"IBC: wrong denom: {message.message.content}: {e}")
        discord_message(title="",
                        description="""The token name does not to match its base denom, or the chain does not use standard API endpoints. Please verify.\n\n
                        If you know this denom (e.g. 'uatom') and are confident it is correct, please pass the command again, specifiyng it at the end:\n\n
                        $register_chain COSMOS https://rest.sentry-01.theta-testnet.polypore.xyz ATOM 6 **uatom**\n\n
                        If still encountering an issue, you may contact an administrator.""",
                        color=16776960, tag=f"<@{user_id}>")
        return

    #insert the chain in the data and write it in the chain file
    for chain in chain_data:
        if chain['chain_id'] == chain_id:
            chain.update({'api': rest_server, 'chain_name': chain_name, 'exponent': exponent, 'denom': denom, 'full_denom': full_denom})
            break
    else:
        chain_data.append({'chain_id': chain_id, 'api': rest_server, 'chain_name': chain_name, 'exponent': exponent, 'denom': denom, 'full_denom': full_denom})

    try:
        with open(path.join(local_directory, "chains.py"), "w") as f:
            f.write(f"chain_data = {str(pformat(chain_data))}")

        discord_message(title="",
                    description=f"""Added chain **{chain_name}** with data:\n\nChain_id: **{chain_id}**\nDenom: **{denom}**\nToken name: **{full_denom}**\nToken decimals: **{exponent}**\n\n
If the data isn't correct, please pass the command again with the right information or contact an administrator.""",
                    color=2161667, tag=f"<@{user_id}>")
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to add chain: {message.message.content}: {e}")
        discord_message(title="",
                        description=f"Failed to add chain.\nError was logged, please inform an administrator.",
                        color=16515843, tag=f"<@{user_id}>")


bot.run(bot_token)


