from discord import Intents
from discord.ext import commands
from threading import Thread
from requests.exceptions import ReadTimeout

from monitor import *

intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_message(message):
    await bot.process_commands(message)


@bot.command(name="data")
async def input(message):

    """Displays the list of currently tracked IBC client and their last known status. No arguments."""

    data = MonitorAll.ibc_data

    title="IBC clients status"
    descriptions = []
    description = ""
    for i in data:
        for key in i:
            description += f"""**{i[key]['chain_name']}**\nClient id: **{key}**\n🔗Chain id: **{i[key]['chain_id']}**\n🔗Counterpart chain id: **{i[key]['counterpart_chain_id']}**\n
                        ⏳Time to expiry: **{str(i[key]['time_to_expiry'])+' hours ⚠️' if i[key]['time_to_expiry'] < 50 else str(i[key]['time_to_expiry'])+' hours ✅'}**\n
                        🕙Last checked: **{datetime.fromtimestamp(i[key]['last_checked']).strftime('%Y-%m-%d %H:%M')+ ' UTC'}**\n\n"""
            if len(description)+len(title) > 2000:
                descriptions.append(description)
                description = ""

    for description in descriptions:
        embed = Embed(title=title, description=description)
        await message.channel.send(embed=embed)
        title = ""
        sleep(0.5)


@bot.command(name="wallets")
async def input(message):

    """Displays the list of currently tracked wallets and their last known balance. No arguments."""

    data = MonitorAll.wallet_balances
    try:
        last_update = datetime.fromtimestamp(MonitorAll.update_time_wallets).strftime('%Y-%m-%d %H:%M')
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
    balance = None
    try:
        balance = get(f"{data[0]['api']}/cosmos/bank/v1beta1/balances/{wallet}/by_denom?denom={data[0]['denom']}",
                      timeout=3)

        if balance.status_code == 200:
            balance = balance.json()['balance']['amount']
            balance = round(int(balance) / 10 ** data[0]['exponent'], 3)
        else:
            raise Exception(balance)

    except ReadTimeout:
        discord_message(title="",
                        description=f"{data[0]['denom']} REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, please inform an administrator ",
                        color=16776960, tag=f"<@{user_id}>")
        return

    except Exception as e:
        if balance is not None:
            syslog(LOG_ERR,
                   f"IBC: failed to check wallet: {message.message.content}: {balance.status_code} {balance.reason}")
            description = f"""Query failed with error `{balance.status_code} {balance.reason}`\n```{balance.text}```
                            If it's an error 400, please ensure that the wallet address is valid.\n
                            If an error 429, wait a few seconds before retrying.\n
                            If it keeps happening, try to re-register the chain with a different REST server."""

        else:
            syslog(LOG_ERR, f"IBC: failed to check wallet: {message.message.content}: {e}")

            description = f"Couldn't check wallet. Got error:\n\n```{e}```\nPlease ensure that the address is correct."

        discord_message(title="",
                        description=description, color=16776960, tag=f"<@{user_id}>")
        return

    #insert the wallet / chain / user in the tracked_wallets dict
    tracked_wallets[wallet] = [chain_id, f"<@{user_id}>", alert_threshold]

    try:
        with open(path.join(local_directory, "tracked_wallets.py"), "w") as f:
            f.write(f"tracked_wallets = {str(pformat(tracked_wallets))}")

        MonitorAll.wallet_balances[wallet] = [data[0]['chain_name'], str(balance) + ' ' + data[0]['full_denom']]
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
                del MonitorAll.wallet_balances[wallet]
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
            MonitorAll.wallet_balances[wallet_data[0]] = [data[0]['chain_name'],
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
    balance = None
    try:
        balance = get(f"{data[0]['api']}/cosmos/bank/v1beta1/balances/{wallet}/by_denom?denom={data[0]['denom']}", timeout=3)

        if balance.status_code == 200:
            balance = balance.json()['balance']['amount']
            balance = round(int(balance)/10**data[0]['exponent'], 3)
        else:
            raise Exception(balance)

    except ReadTimeout:
        discord_message(title="",
                        description=f"{data[0]['denom']} REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, please inform an administrator ",
                        color=16776960, tag=f"<@{user_id}>")
        return

    except Exception as e:
        if balance is not None:
            syslog(LOG_ERR, f"IBC: failed to check wallet: {message.message.content}: {balance.status_code} {balance.reason}")
            description = f"""Query failed with error `{balance.status_code} {balance.reason}`\n```{balance.text}```
                        If it's an error 400, please ensure that the wallet address is valid.\n
                        If an error 429, wait a few seconds before retrying.\n
                        If it keeps happening, try to re-register the chain with a different REST server."""

        else:
            syslog(LOG_ERR, f"IBC: failed to check wallet: {message.message.content}: {e}")

            description = f"Couldn't check wallet. Got error:\n\n```{e}```"

        discord_message(title="",
                        description=description, color=16776960, tag=f"<@{user_id}>")
        return

    MonitorAll.wallet_balances[wallet] = [data[0]['chain_name'], str(balance) + ' ' + data[0]['full_denom']]
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
        chain_id = get(f"{rest_server}/cosmos/base/tendermint/v1beta1/node_info", timeout=5)

        if chain_id.status_code == 200:
            chain_id = chain_id.json()['default_node_info']['network']
        else:
            raise Exception("status_code", chain_id)

        if not denom:
            try:
                denom = get(f"{rest_server}/cosmos/mint/v1beta1/params", timeout=5)
                if denom.status_code == 200:
                    denom = denom.json()['params']['mint_denom']
                else:
                    raise Exception("status_code", denom)

            except: #some chains have their own custom endpoint with their name instead of "cosmos"... not too reliable though.
                try:
                    denom = get(f"{rest_server}/{chain_name.lower()}/mint/v1beta1/params", timeout=5)
                    if denom.status_code == 200:
                        denom = denom.json()['params']['mint_denom']
                    else:
                        raise Exception("status_code", denom)
                except:
                    raise Exception("no_denom")
            #exponent = get(f"{rest_server}/cosmos/bank/v1beta1/denoms_metadata/{denom}", timeout=5).json()['params']['mint_denom']
            #this value isn't always available. Best to pass it as a parameter.
            if full_denom.lower() not in denom:
                raise Exception("bad_denom", denom, full_denom)

    except ReadTimeout:
        discord_message(title="",
                        description=f"REST server did not respond in time. Please try again in a few minutes.\n\nIf still no success, try another.",
                        color=16776960, tag=f"<@{user_id}>")
        return
    except Exception as e:
        syslog(LOG_ERR, f"IBC: failed to register chain: {message.message.content}: {e}")

        if "status_code" in str(e):
            description = f"""Query failed with error `{e.args[1].status_code} {e.args[1].reason}`\n```{e.args[1].text}```
                                    If it's an error 400, please ensure that the wallet address is valid.\n
                                    If an error 429, wait a few seconds before retrying.\n
                                    If it keeps happening, try to re-register the chain with a different REST server."""
            color=16515843

        elif "no_denom" in str(e):
                description = """Couldn't retrieve the token denom.\n\n
                        If you know this denom (e.g. 'uatom') and are confident it is correct, please pass the command again, specifiyng it at the end:\n\n
                        $register_chain COSMOS https://rest.sentry-01.theta-testnet.polypore.xyz ATOM 6 **uatom**\n\n
                        If still encountering an issue, you may contact an administrator."""
                color = 16515843

        elif "bad_denom" in str(e):
            description = f"""The token name does not to match its base denom. Found `{e.args[1]}` which does not seem to match `{e.args[2]}`.\n\n
                                    If you are confident it is actually correct, please pass the command again, specifiyng this base denom it at the end:\n\n
                                    $register_chain {chain_name} {rest_server} {full_denom.upper()} {exponent} **{denom}**\n\n
                                    If still encountering an issue, you may contact an administrator."""
            color = 16776960

        else:
            description = f"Error registering chain: {e}"
            color=16515843

        discord_message(title="",
                        description=description,
                        color=color, tag=f"<@{user_id}>")
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


MonitorAll = MonitorAll()
Thread(target=MonitorAll.start).start()
bot.run(bot_token)
