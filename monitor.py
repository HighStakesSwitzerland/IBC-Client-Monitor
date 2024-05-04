import asyncio
from json import loads, dumps
from os import path
from pprint import pformat
from syslog import LOG_INFO, LOG_WARNING
from time import sleep
from requests import get
from urllib.parse import quote
from datetime import datetime, timezone

from config import *
from chains import *
from discord_message import *

try:
    from tracked_wallets import tracked_wallets
except: #file doesn't exist or whatever issue: start with a fresh dict.
    tracked_wallets = {}
try:
    from expired_clients import expired_clients #store the expired clients to avoid checking them again
except:
    expired_clients = []

local_directory = path.dirname(path.abspath(__file__)) #seems needed on the production server, otherwise the tracked_wallets file is created under /


class MonitorAll:

    def __init__(self):

        try:
            self.ibc_data = []
            with open(path.join(local_directory,"ibc_data"), "r") as f:
                for i in f.readlines():
                    self.ibc_data.append(loads(i))
        except: #no matter the exception, just start with an empty list.
            self.ibc_data = []
        self.wallet_balances = {}
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

                for i in ibc_data:
                    revision_height, trusting_period, chain_name = self.check_client(chain_id, i['client_id'], i['id'], i['counterparty']['connection_id'])
                    #the above will be None if the client is expired. No alert in this instance.
                    if revision_height:
                        self.check_client_update_status(revision_height, trusting_period,
                                                        chain_id, i['counterparty']['chain_id'], i['client_id'], i['chain_name'])
                        #and check the counterpart client
                        #IMPORTANT: the "chain_id" and  "i['counterparty']['client_id']" are inverted here.
                        revision_height, trusting_period, chain_name = self.check_client(i['counterparty']['chain_id'], i['counterparty']['client_id'], i['counterparty']['connection_id'], i['id'])
                        if revision_height:
                            self.check_client_update_status(revision_height, trusting_period,
                                                            i['counterparty']['chain_id'], chain_id,  i['counterparty']['client_id'], chain_name)

            with open(path.join(local_directory,"ibc_data"), 'w') as f: #store the client data and status with their last checked timestamp. To avoid alerting too soon upon restarting the process.
                self.ibc_data = sorted(self.ibc_data, key=lambda x: list(x.values())[0]['chain_name'])
                for i in self.ibc_data:
                    f.write(dumps(i)+'\n')

            with open(path.join(local_directory, "expired_clients.py"), 'w') as f: #store the expired clients data, so we don't check them anymore.
                f.write(f"expired_clients = {str(pformat(expired_clients))}")

            await asyncio.sleep(update_frequency*3600)

    def get_ibc_data(self, chain_id, connections=None):

        key = ""
        ibc_data = []
        rest_server = [j['api'] for j in chain_data if j['chain_id'] == chain_id][0]

        if not connections: #no connections specified = scan them all

            while True:
                try:
                    query = f"{rest_server}/ibc/core/connection/v1/connections?pagination.key={quote(key)}"
                    data = get(query, timeout=4).json()

                    pagination_total = int(data['pagination']['total']) if data['pagination']['total'] else 0
                    if pagination_total > 300:
                        discord_message(title="Configuration issue",
                    description=f"There are {pagination_total} IBC connections to go through. Aborting as this will likely fail.\nPlease define specific connections to monitor instead.",
                                        color=16515843)
                        break
                except Exception as e:
                    syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/connection/v1/connections?pagination.key={quote(key)}")
                    syslog(LOG_ERR, f"IBC: error in 'get_ibc_data': {rest_server}, {chain_id}: {str(e)}")
                    break

                for i in [i for i in data['connections'] if i['state'] == 'STATE_OPEN']: #ignore the clients in state 'INIT' or 'TRYOPEN'
                    is_expired = False

                    for client in expired_clients: #this is horrendous. Basically: if we have 3 matching values out of 4, we can be fairly certain it's the matching entry.
                        if (i['counterparty']['client_id'] or i['client_id'] in client) and sum(1 for x in [v for v in client.values()][0] if x in {i['counterparty']['connection_id'], i['id'], chain_id }) >= 3:
                            is_expired = True
                            break

                    if not is_expired:
                        try:
                            client_data = get(f"{rest_server}/ibc/core/client/v1/client_states/{i['client_id']}", timeout=4).json()
                            i['counterparty']['chain_id'] = client_data['client_state']['chain_id']
                            i['chain_name'] = [j['chain_name'] for j in chain_data if j['chain_id'] == client_data['client_state']['chain_id']][0]
                            ibc_data.append(i)

                        except IndexError: #the IndexError can only occur if the client_data query worked but the counterparty chain is not present in "chain_data"
                            syslog(LOG_ERR, f"IBC: error in 'get_ibc_data': {chain_id}: counterpart chain {client_data['client_state']['chain_id']} is not tracked")
                        except Exception as e:
                            #typically a KeyError, getting something like "'id': 'connection-localhost', 'client_id': '09-localhost'"
                            #but could be a rest server not responding.
                            syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/client/v1/client_states/{i['client_id']}")
                            syslog(LOG_ERR, f"IBC: error in 'get_ibc_data': {chain_id}: {str(e)}")
                            pass
                        sleep(1) #avoid getting 429's if using a public REST server

                key = data['pagination']['next_key']

                if not key:
                    break

                sleep(1)  # if using a public rest server, might be best to throttle down the queries

        else:
            for connection in connections:
                try:
                    data = get(f"{rest_server}/ibc/core/connection/v1/connections/{connection}", timeout=4).json()['connection']
                    data['id'] = connection
                    ibc_data.append(data)
                except Exception as e:
                    syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/connection/v1/connections/{connection}")
                    syslog(LOG_ERR, f"IBC: Failed to check connection: {chain_id}, {connection}: {str(e)}")
                sleep(1)  # avoid getting 429's too fast if using a public REST server

        return ibc_data

    def check_client(self, chain_id, client_id, connection_id, counterpart_connection_id):
        #check the client on the chain id
        revision_height = None
        trusting_period = None
        chain_name = None
        rest_server = None
        try:
            rest_server = [j['api'] for j in chain_data if j['chain_id'] == chain_id][0]
            #check the status:
            status = get(f"{rest_server}/ibc/core/client/v1/client_status/{client_id}").json()['status']
            state = get(f"{rest_server}/ibc/core/client/v1/client_states/{client_id}").json()['client_state']
            if status == 'Active':
                revision_height = state['latest_height']['revision_height']
                trusting_period = int(state['trusting_period'][:-1]) #returns something like 518400s: drop the 's' and interpret as int
                chain_name = [j['chain_name'] for j in chain_data if j['chain_id'] == state['chain_id']][0]

            elif status == 'Expired':
                for data in self.ibc_data: #delete the expired client from the list
                    if client_id in data and data[client_id]['counterpart_chain_id'] == state['chain_id']:
                        self.ibc_data.remove(data)
                        break
                    #add them to the expired_clients so that we skip checking them. Store 4 different items so that we can identify them with certainty.
                expired_clients.append({client_id : [connection_id, counterpart_connection_id, chain_id, state['chain_id']]})

                syslog(LOG_WARNING, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id} {chain_id}, {state['chain_id']}: {status}")
                return None, None, None

            else:
                syslog(LOG_WARNING, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id} {chain_id}, {state['chain_id']}: {status}")

        except Exception as e:
            syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id}")
            syslog(LOG_ERR, f"IBC: Error retrieving data for {chain_id}, {client_id}: {str(e)}")

        return revision_height, trusting_period, chain_name

    def check_client_update_status(self, revision_height, trusting_period, chain_id, counterpart_chain_id, client_id, chain_name):
        rest_server = None
        for data in self.ibc_data: #if the client was checked less than the "update frequency" ago, skip it.
            if client_id in data and data[client_id]['chain_id'] == chain_id:
                update_time = data[client_id]['last_checked']
                if datetime.now(timezone.utc).timestamp() - update_time < update_frequency*3600:
                    return
        #else, check the last update block and time
        update_time = round(datetime.now(timezone.utc).timestamp())
        try:
            rest_server = [j['api'] for j in chain_data if j['chain_id'] == counterpart_chain_id][0]
            data = get(f"{rest_server}/cosmos/base/tendermint/v1beta1/blocks/{revision_height}").json()['block']['header']['time']
            revision_height_timestamp = datetime.timestamp(datetime.fromisoformat(data.split('.')[0]))

            # compare both timestamps (last update vs current time)
            delta = update_time - revision_height_timestamp

            syslog(LOG_INFO, f"IBC: {client_id} {round((trusting_period-delta)/3600, 2)} hours left")

            # if the revision height happened earlier than "expiry_alert_threshold" % of the trusting period, send out a Discord alert.
            if delta > trusting_period * expiry_alert_threshold and trusting_period-delta < 172800:  #alert only when less than 48h remain, otherwise it can be annoying as some bonding periods are long and 80% leaves several days.
                discord_message(title="WARNING - IBC Client Expiration",
                                     description=f"""Client **{client_id}** on {chain_name} (**{chain_id}**, **{counterpart_chain_id}**) will expire in ~{round((trusting_period-delta)/3600, 2)} hours)""", color=16776960,
                                     tag=role_id)

            #add or update the info in the ibc_data object
            data_exists = False
            for data in self.ibc_data:
                if client_id in data and data[client_id]['chain_id'] == chain_id:
                    data[client_id]['time_to_expiry'] = round((trusting_period - delta) / 3600, 2)
                    data[client_id]['last_checked'] = update_time
                    data_exists = True
                    break
            if not data_exists:
                self.ibc_data.append({client_id : {'chain_id': chain_id, 'counterpart_chain_id': counterpart_chain_id, 'time_to_expiry': round((trusting_period - delta) / 3600, 2),
                                                   'chain_name': chain_name, 'last_checked': update_time}})

        except IndexError:
            syslog(LOG_ERR, f"IBC: no rest server configured for {counterpart_chain_id}")
        except KeyError: #the rest server does not have the block history (i.e. was pruned or statesynced recently)
            syslog(LOG_ERR, f"Error in check_client_update_status {client_id} on {chain_id}, {counterpart_chain_id}: height unavailable on rest server")

        except Exception as e:
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


