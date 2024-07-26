discord_webhook = "" #example: "https://discord.com/api/webhooks/1064946556407658/jytEe1xy8mJj8JXuGK8L2voxMn6AlzOTsTBX8wk_Y2NoeM78CCcs0ykFmDSHcLh73NeD"

bot_token = "" #needed for the bot to be queried from within the channel

guild_id = 914988182594027058 #an example

role_id = ""  #Example : if it is a role, "<@&12345641267>" (mind the <@&>)
              #If it's a user, "<@123456789789>" -- only with <@>
              #Multiple roles or users can be specified. Must be separated with space, not a comma.


monitored_chains = {'elystestnet-1': []} #The value is a list of monitored connections, e.g. ["connection-0", "connection-6"].
                                         # If the value is blank, all connections will be scanned. Otherwise, only the specified connections.


expiry_alert_threshold = 0.80 #% of the trusting period under which an alert is sent. 0.5 = the client hasn't been updated for half of its trusting period

update_frequency = 6 #Frequency at which the bot will update the clients and wallet data, in HOURS.