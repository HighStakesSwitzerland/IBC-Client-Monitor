A Python class to retrieve and check the status of IBC clients on a chain and its counterpart.

- Alerts are sent to a configurable Discord channel, mentioning roles/people or not, when the last update of a client happened more than 80% of its trusting period.
- E.g. if the trusting period is 51800 seconds and the last update (manual update or simply a processed IBC transaction) occurred over 41440 seconds ago. It means that in 10360 seconds the client will expire, therefore one should manually update it.

- Requires the Discord python module, install with `python3 -m pip install discord`. Other packages are present by default.

- Configuration is in `config.py` 
  - fill out the discord webhook url.
  - the role/user ids that would be tagged in the discord messages. Leave blank to tag no one.
  - `monitored_chains` is a dictionary whose keys are the chain_id and the values are a list.
    - the value can either be a list of connections to check, e.g. `['connection-0', 'connection-5']`, or an empty list `[]`
    - in this case, all the connections of the concerned chain will be checked.
    - the process will abort if there are more than 100 connections to check (on the cosmos testnet, there are nearly 3000).
    - if this happens, update the list to limit the scan to specific connections.
  - `rest_servers` is a dictionary: `{'chain_id': 'chain id here', 'api': 'the url of the rest server'}`
    - it must contain an entry for each counterpart chain to be able to verify the client. If one is missing, the concerned clients won't be checked.

- Can be run as Cron jobs, e.g. every hour `0 * * * * sudo -u hermes python3 /home/hermes/HermesClientUpdate/monitor.py`