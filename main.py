import asyncio
from syslog import syslog, LOG_ERR, LOG_INFO, LOG_WARNING
from threading import Thread
from time import sleep
from requests import get
from datetime import datetime, timezone
from discord import SyncWebhook, Embed, Intents
from discord.ext import commands
from urllib.parse import quote

from config import *


class ClientMonitorAll:

    def __init__(self):

        self.ibc_data = {}

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(self.update_ibc_data())
        loop.run_forever()

    async def update_ibc_data(self):

        while True:
            for chain_id in monitored_chains:
                #get the client ids + their counterpart chain and client
                ibc_data = self.get_ibc_data(chain_id, connections=monitored_chains[chain_id])
                #next, check the status of each client. If it's active, check the last update and trusting period.

                current_time_utc = datetime.now(timezone.utc).timestamp() #current time to calculate how long ago the client was updated.

                for i in ibc_data:
                    revision_height, trusting_period = self.check_client(chain_id, i['client_id'])
                    #the above will be None if the client is expired. No alert in this instance.
                    if revision_height:
                        self.check_client_update_status(revision_height, trusting_period,
                                                        current_time_utc, chain_id, i['counterparty']['chain_id'], i['client_id'])
                        #and check the counterpart client
                        #IMPORTANT: the "chain_id" and  "i['counterparty']['client_id']" are inverted here.
                        revision_height, trusting_period = self.check_client(i['counterparty']['chain_id'], i['counterparty']['client_id'])
                        if revision_height:
                            self.check_client_update_status(revision_height, trusting_period,
                                                            current_time_utc, i['counterparty']['chain_id'], chain_id,  i['counterparty']['client_id'])

            await asyncio.sleep(7200)

    def get_ibc_data(self, chain_id, connections=None):

        key = ""
        ibc_data = []
        rest_server = [j['api'] for j in rest_servers if j['chain_id'] == chain_id][0]

        if not connections: #no connections specified = scan them all

            while True:
                try:
                    query = f"{rest_server}/ibc/core/connection/v1/connections?pagination.key={quote(key)}"
                    data = get(query, timeout=2).json()

                    pagination_total = int(data['pagination']['total']) if data['pagination']['total'] else 0
                    if pagination_total > 100:
                        self.discord_message("Configuration issue",
                                f"There are {pagination_total} IBC connections to go through. Aborting as this will likely fail.\nPlease define specific connections to monitor instead.",
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
        try:
            rest_server = [j['api'] for j in rest_servers if j['chain_id'] == chain_id][0]
            #check the status:
            status = get(f"{rest_server}/ibc/core/client/v1/client_status/{client_id}").json()['status']
            state = get(f"{rest_server}/ibc/core/client/v1/client_states/{client_id}").json()['client_state']
            if status == 'Active':
                #state = get(f"{rest_server}/ibc/core/client/v1/client_states/{client_id}").json()['client_state']
                revision_height = state['latest_height']['revision_height']
                trusting_period = int(state['trusting_period'][:-1]) #returns something like 518400s: drop the 's' and interpret as int

            else:
                syslog(LOG_WARNING, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id} {chain_id}, {state['chain_id']}: {status}")

        except IndexError:
            syslog(LOG_ERR, f"IBC: no rest server configured for {chain_id}")

        except Exception as e:
            #print(f"IBC: Error retrieving data for {chain_id}, {client_id}: {str(e)}")
            syslog(LOG_ERR, f"IBC: {rest_server}/ibc/core/client/v1/client_status/{client_id}")
            syslog(LOG_ERR, f"IBC: Error retrieving data for {chain_id}, {client_id}: {str(e)}")

        return revision_height, trusting_period

    def check_client_update_status(self, revision_height, trusting_period, current_time_utc, chain_id, counterpart_chain_id, client_id):
        try:
            rest_server = [j['api'] for j in rest_servers if j['chain_id'] == counterpart_chain_id][0]
            data = get(f"{rest_server}/cosmos/base/tendermint/v1beta1/blocks/{revision_height}").json()['block']['header']['time']
            revision_height_timestamp = datetime.timestamp(datetime.fromisoformat(data.split('.')[0]))

            # compare both timestamps
            delta = current_time_utc - revision_height_timestamp

            syslog(LOG_INFO, f"IBC: {client_id} {round((trusting_period-delta)/3600, 2)} hours left")

            # if the revision height happened earlier than XX% of the trusting period, send out a Discord alert.
            if delta > trusting_period * alert_threshold:
                self.discord_message(title="WARNING - IBC Client Expiration",
                                     description=f"""Client **{client_id}** on chains **{chain_id}**, **{counterpart_chain_id}** will expire in {round(trusting_period-delta)} seconds (~{round((trusting_period-delta)/3600, 2)} hours)""", color=16776960,
                                     tag=role_id)

            self.ibc_data[f'{client_id}'] = {'chain_id': chain_id, 'counterpart_chain_id': counterpart_chain_id, 'time_to_expiry': round((trusting_period-delta)/3600, 2)}

        except IndexError:
            syslog(LOG_ERR, f"IBC: no rest server configured for {counterpart_chain_id}")

        except Exception as e:
            #print(f"IBC: Error check client update status {client_id} on {chain_id}: {str(e)}")
            syslog(LOG_ERR, f"IBC: {rest_server}/cosmos/base/tendermint/v1beta1/blocks/{revision_height}")
            syslog(LOG_ERR, f"IBC: Error in check_client_update_status {client_id} on {chain_id}, {counterpart_chain_id}: {str(e)}")

    def discord_message(self, title, description, color, tag=None):
        try:
            webhook = SyncWebhook.from_url(discord_webhook)
            #discord messages can't exceed 4096 characters, need to truncate in case it's longer.
            embed = Embed(title=title, description=description[:(4095 - len(title))],color=color)
            webhook.send(tag, embed=embed)
        except Exception as e:
            syslog(LOG_ERR, f"IBC: Couldn't send a discord alert, please check configuration.\n{description}\n{e}")


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

    data = ClientMonitorAll.ibc_data

    title="IBC clients status"
    description = ""
    for key in data:
        description += f"**{key}**:\n🔗'chain_id': **{data[key]['chain_id']}**\n🔗'counterpart_chain_id': **{data[key]['counterpart_chain_id']}**\n⏳'time_to_expiry': **{str(data[key]['time_to_expiry'])+' hours ⚠️' if data[key]['time_to_expiry'] < 50 else str(data[key]['time_to_expiry'])+' hours ✅'}**\n\n"
        #embed.add_field(name=key, value=[i, data[key][i] for i in data[key]])
    embed = Embed(title=title, description=description[:(4095 - len(title))])
    #await message.channel.send(ClientMonitorAll.ibc_data)

    await message.channel.send(embed=embed)

bot.run(bot_token)
