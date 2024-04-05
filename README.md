## Description
A discord bot that monitors the status of IBC channels and the balances of the relayer wallets of a blockchain from the Cosmos ecosystem.

- Requires the Discord python module, install with `python3 -m pip install discord`. Other packages are present by default.
- Alerts are sent to a configurable Discord channel, mentioning roles/people or not, when the last update of a client happened more than 80% of its trusting period ago (by default, can be modified).
- E.g. if the trusting period is 51800 seconds and the last update (manual update or simply a processed IBC transaction) occurred over 41440 seconds ago. It means that in 10360 seconds the client will expire, therefore one should manually update it.
- The bot can be queried from within the Discord channel by passing the following commands:
  - `$data` will return the list of clients and their current status.
  - `$wallets` will return the list of the monitored wallets and their balance.
- Wallet balances alerts are configurable and work on a subscription basis:
  - Operators can register by running `$register wallet_address chain_id alert_threshold` in the bot channel. 
  - Example : `$register cosmos1xxxxxxxxxxxxxxxxxxxxxx theta-testnet-1 2` means that the user will be notified when the balance of this wallet falls below 2 ATOM on the Cosmos testnet.
  - The notification message will tag the user.
  - The wallet monitoring data is stored in `tracked_wallets.py`, which will be created if it doesn't exist.
  - A wallet can be deregistered so that its balance is no longer checked with the command `$deregister <wallet>`.
- Run `$help` to view the available commands, and `$help <command>` to get information about a specific command.

## Deployment & Configuration
The bot must be added in your own Discord account, then deployed in your server. 
- Log in at https://discord.com/developers/applications and click on **New Application** on the top right.
- Give it a name and click on **Create**
- In the **Bot** menu entry, click on **Reset Token** and confirm (you may need to enter a code if you enable 2FA).
- **Copy this token and do not lose it**. You can already save it in `config.py` for the `bot_token` value.
- in the **OAuth2** menu, scroll down to **OAuth2 URL Generator** and tick the **bot** checkbox. Then below, tick the **Send Messages** checkbox.
- Open the URL that appeared at the bottom of the page, select the Discord server where you want to add the bot, and click on **Authorize**
- Now go to your Discord server, right-click on the channel where the bot should write and click on **Edit** --> **Add members or roles** --> Select the bot.
- Select the **Integrations** menu item --> **Webhooks** --> **New Webhook** --> Select it and click on **Copy Webhook URL**.
- Save this webhook as the value for the **discord_webhook** item in `config.py`. This allows the bot to send messages in this channel.
###
- In `config.py` 
  - Once you have filled out the discord webhook url and bot token, you can define which users/roles will be tagged in the bot messages by updating the value of **role_id** item.
  - Right-click on a user and click on **Copy User ID**, or click on a user and right-click on one of its roles then on **Copy Role ID**.
  - An ID looks like `972778865355272194`
  - Add these IDs in the **role_id** item, following the syntax:
    - For a role: `<@&972778865355272194>`
    - For a user: `<@972778865355272194>`
    - You can add multiple roles and IDs by separating them with a space: `role_id = <@&972778865355272194> <@951374414451187732>"`
    - Leave blank to tag no one.
  - `monitored_chains` is a dictionary whose keys are the chain_id and the values are a list.
    - the value can either be a list of connections to check, e.g. `['connection-0', 'connection-5']`, or an empty list `[]`
    - in this case, all the connections of the concerned chain will be checked.
    - the process will abort if there are more than 100 connections to check (on the cosmos testnet, there are nearly 3000).
    - if this happens, update the list to limit the scan to specific connections.
  - `rest_servers` is a dictionary, with items in the form:
    - `{'chain_id': 'theta-testnet-001', 'api': 'https://rest.sentry-01.theta-testnet.polypore.xyz', 'chain_name': 'COSMOS', 'exponent': 6, 'denom': 'uatom', 'full_denom': 'ATOM'}`
    - The `exponent` is the number of decimals of a token: 1 ATOM = 10**6 uatom.
    - it must contain an item for each counterpart chain to be able to verify the client. If one is missing, the concerned clients won't be checked.
  - The bot will update its data every 6 hours by default. You can adjust this value by changing the `update_frequency` item.

- Run with `python3 main.py`, preferably as a systemd service containing for example:
```
[Unit]
Description=IBC clients monitor + discord bot
After=network.target

[Service]
Type=simple
Restart=on-failure
RestartSec=3
ExecStart=/usr/bin/python3 /etc/IBC-Client-Monitor/main.py

ExecStop=/bin/kill -9 $MAINPID

[Install]
WantedBy=multi-user.target
```