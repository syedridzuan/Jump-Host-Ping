#!/home/ipcore/venv-py2.7/bin/python

"""
This is pint script for ERX.

Please edit config.yaml, do not edit this script.
V1.0

"""

from __future__ import print_function
import traceback

import paramiko
from paramiko_expect import SSHClientInteraction
import re
import yaml
import yamlordereddictloader
from pprint import pprint as pp
import os
import logging
import time
import telegram


sfolder = os.path.dirname(os.path.realpath(__file__))
script_name = os.path.basename(__file__)
log_name = os.path.basename(__file__) + ".log"
log_file_list = [sfolder, "log", log_name]
logfile = os.path.join(*log_file_list)

logging.basicConfig(level=logging.INFO,
                    filename=logfile,  # log to this file.
                    format='%(asctime)s %(message)s')  # include timestamp.

start_time = time.time()
logging.info("Script start time: {}".format(start_time))

config_yaml = os.path.join(sfolder, "config.yaml")
print(config_yaml)

with open(config_yaml) as f:
    yaml_data = yaml.load(f, Loader=yamlordereddictloader.Loader)
    host1_config = yaml_data['host1']
    host2_config = yaml_data['host2']
    tgram_config = yaml_data['telegram']


logging.info("Initiliaze telegram bot")
bot = telegram.Bot(token=tgram_config['token'])
chats = [tgram_config['chat']]


def main():
    """Main program."""
    for key, host2 in yaml_data['ping'].items():
        prompt = ('{}@{}.*'.format(host1_config['username'],
                                   host2['jump_host']))
        logging.info("ERX: {}".format(key))
        print(key, host2)
        try:
            # Create a new SSH client object
            client = paramiko.SSHClient()

            # Set SSH key parameters to auto accept unknown hosts
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect to the host
            client.connect(hostname=host2['jump_host'],
                           username=host1_config['username'],
                           password=host1_config['password'])

            with SSHClientInteraction(client, timeout=10, display=True) as interact:
                interact.expect(prompt)
                result = in_host2(interact, host2, host2['ip_list'], key)
                if result:
                    pass
                    #check_ping(result, key)
                else:
                    pass
                    send_telegram("Some wrong with accessing ERX, please check!")
                interact.expect(prompt)

        except Exception:
                send_telegram("Some wrong with script")
                traceback.print_exc()

        finally:
            try:
                client.close()
                #pp(result)
            except Exception:
                pass

def check_ping(result, key):
    for item in result:
        if not item[1]:
            msg = ("Ping not 100% detected for ip: {},"
                   " host:{} and LNS: {}".format(item[0], item[1], key))
            print(msg)
            send_telegram(msg)

def send_telegram(message):
    """Send telegram message."""
    logging.info("Sending file and message to telegram.")
    for item in chats:
        try:
            bot.send_message(chat_id=item,
                             text=message,
                             parse_mode=telegram.ParseMode.HTML)
        except Exception as e:
            print(e.__doc__)
            print(e.message)



def in_host2(interact, host2, ip_list, host2_name):
    """ERX detail execution."""
    result = []
    telnet = 'telnet {} routing-instance {}'.format(host2['ip'], host2['vrf'])
    interact.send(telnet)
    interact.expect("Username.*")
    interact.send(host2_config['username'])
    interact.expect('Password.*')
    interact.send(host2_config['password'])
    interact.expect("{}.*".format(host2['prompt']))

    for ips in ip_list:
        for key, ip in ips.items():
            interact.send('ping {}'.format(ip))
            interact.expect("{}.*".format(host2['prompt']))
            cmd_output_ls = interact.current_output_clean
            logging.info(cmd_output_ls)

            if re.search(r'\s0\%', cmd_output_ls):
                logging.info("Ping not 100%")
                msg = ("Ping 100% failed detected for ip: {},"
                       " host:{} and LNS: {}".format(ip, key, host2_name))
                print(msg)
                send_telegram(msg)
                result.append([key, ip, False])
            else:
                logging.info("Ping ok")
                result.append([ip, True])

    interact.send('exit')

    return result

if __name__ == '__main__':
    main()
