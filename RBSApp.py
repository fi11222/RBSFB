#!/usr/bin/python3
# -*- coding: utf-8 -*-

from ec_app_core import *
from ec_request_handler import *

from rbs_fb_profile import *
from rbs_fb_bulk import *

from wrapvpn import OpenvpnWrapper, OpenVpnFailure

import json
import random
import sys
import locale
import pytz
from socketserver import ThreadingMixIn

__author__ = 'Pavan Mahalingam'


class RbsBackgroundTask(threading.Thread):
    """
    Thread class performing the continuous batch download of Facebook stories
    """
    def __init__(self, p_pool):
        """
        Sets up class variable and launches the thread.
        
        :param p_pool: :any:`EcConnectionPool` passed from the main :any:`RbsApp` application class.
        """
        super().__init__(daemon=True)

        #: Local logger
        self.m_logger = logging.getLogger('RbsBackgroundTask')

        #: The browser driver class (:any:`BrowserDriver`)
        self.m_browser = None

        #: Bulk Downloader
        self.m_bulk = None

        #: Connection pool
        self.m_pool = p_pool

        # starts the thread
        self.name = 'B'
        self.start()

    def internet_check(self):
        """
        Presence of internet connection verification. Uses :any:`OpenvpnWrapper.getOwnIp`
        
        :return: `True` if internet can be reached. `False` otherwise. 
        """
        try:
            l_ip = OpenvpnWrapper.getOwnIp()

            # if this point is reached --> the internet connection is probably ok
            self.m_logger.info('Own IP: {0}'.format(l_ip))
            l_internetOk = True
        except OpenVpnFailure as e1:
            self.m_logger.warning('Own IP failure: ' + repr(e1))
            l_internetOk = False

        return l_internetOk

    def log_phantom_connection(self, p_phantom, p_vpn, p_password, p_logIn=True, p_success=True):
        """
        Logs a phantom login or logout operation to `TB_EC_MSG` and `TB_PHANTOM_LOGIN`.
        
        :param p_phantom: Phantom ID (e-mail address)
        :param p_vpn: Openvpn configuration filename (or `None`, if logout or no vpn for this phantom)
        :param p_password: Phantom's password (or `None`, if logout)
        :param p_logIn: True --> Login, False --> Logout
        :param p_success: True --> Success, False --> Failure
        :return: Nothing.
        """
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
        except Exception as e1:
            self.m_logger.warning('TB_EC_MSG insert failure: {0}'.format(repr(e1)))
            raise

        # Log message in TB_PHANTOM_LOGIN
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
        except Exception as e1:
            self.m_logger.warning('TB_PHANTOM_LOGIN insert failure: {0}'.format(repr(e1)))
            raise

        l_cursor.close()
        self.m_pool.putconn(l_conn)

    def run(self):
        """
        Actual continuous FB stories download loop, executed by the class thread. Perform the following tasks,
        in an infinite loop:
        
        * Create a :any:`BrowserDriver` instance if none exists (only once).
        * Logs in a new phantom if none logged in.
        * Logs out if the browser driver is stale.
        * Downloads a random user profile (taken from `TB_USER`).
        
        On each loop, there is a random delay (between :any:`EcAppParam.gcm_bkgMinDelay` and
        :any:`EcAppParam.gcm_bkgMaxDelay`) which is performed while doing random mouse movements if
        the browser driver is there and a phantom is logged in, or as a simple `time.sleep()` otherwise.
        
        The loop also checks for the presence of the internet connection and suspends operation if not.
        
        :return: Nothing 
        """
        l_phantomList = [
            ('karim.elmoulaid@gmail.com', '15Eyyaka', 'Canada.Quebec.Montreal_LOC2S1.TCP.ovpn', 12, 3),
            # ('kabeer.burnahuddin@gmail.com', '15Eyyaka', 'India.Maharashtra.Mumbai.UDP.ovpn', 2, 17),
            ('kabeer.burnahuddin@gmail.com', '15Eyyaka', None, 2, 17),
            ('nicolas.reimen@gmail.com', 'murugan!', None, 2, 17),
            ('yahia.almasoodi@yahoo.com', '15Eyyaka', 'UnitedArabEmirates.Dubai_LOC1S1.TCP.ovpn', 4, 19),
            ('bulk', None, None, 20, 1)
            # ('bulk', None, None, 1, 24)
        ]

        l_bulk_id = 'nicolas.reimen@gmail.com'
        l_bulk_pass = 'murugan!'

        l_phantomIndex = EcAppParam.gcm_startPhantomNo

        l_internetOk = True
        l_phantomId = ''
        while True:
            # Internet connection test
            l_internetOkPrevious = l_internetOk
            l_internetOk = self.internet_check()

            # random delay
            l_sleep = random.randint(EcAppParam.gcm_bkgMinDelay, EcAppParam.gcm_bkgMaxDelay)
            self.m_logger.info('[{0}] Waiting for {1} seconds'.format(l_phantomId, l_sleep))
            if self.m_browser is not None and self.m_browser.isLoggedIn() and l_internetOk:
                # executed with random mouse movements if possible
                self.m_browser.mouse_obfuscate(l_sleep)
            else:
                time.sleep(l_sleep)

            self.m_logger.info('>>>>>>>>>>>>>>> top >>>>>>>>>>>>>>>>>>>>>>>')
            l_internetOk = self.internet_check()

            # if no internet connection, suspend operation
            if not l_internetOk:
                self.m_logger.warning('Internet connection off')
                continue

            # if internet connection just reestablished, refresh page.
            if l_internetOk and not l_internetOkPrevious:
                self.m_logger.warning('Internet connection reestablished - refreshing page')
                self.m_browser.refresh_page()

            # List of possible actions, depending on conditions:
            if self.m_browser is None:
                # 1. Initial state: no browser driver yet
                self.m_logger.info('>> Create browser driver')

                try:
                    self.m_browser = BrowserDriver()
                    # instantiate the bulk downloader --> starts the OCR thread
                    self.m_bulk = BulkDownloader(self.m_browser, self.m_pool, l_bulk_id, l_bulk_pass)
                    self.m_logger.info('*** Browser Driver set-up complete')
                except Exception as e:
                    self.m_logger.warning('Unable to instantiate browser: ' + repr(e))
                    self.m_browser = None
                    raise
            elif self.m_browser is not None and not self.m_browser.isLoggedIn():
                # 2. Not logged in state (either at start or after a stale-generated logout)
                # --> Login
                self.m_logger.info('>> login')

                l_phantomId, l_phantomPwd, l_vpn, l_morning, l_evening = l_phantomList[l_phantomIndex]
                l_phantomIndex += 1
                if l_phantomIndex >= len(l_phantomList):
                    l_phantomIndex = 0

                # test appropriate time ?
                l_now = datetime.datetime.now(tz=pytz.utc)
                self.m_logger.info('Now: {0}'.format(l_now.strftime('%d/%m/%Y %H:%M')))
                if l_morning < l_evening:
                    l_morning_date = l_now + datetime.timedelta(hours=l_morning-l_now.hour, minutes=-l_now.minute)
                    l_evening_date = l_now + datetime.timedelta(hours=l_evening-l_now.hour, minutes=-l_now.minute)
                    l_in_range = (l_now >= l_morning_date and l_now <= l_evening_date)

                    self.m_logger.info('Bracket: [{0} - {1}]'.format(
                        l_morning_date.strftime('%d/%m/%Y %H:%M'), l_evening_date.strftime('%d/%m/%Y %H:%M')))
                else:
                    l_morning_date_m = l_now + datetime.timedelta(hours=-24+l_morning-l_now.hour, minutes=-l_now.minute)
                    l_evening_date_m = l_now + datetime.timedelta(hours=l_evening-l_now.hour, minutes=-l_now.minute)
                    self.m_logger.info('Bracket (day-1) : [{0} - {1}]'.format(
                        l_morning_date_m.strftime('%d/%m/%Y %H:%M'), l_evening_date_m.strftime('%d/%m/%Y %H:%M')))

                    l_morning_date_p = l_now + datetime.timedelta(hours=l_morning-l_now.hour, minutes=-l_now.minute)
                    l_evening_date_p = l_now + datetime.timedelta(hours=l_evening-l_now.hour+24, minutes=-l_now.minute)
                    self.m_logger.info('Bracket (day+1) : [{0} - {1}]'.format(
                        l_morning_date_p.strftime('%d/%m/%Y %H:%M'), l_evening_date_p.strftime('%d/%m/%Y %H:%M')))

                    l_in_range = (l_morning_date_m <= l_now and l_now < l_evening_date_m) or \
                                 (l_morning_date_p <= l_now and l_now < l_evening_date_p)

                if not l_in_range:
                    self.m_logger.info('Not in range')
                    continue

                self.m_logger.info('%%%%%%%%%% USER %%%%%%%%%%%%%%%')
                self.m_logger.info('User: {0}'.format(l_phantomId))
                self.m_logger.info('Pwd : {0}'.format(l_phantomPwd))
                self.m_logger.info('Vpn : {0}'.format(l_vpn))

                if l_phantomId == 'bulk':
                    self.log_phantom_connection(l_phantomId, l_vpn, l_phantomPwd, p_logIn=True, p_success=True)
                    self.m_bulk.bulk_download()
                    self.log_phantom_connection(l_phantomId, None, None, p_logIn=False, p_success=True)
                    sys.exit(0)
                    # continue

                try:
                    self.m_browser.login_as_scrape(l_phantomId, l_phantomPwd, l_vpn)
                    self.m_logger.info('*** User Logged in')
                    self.log_phantom_connection(l_phantomId, l_vpn, l_phantomPwd, p_logIn=True, p_success=True)
                except Exception as e:
                    self.m_logger.warning('Unable to log in: ' + repr(e))
                    self.log_phantom_connection(l_phantomId, l_vpn, l_phantomPwd, p_logIn=True, p_success=False)
            elif self.m_browser is not None and self.m_browser.isLoggedIn() and self.m_browser.isStale():
                # 3. Stale browser situation --> Logout
                self.m_logger.info('>> Stale browser --> user logout')

                # log out current user
                try:
                    self.m_browser.log_out()
                    self.m_logger.info('*** User Logged out')
                    self.log_phantom_connection(l_phantomId, None, None, p_logIn=False, p_success=True)
                    l_phantomId = ''
                except Exception as e:
                    self.m_logger.warning('Unable to log out: ' + repr(e))
                    self.log_phantom_connection(l_phantomId, None, None, p_logIn=False, p_success=False)

                    # if there was an internet connection and the logout process failed: stop everything for analysis.
                    if self.internet_check():
                        sys.exit(0)
            else:
                # 4. Ordinary situation: browser is ok and a new story can be fetched
                self.m_logger.info('>> fetch one random user feed')
                try:
                    t0 = time.perf_counter()
                    self.m_browser.go_random()

                    l_downloader = ProfileDownloader(self.m_browser)
                    l_downloader.get_fb_profile()

                    # self.m_browser.go_to_id(None, 'ArmyAnonymous/', None)
                    # l_downloader.get_fb_profile(p_feedType='Page')
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

                # sys.exit(0)


class RbsApp(EcAppCore):
    """
    Main application class. Subclass of generic EC app class :any:`EcAppCore`
    
    This class perform two separate tasks:
    
    * Launching the thread performing the continuous downloading of FB stories (:any:`RbsBackgroundTask`)
    * Providing a response to the HTTP request for the display of results through the appropriate methods inherited
      from the base :any:`EcAppCore` class.
    """
    def __init__(self):
        super().__init__()

        #: local logger
        self.m_logger = logging.getLogger('RbsApp')

        if EcAppParam.gcm_startGathering:
            #: Background task performing continuous download of FB stories
            self.m_background = RbsBackgroundTask(self.m_connectionPool)
        else:
            self.m_background = None

    def get_responseGet(self, p_requestHandler):
        """
        Build the appropriate response based on the data provided by the request handler given in parameter.
        
        :param p_requestHandler: an :any:`EcRequestHandler` instance providing the HTTP request parameters.
        :return: A string containing the HTML of the response
        """
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
            return self.sessionList()

    def sessionList(self):
        """
        Build the response for the "list of sessions" screen. No parameters necessary.
        
        :return: The list of sessions HTML. 
        """
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
        """
        Build the HTML for an individual session screen, i.e. the list of stories retrieved from that session.
        
        :param p_requestHandler: The :any:`EcRequestHandler` instance providing the session ID parameter. 
        :return: The Session HTML.
        """
        # the session ID is the last member of the URL
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
        """
        Build the HTML for an individual story screen.

        :param p_requestHandler: The :any:`EcRequestHandler` instance providing the story ID parameter. 
        :return: The story HTML.
        """
        # the story ID is the last member of the URL
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

                # <img src="data:image/jpeg;base64,
                l_imgDisplay = ''
                for l_imgB64 in l_story['images']:
                    l_imgDisplay += """
                        <img src="data:image/png;base64,{0}">
                    """.format(l_imgB64)

                l_html_disp = l_story['html'] if 'html' in l_story.keys() else ''
                l_html_disp = re.sub(r'<', r'&lt;', l_html_disp)
                l_html_disp = re.sub(r'>', r'&gt;&#8203;', l_html_disp)
                # l_html_disp = re.sub(r'>', r'&gt; ', l_html_disp)

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
                    l_idStory,
                    l_story['text'],
                    l_story['text_quoted'],
                    l_story['type'],
                    repr(l_story['from_list']),
                    l_story['date'],
                    repr(l_story['date_quoted']),
                    repr(l_story['shared']),
                    'Yes' if l_story['sponsored'] else 'No',
                    'Yes' if l_story['with'] else 'No',
                    l_likes,
                    l_comments, repr(l_story['comments']) if 'comments' in l_story.keys() else '',
                    l_story['shares'] if 'shares' in l_story.keys() else '',
                    l_imgDisplay,
                    l_html_disp
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
        #. Test the availability of the database connection.
        #. Initialises the logging system (:any:`EcLogger.logInit`)
        #. Instantiates the application class (:any:`RbsApp`). This launches the background stories-downloading
           thread.
        #. Initialises the request handler class (:any:`EcRequestHandler.init_class`), passing it a handle 
           on the application class.
        #. Initialises the vpn wrapper class (:any:`OpenvpnWrapper.init_class`)
        #. Instantiates the standard Python HTTP server class (:any:`ThreadedHTTPServer`). The request handler
           class will be instantiated by this class and a handle to it is therefore passed to it.
        #. Set up the appropriate locale (for proper date format handling)
        #. Launches the server (:any:`l_httpd.serve_forever`)
        
        The dependencies between the main application classes is as follows:

        HTTP server: one instance "running forever"
            ↳ request handler: one instance for each HTTP request
                ↳ application: one instance created at startup. Response building methods called by request handler
                    ↳ Background threads:
                        * Health check: launched by application base class (:any:`EcAppCore`)
                        * Stories downloading: launched by app specific subclass (:any:`RbsApp`)
        """
        print('EC server starting ...')

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
        EcLogger.root_logger().info('locale (LC_TIME)  : {0}'.format(locale.getlocale(locale.LC_TIME)))

        EcLogger.root_logger().info('gcm_appName       : ' + EcAppParam.gcm_appName)
        EcLogger.root_logger().info('gcm_appVersion    : ' + EcAppParam.gcm_appVersion)
        EcLogger.root_logger().info('gcm_appTitle      : ' + EcAppParam.gcm_appTitle)

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
