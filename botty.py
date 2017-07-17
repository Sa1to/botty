import os
import time
import requests
import datetime
from slackclient import SlackClient

BOT_ID = os.environ.get("BOT_ID")
MASTER_ID = os.environ.get("MASTER_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "do"
CALL_COMMAND = "call"

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
reportSent = 0


def get_all_fields(message, res):
    message = message + '*' + unicode(res['name']) + '*' + "\n" + '>*Price in USD:* ' + \
              unicode(res['price_usd']) + "\n" + \
              '>*Price in BTC:* ' + unicode(res['price_btc']) + "\n" + \
              '>*24 volume USD:* ' + unicode(res['24h_volume_usd']) + "\n" + \
              '>*Market cap USD:* ' + unicode(res['market_cap_usd']) + "\n" + \
              '>*Available supply:* ' + unicode(res['available_supply']) + "\n" + \
              '>*Total supply:* ' + unicode(res['total_supply']) + "\n" + \
              '>*Percent change for 24h:* ' + unicode(res['percent_change_24h']) + "\n" + \
              '>*Percent change for 7d:* ' + unicode(res['percent_change_7d']) + "\n" + \
              '>*Percentage change for 1h:* ' + \
              unicode(res['percent_change_1h']) + "\n" + '>*Last updated:* ' + \
              datetime.datetime.fromtimestamp(float(res['last_updated'])).__str__() + "\n"

    return message


def get_extended_fields(message, res, curr):
    message = get_all_fields(message, res)

    try:
        message = message + \
                  '>*Price in ' + curr + ':* ' + unicode(res['price_' + curr]) + "\n" + \
                  '>*24 volume ' + curr + ':* ' + unicode(res['24h_volume_' + curr]) + "\n" + \
                  '>*Market cap ' + curr + ':* ' + unicode(res['market_cap_' + curr]) + "\n"
    except KeyError:
        message = "You gave me wrong currency!"
        
    return message


def send_coins_raport(channel, user):
    response = requests.get("https://api.coinmarketcap.com/v1/ticker/?limit=10").json()
    message = "\n"
    for res in response:
        message = get_all_fields(message, res)

    slack_client.api_call("chat.postMessage", channel=channel,
                          text="<@" + user + ">" + " *REPORT ABOUT TOP 10 CRYPTO CURRENCIES:*" + message,
                          as_user=True)


def check_hourly_change():
    response = requests.get("https://api.coinmarketcap.com/v1/ticker").json()
    message = "*TOP 5 CURRENCIES THAT EXCEEDED 10% CHANGE DURING LAST 1 HOUR:*\n"
    present = 0
    for res in response:
        if ('None' not in unicode(res['percent_change_1h'])) and (
                        float(res['percent_change_1h']) > 10 or float(res['percent_change_1h']) < -10):
            present += 1
            message = get_all_fields(message, res)
            if present == 5:
                break

    if present != 0:
        slack_client.api_call("chat.postMessage", channel="#general",
                              text="<!here>" + message, as_user=True)


def handle_command(command, channel, output):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    flag = 0
    response = "Not sure what you mean. Use *help* command to see more"

    if output['user'] == MASTER_ID:
        slack_client.api_call("chat.postMessage", channel=channel,
                              text="Yes, master", as_user=True)
        slack_client.api_call(
            "reactions.add",
            channel=channel,
            name="heart",
            timestamp=output['ts']
        )

    if 'help' in command:
        flag = 1
        message = "*HERE IS THE LIST OF COMMANDS THAT YOU CAN USE:* \n" + \
                  "*all_coins:*" + "\n" + ">prints report about top 10 currencies" + "\n" + \
                  "*convert [currency]:*" + "\n" + ">return price, 24h volume, and market cap in terms of another currency for top 10 crypto" + "\n" + \
                  "*coin [crypto] [(optional)currency]:*" + "\n" ">return info about single crypto currency (by default in USD)"

        slack_client.api_call("chat.postMessage", channel=channel,
                              text=message, as_user=True)

    elif 'all_coins' in command:
        flag = 1
        send_coins_raport(channel, output['user'])

    elif 'convert' in command:
        flag = 1
        currency = command.split('convert ', 1)[1]
        url = "https://api.coinmarketcap.com/v1/ticker/?convert=" + currency + "&limit=10"
        response = requests.get(url).json()

        if currency not in unicode(response[0]):
            slack_client.api_call(
                "reactions.add",
                channel=channel,
                name="red_circle",
                timestamp=output['ts']
            )
            slack_client.api_call("chat.postMessage", channel=channel,
                                  text="<@" + output['user'] + ">" + " You gave me wrong currency", as_user=True)
        else:
            message = "\n"
            for res in response:
                message = get_all_fields(message, res)

            slack_client.api_call("chat.postMessage", channel=channel,
                                  text="<@" + output['user'] + ">" + message, as_user=True)
    elif 'coin' in command:
        print(output)
        flag = 1
        currency = command.split(' ')
        message = "\n"
        if len(currency) == 2:
            url = "https://api.coinmarketcap.com/v1/ticker/" + currency[1]
            response = requests.get(url)
            if response.status_code == 200:
                message = get_all_fields(message, response.json()[0])
            else:
                message = "You gave me wrong currency! I don't understand " + currency[1]
        else:
            url = "https://api.coinmarketcap.com/v1/ticker/" + currency[1] + "/?convert=" + currency[2]
            response = requests.get(url)
            if response.status_code == 200:
                message = get_extended_fields(message, response.json()[0], currency[2])
            else:
                message = "You gave me wrong currency!"

        slack_client.api_call("chat.postMessage", channel=channel,
                              text="<@" + output['user'] + ">" + message, as_user=True)

    if flag == 0:
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel'], slack_rtm_output[0]
    return None, None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("Botty connected and running!")
        while True:
            command, channel, output = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(command, channel, output)
            time.sleep(READ_WEBSOCKET_DELAY)

            currDateTime = datetime.datetime.time(datetime.datetime.now())

            if currDateTime.minute == 0 and currDateTime.second == 0:
                check_hourly_change()
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
