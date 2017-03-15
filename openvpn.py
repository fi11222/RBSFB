#!/usr/bin/python3
# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, run
import re
import time
import urllib.request
import urllib.error
from threading import Thread
from queue import Queue, Empty  # python 3.x
import sys
import logging

import ec_app_param
from ec_utilities import *

__author__ = 'fi11222'

# !!!!!!! THIS IS NOW OBSOLETE - SEE BELOW !!!!!!!!!!!!
# fi11222 must be added to the sudoer file as a NOPASSWD sudo user
# http://askubuntu.com/questions/334318/sudoers-file-enable-nopasswd-for-user-all-commands

# sudo visudo --->
# add:
# fi11222<TAB>ALL=NOPASSWD: ALL
# under:
# root    ALL=(ALL:ALL) ALL

# As of Ubuntu 16.04, in order to be able to perform sudo commands without having to type the sudo password,
# fi11222 must be added to a file in the /etc/sudoer.d directory as a NOPASSWD sudo user
# https://www.build-business-websites.co.uk/ubuntu-sudo-without-password-prompt/

# sudo visudo -f /etc/sudoers.d/custom-users
# add single line:
# fi11222<TAB>ALL=(ALL) NOPASSWD:ALL

# ---------------------------------------------------- Functions -------------------------------------------------------


class OpenvpnWrapper:
    cm_baseIP = None

    @classmethod
    def initClass(cls):
        cls.cm_baseIP = cls.getOwnIp()
        EcLogger.root_logger().info('Base IP: ' + cls.cm_baseIP)

    @staticmethod
    def getOwnIp():
        """
        Calls a "what is my Ip" web service to get own IP
        """
        l_myIp = None
        for l_ip_service in ['https://api.ipify.org', 'http://checkip.amazonaws.com/',
                             'http://icanhazip.com/', 'https://ipapi.co/ip/']:
            try:
                l_myIp = urllib.request.urlopen(l_ip_service).read().decode('utf-8').strip()
            except urllib.error.URLError as e:
                print('Cannot Open {0} service:'.format(l_ip_service), repr(e))

            if l_myIp is not None:
                break

        return l_myIp

    def __init__(self, p_config):
        """
        turns on Openvpn with the config file given in parameter
        returns a process
        If alive --> everything ok
        if dead (poll() not None) --> error of some kind

        :param p_config:
        :param p_verbose:
        :return:
        """

        self.m_logger = logging.getLogger('OpenvpnWrapper')

        if OpenvpnWrapper.getOwnIp() != OpenvpnWrapper.cm_baseIP:
            self.m_logger.info('VPN probably on already. No need to start a new one.')
            self.m_process = None
            return

        # function to output lines as a queue
        # (1) from http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
        def enqueue_output(out, queue):
            for line in iter(out.readline, b''):
                queue.put(line)
            out.close()

        # print IP before openvpn switches on if in verbose mode
        self.m_logger.info('Old Ip: {0}'.format(OpenvpnWrapper.getOwnIp()))

        # records starting time to be able to time out if takes too long
        t0 = time.perf_counter()

        # calls openvpn
        ON_POSIX = 'posix' in sys.builtin_module_names
        self.m_process = Popen(['sudo', 'openvpn', p_config],
                          stdout=PIPE,
                          stderr=PIPE,
                          cwd='.',
                          bufsize=1,
                          universal_newlines=True,
                          close_fds=ON_POSIX)

        # see (1) above
        l_outputQueue = Queue()
        t = Thread(target=enqueue_output, args=(self.m_process.stdout, l_outputQueue))
        t.daemon = True  # thread dies with the program
        t.start()

        # wait for openvpn to establish connection
        while True:
            # cancels process if openvpn closes unexpectedly or takes more than 30 seconds to connect
            if self.m_process.poll() is not None or time.perf_counter() - t0 > 30.0:
                l_out = self.m_process.stdout.readline().strip()
                l_err = self.m_process.stderr.readline().strip()
                self.m_logger.warning('+++ ' + l_out)
                self.m_logger.warning('--- ' + l_err)

                # kills all openvpn processes if still running
                if self.m_process.poll() is not None:
                    run(['sudo', 'killall', '-9', 'openvpn'], stdout=PIPE, stderr=PIPE)

                break

            # l_out = l_process.stdout.readline().strip()

            # read line without blocking
            try:
                l_out = l_outputQueue.get_nowait().strip()  # or q.get(timeout=.1)
            except Empty:
                time.sleep(.1)
            else:  # got line
                # prints openvpn output if in verbose mode
                self.m_logger.info('+++' + l_out)

                # if "Initialization Sequence Completed" appears in message --> connexion established
                if re.search('Initialization Sequence Completed', l_out):
                    self.m_logger.info('OpenVpn pid : {0}'.format(self.m_process.pid))
                    # print new IP
                    self.m_logger.info('New Ip : ' + OpenvpnWrapper.getOwnIp())
                    self.m_logger.info('Elapsed time: {0} seconds'.format(time.perf_counter() - t0))

                    break

    def close(self):
        l_result = run(['sudo', 'killall', '-9', 'openvpn'], stdout=PIPE, stderr=PIPE)
        self.m_logger.info('Killing vpn processes : ' + repr(l_result))
        self.m_logger.info('End Ip : ' + OpenvpnWrapper.getOwnIp())

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB scraping web service for ROAD B SCORE                   |')
    print('|                                                            |')
    print('| Openvpn driver script                                      |')
    print('|                                                            |')
    print('| v. 1.1 - 14/03/2017                                        |')
    print('+------------------------------------------------------------+')

    # mailer init
    EcMailer.init_mailer()

    # test connection to PostgresQL and wait if unavailable
    gcm_maxTries = 20
    l_iter = 0
    while True:
        if l_iter >= gcm_maxTries:
            EcMailer.send_mail('WAITING: No PostgreSQL yet ...', 'l_iter = {0}'.format(l_iter))
            sys.exit(0)

        l_iter += 1

        try:
            l_connect = psycopg2.connect(
                host=EcAppParam.gcm_dbServer,
                database=EcAppParam.gcm_dbDatabase,
                user=EcAppParam.gcm_dbUser,
                password=EcAppParam.gcm_dbPassword
            )

            l_connect.close()
            break
        except psycopg2.Error as e:
            EcMailer.send_mail('WAITING: No PostgreSQL yet ...', repr(e))
            time.sleep(1)
            continue

    # logging system init
    try:
        EcLogger.log_init()
    except Exception as e:
        EcMailer.send_mail('Failed to initialize EcLogger', repr(e))

    l_vpn = OpenvpnWrapper('India.Maharashtra.Mumbai.TCP.ovpn')
    l_vpn.close()

