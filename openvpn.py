#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

from subprocess import Popen, PIPE, run
import re
import time
import urllib.request
import urllib.error
from threading import Thread
from queue import Queue, Empty  # python 3.x
import sys

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

# Calls a "what is my Ip" web service to get own IP
def getOwnIp():
    # http://icanhazip.com/
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

# turns on Openvpn with the config file given in parameter
# returns a process
# If alive --> everything ok
# if dead (poll() not None) --> error of some kind
def switchonVpn(p_config, p_verbose=True):

    # function to output lines as a queue
    # (1) from http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python
    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    # print IP before openvpn switches on if in verbose mode
    if p_verbose:
        print('Old Ip:', getOwnIp())

    # records starting time to be able to time out if takes too long
    t0 = time.perf_counter()

    # calls openvpn
    ON_POSIX = 'posix' in sys.builtin_module_names
    l_process = Popen(['sudo', 'openvpn', p_config],
                      stdout=PIPE,
                      stderr=PIPE,
                      cwd='.',
                      bufsize=1,
                      universal_newlines=True,
                      close_fds=ON_POSIX)

    # see (1) above
    l_outputQueue = Queue()
    t = Thread(target=enqueue_output, args=(l_process.stdout, l_outputQueue))
    t.daemon = True  # thread dies with the program
    t.start()

    # wait for openvpn to establish connection
    while True:
        # cancels process if openvpn closes unexpectedly or takes more than 30 seconds to connect
        if l_process.poll() is not None or time.perf_counter() - t0 > 30.0:
            l_out = l_process.stdout.readline().strip()
            l_err = l_process.stderr.readline().strip()
            print('+++', l_out)
            print('---', l_err)

            # kills process if still running
            if l_process.poll() is not None:
                l_process.kill()

            break

        # l_out = l_process.stdout.readline().strip()

        # read line without blocking
        try:
            l_out = l_outputQueue.get_nowait().strip()  # or q.get(timeout=.1)
        except Empty:
            time.sleep(.1)
        else:  # got line
            # prints openvpn output if in verbose mode
            if p_verbose:
                print('+++', l_out)

            # if "Initialization Sequence Completed" appears in message --> connexion established
            if re.search('Initialization Sequence Completed', l_out):
                if p_verbose:
                    print('OpenVpn pid :', l_process.pid)
                    # print new IP
                    print('New Ip      :', getOwnIp())
                    print('Elapsed time:', time.perf_counter() - t0, 'seconds')

                break

    return l_process

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB scraping web service for ROAD B SCORE                   |')
    print('|                                                            |')
    print('| Openvpn driver script                                      |')
    print('|                                                            |')
    print('| v. 1.1 - 14/03/2017                                        |')
    print('+------------------------------------------------------------+')

    l_process = switchonVpn('India.Maharashtra.Mumbai.TCP.ovpn', p_verbose=True)

    if l_process.poll() is None:
        # kill -9 does not work here (does not kill child processes of which there is one here)
        # kill -15 does not work either (why ?)
        # only killall does
        print('pid: {0}'.format(l_process.pid))
        l_result = run(['sudo', 'killall', '-9' , 'openvpn'], stdout=PIPE, stderr=PIPE)
        print('--> ' + repr(l_result))

    print('Ip now:', getOwnIp())