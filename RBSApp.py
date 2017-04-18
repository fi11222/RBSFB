#!/usr/bin/python3
# -*- coding: utf-8 -*-

from ec_app_core import *
from ec_request_handler import *

from rbs_fb_connect import *

from wrapvpn import OpenvpnWrapper, OpenVpnFailure

import random
import sys
import locale
from socketserver import ThreadingMixIn

__author__ = 'Pavan Mahalingam'


class RbsBackgroundTask(threading.Thread):
    def __init__(self, p_pool):
        super().__init__(daemon=True)

        self.m_logger = logging.getLogger('RbsBackgroundTask')

        self.m_browser = None

        self.m_pool = p_pool

        # starts the background thread
        self.start()

    def internet_check(self):
        try:
            l_ip = OpenvpnWrapper.getOwnIp()

            # if this point is reached --> the internet connection is probably ok
            self.m_logger.info('Own IP: {0}'.format(l_ip))
            l_internetOk = True
        except OpenVpnFailure as e:
            self.m_logger.warning('Own IP failure: ' + repr(e))
            l_internetOk = False

        return l_internetOk

    def log_phantom_connection(self, p_phantom, p_vpn, p_password, p_logIn=True, p_success=True):
        # log message in TB_EC_MSG
        l_conn = self.m_pool.getconn('log_phantom_connection()')
        l_cursor = l_conn.cursor()
        try:
            l_cursor.execute("""
                    insert into "TB_EC_MSG"(
                        "ST_TYPE",
                        "ST_NAME",
                        "ST_LEVEL",
                        "ST_MODULE",
                        "ST_FILENAME",
                        "ST_FUNCTION",
                        "N_LINE",
                        "TX_MSG"
                    )
                    values(%s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    'ULIO',
                    'xxx',
                    'XXX',
                    'RBSApp',
                    './RBSApp.py',
                    'log_phantom_connection',
                    0,
                    'Phantom: {0} [vpn: {1}] {2} {3}'.format(
                        p_phantom, p_vpn,
                        'Login' if p_logIn else 'Logout',
                        'Successful' if p_success else 'Failed'
                    )
                )
            )
            l_conn.commit()
        except Exception as e:
            self.m_logger.warning('TB_EC_MSG insert failure: {0}'.format(repr(e)))
            raise

        l_cursor.close()
        l_cursor = l_conn.cursor()
        try:
            l_cursor.execute("""
                    insert into "TB_PHANTOM_LOGIN"(
                        "ST_PHANTOM_ID",
                        "ST_VPN",
                        "ST_PASSWORD",
                        "ST_OPE",
                        "K_SUCCESS",
                        "DT_LOG"
                    )
                    values(%s, %s, %s, %s, %s, %s);
                """, (
                    p_phantom,
                    p_vpn,
                    p_password,
                    'Login' if p_logIn else 'Logout',
                    p_success,
                    datetime.datetime.now(tz=pytz.utc)
                )
            )
            l_conn.commit()
        except Exception as e:
            self.m_logger.warning('TB_PHANTOM_LOGIN insert failure: {0}'.format(repr(e)))
            raise

        l_cursor.close()
        self.m_pool.putconn(l_conn)

    def run(self):
        l_phantomList = [
            ('karim.elmoulaid@gmail.com', '15Eyyaka', 'Canada.Quebec.Montreal_LOC2S1.TCP.ovpn'),
            ('kabeer.burnahuddin@gmail.com', '15Eyyaka', None),
            ('kabir.abdulhami@gmail.com', '12Alhamdulillah', 'India.Maharashtra.Mumbai.TCP.ovpn'),
            ('nicolas.reimen@gmail.com', 'murugan!', None),
        ]

        l_phantomIndex = 0

        l_internetOk = True
        l_phantomId = ''
        while True:
            l_sleep = random.randint(EcAppParam.gcm_bkgMinDelay, EcAppParam.gcm_bkgMaxDelay)
            self.m_logger.info('[{0}] Waiting for {1} seconds'.format(l_phantomId, l_sleep))

            # Internet connection test
            l_internetOkPrevious = l_internetOk
            l_internetOk = self.internet_check()

            if self.m_browser is not None and self.m_browser.isLoggedIn() and l_internetOk:
                self.m_browser.mouse_obfuscate(l_sleep)
            else:
                time.sleep(l_sleep)

            l_internetOk = self.internet_check()

            if not l_internetOk:
                self.m_logger.warning('Internet connection off')
                continue

            if l_internetOk and not l_internetOkPrevious:
                self.m_logger.warning('Internet connection reestablished - refreshing page')
                self.m_browser.refresh_page()

            self.m_logger.info('>>>>>>>>>>>>>>> top >>>>>>>>>>>>>>>>>>>>>>>')

            if self.m_browser is None:
                # initial state: no browser driver yet
                self.m_logger.info('>> create browser')

                try:
                    self.m_browser = BrowserDriver()
                    self.m_logger.info('*** Browser Driver set-up complete')
                except Exception as e:
                    self.m_logger.warning('Unable to instantiate browser: ' + repr(e))
                    self.m_browser = None
                    raise
            elif self.m_browser is not None and not self.m_browser.isLoggedIn():
                # not logged in state (either at start or after a
                self.m_logger.info('>> log in')

                l_phantomId, l_phantomPwd, l_vpn = l_phantomList[l_phantomIndex]
                l_phantomIndex += 1
                if l_phantomIndex >= len(l_phantomList):
                    l_phantomIndex = 0

                self.m_logger.info('%%%%%%%%%% USER %%%%%%%%%%%%%%%')
                self.m_logger.info('User: {0}'.format(l_phantomId))
                self.m_logger.info('Pwd : {0}'.format(l_phantomPwd))
                self.m_logger.info('Vpn : {0}'.format(l_vpn))

                try:
                    self.m_browser.login_as_scrape(l_phantomId, l_phantomPwd, l_vpn)
                    self.m_logger.info('*** User Logged in')
                    self.log_phantom_connection(l_phantomId, l_vpn, l_phantomPwd, p_logIn=True, p_success=True)
                except Exception as e:
                    self.m_logger.warning('Unable to log in: ' + repr(e))
                    self.log_phantom_connection(l_phantomId, l_vpn, l_phantomPwd, p_logIn=True, p_success=False)
            elif self.m_browser is not None and self.m_browser.isLoggedIn() and self.m_browser.isStale():
                # stale browser situation
                self.m_logger.info('>> stale browser')

                # log out current user
                try:
                    self.m_browser.log_out()
                    self.m_logger.info('*** User Logged out')
                    self.log_phantom_connection(l_phantomId, '', '', p_logIn=False, p_success=True)
                    l_phantomId = ''
                except Exception as e:
                    self.m_logger.warning('Unable to log out: ' + repr(e))
                    self.log_phantom_connection(l_phantomId, '', '', p_logIn=False, p_success=False)

                    if self.internet_check():
                        sys.exit(0)
            else:
                # normal situation: browser is ok and a new story can be fetched
                self.m_logger.info('>> fetch one user feed')
                try:
                    t0 = time.perf_counter()
                    self.m_browser.go_random()
                    self.m_browser.get_fb_profile()
                    self.m_logger.info(
                        '*** User data download complete. Elapsed time: {0}'.format(time.perf_counter() - t0))
                except EX.TimeoutException as e:
                    self.m_logger.warning('Non fatal TimeoutException. Will try again.' + repr(e))
                except Exception as e:
                    if self.internet_check():
                        self.m_logger.warning('Serious exception - Raising: ' + repr(e))
                        raise
                    else:
                        self.m_logger.warning('Serious exception - but internet failure: ' + repr(e))


class RbsApp(EcAppCore):
    def __init__(self):
        super().__init__()

        self.m_logger = logging.getLogger('RbsApp')

        if EcAppParam.gcm_startGathering:
            self.m_background = RbsBackgroundTask(self.m_connectionPool)
        else:
            self.m_background = None

    def sessionList(self, p_requestHandler):
        l_conn = self.m_connectionPool.getconn('sessionList()')
        l_cursor = l_conn.cursor()
        try:
            l_cursor.execute("""
                select
                    A."ST_SESSION_ID"
                    , A."DT_CRE"
                    , B."N_STORY_COUNT"
                    , C."ST_NAME"
                    , C."ST_USER_ID"
                from "TB_SESSION" A
                    join (
                        select "ST_SESSION_ID", count(1) as "N_STORY_COUNT"
                        from "TB_STORY"
                        group by "ST_SESSION_ID"
                    ) B on A."ST_SESSION_ID" = B."ST_SESSION_ID"
                    join "TB_USER" C on C."ID_INTERNAL" = A."ID_INTERNAL"
                order by "DT_CRE" desc
                limit {0};
            """.format(EcAppParam.gcm_sessionDisplayCount))

            l_response = ''
            for l_sessionId, l_dtCre, l_count, l_userName, l_userId in l_cursor:
                l_response += """
                    <tr>
                        <td>{0}</td>
                        <td>{1}</td>
                        <td><a href="/session/{2}">{2}</a></td>
                        <td>{3}</td>
                        <td style="text-align: center;">{4}</td>
                    <tr/>
                """.format(
                    l_userName, l_userId, l_sessionId, l_dtCre.strftime('%d/%m/%Y %H:%M'), l_count)
        except Exception as e:
            self.m_logger.warning('TB_SESSION query failure: {0}'.format(repr(e)))
            raise

        l_cursor.close()
        self.m_connectionPool.putconn(l_conn)
        return """
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" >
            <head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
            </head>
            <body>
                <table>
                    <tr>
                        <td style="font-weight: bold;">ST_NAME</td>
                        <td style="font-weight: bold;">ST_USER_ID</td>
                        <td style="font-weight: bold;">ST_SESSION_ID</td>
                        <td style="font-weight: bold;">DT_CRE</td>
                        <td style="font-weight: bold;">N_STORY_COUNT</td>
                    <tr/>
                    {0}
                </table>
            </body>
            </html>
        """.format(l_response)

    def oneSession(self, p_requestHandler):
        l_sessionId = re.sub('/session/', '', p_requestHandler.path)
        self.m_logger.info('l_sessionId: {0}'.format(l_sessionId))
        l_conn = self.m_connectionPool.getconn('oneSession()')
        l_cursor = l_conn.cursor()
        try:
            l_cursor.execute("""
                        select *
                        from "TB_STORY"
                        where "ST_SESSION_ID" = '{0}'
                        order by "ID_STORY";
                    """.format(l_sessionId))

            l_response = ''
            for l_idStory, l_sessionId, l_dtStory, l_dtCre, l_stType, \
                l_json, l_likes, l_comments, l_shares in l_cursor:

                l_story = json.loads(l_json)
                l_imgCount = len(l_story['images'])
                l_text = l_story['text'][:50]
                if len(l_text) != len(l_story['text']):
                    l_text += '...'
                l_textQ = l_story['text_quoted'][:50]
                if len(l_textQ) != len(l_story['text_quoted']):
                    l_textQ += '...'
                if len(l_text + l_textQ) > 0:
                    l_displayText = l_text + '■■■' + l_textQ
                else:
                    l_displayText = ''

                l_response += """
                            <tr>
                                <td style="padding-right:1em;"><a href="/story/{0}">{0}</a></td>
                                <td style="padding-right:1em;">{1}</td>
                                <td style="padding-right:1em;">{2}</td>
                                <td style="padding-right:1em;">{3}</td>
                                <td style="padding-right:1em;">{4}</td>
                                <td style="padding-right:1em;">{5}</td>
                                <td style="padding-right:1em;">{6}</td>
                                <td style="padding-right:1em;">{7}</td>
                                <td>{8}</td>
                            <tr/>
                        """.format(
                    l_idStory,
                    l_dtStory.strftime('%d/%m/%Y&nbsp;%H:%M') if l_dtStory is not None else 'NULL',
                    l_dtCre.strftime('%d/%m/%Y&nbsp;%H:%M'),
                    l_stType, l_likes, l_comments, l_shares, l_imgCount, l_displayText
                )
        except Exception as e:
            self.m_logger.warning('TB_STORY query failure: {0}'.format(repr(e)))
            raise

        l_cursor.close()
        self.m_connectionPool.putconn(l_conn)
        return """
                    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" >
                    <head>
                        <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
                    </head>
                    <body>
                        <h1>Session: {0}</h1>
                        <table>
                            <tr>
                                <td style="font-weight: bold; padding-right:1em;">ID_STORY</td>
                                <td style="font-weight: bold; padding-right:1em;">DT_STORY</td>
                                <td style="font-weight: bold; padding-right:1em;">DT_CRE</td>
                                <td style="font-weight: bold; padding-right:1em;">ST_TYPE</td>
                                <td style="font-weight: bold; padding-right:1em; font-size:60%;">N_LIKES</td>
                                <td style="font-weight: bold; padding-right:1em; font-size:60%;">N_COMMENTS</td>
                                <td style="font-weight: bold; padding-right:1em; font-size:60%;">N_SHARES</td>
                                <td style="font-weight: bold; padding-right:1em; font-size:60%;">Img.&nbsp;#</td>
                                <td style="font-weight: bold;">Text■■■Quoted text</td>
                            <tr/>
                            {1}
                        </table>
                    </body>
                    </html>
                """.format(l_sessionId, l_response)

    def oneStory(self, p_requestHandler):
        l_storyId = re.sub('/story/', '', p_requestHandler.path)
        self.m_logger.info('l_storyId: {0}'.format(l_storyId))
        l_conn = self.m_connectionPool.getconn('oneStory()')
        l_cursor = l_conn.cursor()
        try:
            l_cursor.execute("""
                                select *
                                from "TB_STORY"
                                where "ID_STORY" = {0};
                            """.format(l_storyId))

            l_response = ''
            for l_idStory, l_sessionId, l_dtStory, l_dtCre, \
                l_stType, l_json, l_likes, l_comments, l_shares in l_cursor:

                l_story = json.loads(l_json)

                #<img src="data:image/jpeg;base64,
                l_imgDisplay = ''
                for l_imgB64 in l_story['images']:
                    l_imgDisplay += """
                        <img src="data:image/png;base64,{0}">
                    """.format(l_imgB64)

                l_html_disp = l_story['html'] if 'html' in l_story.keys() else ''
                l_html_disp = re.sub(r'<', r'&lt;', l_html_disp)
                l_html_disp = re.sub(r'>', r'&gt;&#8203;', l_html_disp)
                #l_html_disp = re.sub(r'>', r'&gt; ', l_html_disp)

                l_likes = ''
                if 'likes' in l_story.keys():
                    l_likes = repr(l_story['likes'])

                l_response += """
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">ID_STORY</td>
                        <td>{0}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Text:</td>
                        <td>{1}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Text&nbsp;quoted:</td>
                        <td>{2}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Type:</td>
                        <td>{3}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">From:</td>
                        <td>{4}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Date:</td>
                        <td>{5}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Quoted&nbsp;date(s):</td>
                        <td>{6}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Shared&nbsp;Item(s):</td>
                        <td>{7}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Sponsored:</td>
                        <td>{8}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">With:</td>
                        <td>{9}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Likes:</td>
                        <td>{10}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Comments:</td>
                        <td>[{11}] {12}</td>
                    <tr/>
                    <tr>
                        <td style="padding-right:1em; font-weight: bold; vertical-align: top;">Shares:</td>
                        <td>{13}</td>
                    <tr/>
                    <tr>
                        <td colspan="2">{14}</td>
                    <tr/>
                    <tr>
                        <td colspan="2" style="word-wrap:break-word;">{15}</td>
                    <tr/>
                """.format(
                    l_idStory
                    , l_story['text']
                    , l_story['text_quoted']
                    , l_story['type']
                    , repr(l_story['from_list'])
                    , l_story['date']
                    , repr(l_story['date_quoted'])
                    , repr(l_story['shared'])
                    , 'Yes' if l_story['sponsored'] else 'No'
                    , 'Yes' if l_story['with'] else 'No'
                    , l_likes
                    , l_comments, repr(l_story['comments']) if 'comments' in l_story.keys() else ''
                    , l_story['shares'] if 'shares' in l_story.keys() else ''
                    , l_imgDisplay
                    , l_html_disp
                )
        except Exception as e:
            self.m_logger.warning('TB_STORY query failure: {0}'.format(repr(e)))
            raise

        l_cursor.close()
        self.m_connectionPool.putconn(l_conn)
        return """
                <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" >
                <head>
                    <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
                </head>
                <body style="font-family: sans-serif;">
                    <table>{0}</table>
                </body>
                </html>
            """.format(l_response)

    def get_responseGet(self, p_requestHandler):
        # completely useless line. Only there to avoid PEP-8 pedantic complaint
        self.m_rq = p_requestHandler

        self.m_logger.info('request: ' + p_requestHandler.path)
        if p_requestHandler.path == '/test':
            return """
                <html>
                    <head></head>
                    <body>
                        <p style="color: green;">Ok, we are in business ... </p>
                    </body>
                </html>
            """
        elif re.search('^/session/', p_requestHandler.path):
            return self.oneSession(p_requestHandler)
        elif re.search('^/story/', p_requestHandler.path):
            return self.oneStory(p_requestHandler)
        else:
            return self.sessionList(p_requestHandler)

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

        EcLogger.root_logger().info('locale (LC_CTYPE) : {0}'.format(locale.getlocale(locale.LC_CTYPE)))
        EcLogger.root_logger().info('locale (LC_TIME)  : {0}'.format(locale.getlocale(locale.LC_TIME)))

        l_locale, l_encoding = locale.getlocale(locale.LC_TIME)
        if l_locale is None:
            locale.setlocale(locale.LC_TIME, locale.getlocale(locale.LC_CTYPE))

        EcLogger.root_logger().info('gcm_appName       : ' + EcAppParam.gcm_appName)
        EcLogger.root_logger().info('gcm_appVersion    : ' + EcAppParam.gcm_appVersion)
        EcLogger.root_logger().info('gcm_appTitle      : ' + EcAppParam.gcm_appTitle)
        EcLogger.root_logger().info('locale (LC_CTYPE) : {0}'.format(locale.getlocale(locale.LC_CTYPE)))
        EcLogger.root_logger().info('locale (LC_TIME)  : {0}'.format(locale.getlocale(locale.LC_TIME)))

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
