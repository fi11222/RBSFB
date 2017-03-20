#!/usr/bin/python3
# -*- coding: utf-8 -*-

from ec_app_core import *
from ec_request_handler import *

from rbs_fb_connect import *

from openvpn import OpenvpnWrapper

import random
import sys
from socketserver import ThreadingMixIn

__author__ = 'Pavan Mahalingam'


class RbsBackgroundTask(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

        self.m_logger = logging.getLogger('RbsBackgroundTask')

        self.m_browser = None

        # starts the background thread
        self.start()

    def run(self):
        while True:
            time.sleep(15)
            self.m_logger.info('top')

            if self.m_browser is not None and self.m_browser.isStale():
                self.m_browser.close()
                self.m_browser = None
                self.m_logger.info('*** Browser Driver closed')
            elif self.m_browser is None:
                l_phantomId = 'nicolas.reimen@gmail.com'
                l_phantomPwd = 'murugan!'
                l_vpn = None

                try:
                    self.m_browser = BrowserDriver(l_phantomId, l_phantomPwd, l_vpn)
                    self.m_logger.info('*** Browser Driver set-up complete')
                except Exception as e:
                    self.m_logger.warning('Serious exception - aborting browser driver: ' + repr(e))
                    self.m_browser = None
            else:
                try:
                    t0 = time.perf_counter()
                    self.m_browser.go_random()
                    self.m_browser.get_fb_profile()
                    self.m_logger.info(
                        '*** User data download complete. Elapsed time: {0}'.format(time.perf_counter() - t0))
                except EX.TimeoutException as e:
                    self.m_logger.warning('Non fatal TimeoutException. Will try again.' + repr(e))
                except Exception as e:
                    self.m_logger.warning('Serious exception - killing browser driver: ' + repr(e))
                    self.m_browser.close()
                    self.m_browser = None


class RbsApp(EcAppCore):
    def __init__(self):
        super().__init__()

        self.m_background = RbsBackgroundTask()

# Multi-threaded HTTP server according to https://pymotw.com/2/BaseHTTPServer/index.html#module-BaseHTTPServer
class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """Handles requests in a separate thread each."""


class StartApp:
    """
    This is a simple wrapper around the function which starts the application. Everything is static.
    """

    @classmethod
    def start_rbsfb(cls):
        """
        The actual entry point, called from ``if __name__ == "__main__":``. Does the following:

        #. Initialises the mailer (:any:`EcMailer.initMailer`)
        #. Initialises the logging system (:any:`EcLogger.logInit`)
        """
        print('ScripTrans server starting ...')

        # random generator init
        random.seed()

        # mailer init
        EcMailer.init_mailer()

        # test connection to PostgresQL and wait if unavailable
        while True:
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
                EcLogger.cm_logger.debug('WAITING: No PostgreSQL yet ... : ' + repr(e))
                EcMailer.send_mail('WAITING: No PostgreSQL yet ...', repr(e))
                time.sleep(1)
                continue

        # logging system init
        try:
            EcLogger.log_init()
        except Exception as e:
            EcMailer.send_mail('Failed to initialize EcLogger', repr(e))

        try:
            # instantiate the app (and the connection pool within it)
            l_app = RbsApp()
        except Exception as e:
            EcLogger.cm_logger.critical('App class failed to instantiate. Error: {0}'.format(repr(e)))
            sys.exit(0)

        # initializes request handler class
        EcRequestHandler.init_class(l_app)

        # initializing openvpn wrapper
        OpenvpnWrapper.initClass()

        try:
            # python http server init
            l_httpd = ThreadedHTTPServer(("", EcAppParam.gcm_httpPort), EcRequestHandler)
        except Exception as e:
            EcLogger.cm_logger.critical('Cannot start server at [{0}:{1}]. Error: {2}-{3}'.format(
                EcAppParam.gcm_appDomain,
                EcAppParam.gcm_httpPort,
                type(e).__name__, repr(e)
            ))
            sys.exit(0)

        EcLogger.root_logger().info('gcm_appName    : ' + EcAppParam.gcm_appName)
        EcLogger.root_logger().info('gcm_appVersion : ' + EcAppParam.gcm_appVersion)
        EcLogger.root_logger().info('gcm_appTitle   : ' + EcAppParam.gcm_appTitle)

        # final success message (sends an e-mail message because it is a warning)
        EcLogger.cm_logger.warning('Server up and running at [{0}:{1}]'
                                   .format(EcAppParam.gcm_appDomain, str(EcAppParam.gcm_httpPort)))

        try:
            # start server main loop
            l_httpd.serve_forever()
        except Exception as e:
            EcLogger.cm_logger.critical('App crashed. Error: {0}-{1}'.format(type(e).__name__, repr(e)))

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    StartApp.start_rbsfb()
