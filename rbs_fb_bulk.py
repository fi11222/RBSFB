#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json

from rbs_fb_connect import *

__author__ = 'Pavan Mahalingam'

class BulkDownloaderException(Exception):
    def __init__(self, p_msg):
        self.m_msg = p_msg

class BulkDownloader:
    """
    Bogus class used to isolate the bulk downloading (FB API) features.
    """
    def __init__(self, p_browser_driver, p_pool):
        # Local copy of the browser Driver
        self.m_browserDriver = p_browser_driver

        #: Connection pool
        self.m_pool = p_pool

        # instantiates class logger
        self.m_logger = logging.getLogger('BulkDownloader')

        # number of times an object store has been attempted
        self.m_objectStoreAttempts = 0

        # number of objects actually stored
        self.m_objectStored = 0

        self.m_postRetrieved = 0
        self.m_commentRetrieved = 0

        # number of requests performed
        self.m_FBRequestCount = 0

    def bulk_download(self):
        """
        Performs the bulk-downloading tasks.
        
        :return: Nothing
        """

        self.m_browserDriver.get_fb_token()
        self.getPages()

    # calls Facebook's HTTP API and traps errors if any
    def performRequest(self, p_request):
        l_request = p_request

        l_finished = False
        l_response = None

        # print('g_FBRequestCount:', g_FBRequestCount)

        # replace access token with the latest (this is necessary because
        # some old tokens may remain in the 'next' parameters kept from previous requests)
        l_request = self.m_browserDriver.freshen_token(l_request)

        # request new token every G_TOKEN_LIFESPAN API requests
        if self.m_FBRequestCount > 0 and self.m_FBRequestCount % EcAppParam.gcm_token_lifespan == 0:
            l_request = self.m_browserDriver.renew_token_and_request(l_request)

        self.m_FBRequestCount += 1

        l_errCount = 0
        while not l_finished:
            try:
                l_response = urllib.request.urlopen(l_request, timeout=10).read().decode('utf-8').strip()
                l_finished = True

            except urllib.error.HTTPError as e:
                l_headersDict = dict(e.headers.items())

                self.m_logger.warning('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n{10} {11}\n{12} {13}\n'.format(
                    'l_errCount     :', l_errCount,
                    'Request Problem:', repr(e),
                    '   Code        :', e.code,
                    '   Errno       :', e.errno,
                    '   Headers     :', l_headersDict,
                    '   Message     :', e.msg,
                    'p_request      :', p_request
                ))

                # Facebook error
                if 'WWW-Authenticate' in l_headersDict.keys():
                    l_FBMessage = l_headersDict['WWW-Authenticate']

                    # Request limit reached --> wait G_WAIT_FB s and retry
                    if re.search(r'\(#17\) User request limit reached', l_FBMessage):
                        l_wait = EcAppParam.gcm_wait_fb
                        self.m_logger.info('{0} {1}\n{2}\n'.format(
                            'FB request limit msg: ', l_FBMessage,
                            'Waiting for {0} seconds'.format(l_wait)
                        ))

                        l_sleepPeriod = 5 * 60
                        for i in range(int(l_wait / l_sleepPeriod)):
                            time.sleep(l_sleepPeriod)
                            l_request = self.m_browserDriver.renew_token_and_request(l_request)

                    # Unknown FB error --> wait 10 s and retry 3 times max then return empty result
                    if re.search(r'An unexpected error has occurred', l_FBMessage) \
                            or re.search(r'An unknown error has occurred', l_FBMessage):
                        if l_errCount < 3:
                            l_wait = 10
                            self.m_logger.info('{0} {1}\n{2}\n'.format(
                                'FB unknown error: ', l_FBMessage,
                                'Waiting for {0} seconds'.format(l_wait)
                            ))

                            time.sleep(l_wait)
                            l_request = self.m_browserDriver.renew_token_and_request(l_request)
                        else:
                            l_response = '{"data": []}'

                            self.m_logger.info('{0} {1}\n{2}\n'.format(
                                'FB unknown error: ', l_FBMessage,
                                'Returned: {0}'.format(l_response)
                            ))

                            l_finished = True

                    # Session expired ---> nothing to do
                    elif re.search(r'Session has expired', l_FBMessage):
                        self.m_logger.info('{0} {1}\n'.format(
                            'FB session expiry msg: ', l_FBMessage))

                        sys.exit()

                    # Unsupported get request ---> return empty data and abandon request attempt
                    elif re.search(r'Unsupported get request', l_FBMessage):
                        l_response = '{"data": []}'

                        self.m_logger.info('{0} {1}\n{2}\n'.format(
                            'FB unsupported get msg: ', l_FBMessage,
                            'Returned: {0}'.format(l_response)
                        ))

                        l_finished = True

                    # Other FB error
                    else:
                        self.m_logger.info('{0} {1}\n'.format(
                            'FB msg: ', l_FBMessage
                        ))

                        sys.exit()

                # Non FB HTTPError
                else:
                    l_wait = self.getWait(l_errCount)
                    self.m_logger.info('Waiting for {0} seconds'.format(l_wait))

                    time.sleep(l_wait)
                    if l_wait > 60 * 15:
                        l_request = self.m_browserDriver.renew_token_and_request(l_request)

                l_errCount += 1

            except urllib.error.URLError as e:
                self.m_logger.warning('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n'.format(
                    'l_errCount     :', l_errCount,
                    'Request Problem:', repr(e),
                    '   Errno       :', e.errno,
                    '   Message     :', e.reason,
                    'p_request      :', p_request
                ))

                time.sleep(1)

                l_errCount += 1

            except Exception as e:
                self.m_logger.warning('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n'.format(
                    'l_errCount     :', l_errCount,
                    'Request Problem:', repr(e),
                    '   Message     :', e.args,
                    'p_request      :', p_request
                ))

                time.sleep(1)

                l_errCount += 1

        return l_response

    def getWait(self, p_errorCount):
        if p_errorCount < 3:
            return 5
        elif p_errorCount < 6:
            return 30
        elif p_errorCount < 9:
            return 60 * 2
        elif p_errorCount < 12:
            return 60 * 5
        elif p_errorCount < 15:
            return 60 * 15
        elif p_errorCount < 18:
            return 60 * 30
        elif p_errorCount < 21:
            return 60 * 60
        else:
            self.m_logger.warning('Too many errors: {0}'.format(p_errorCount))
            raise BulkDownloaderException('Too many errors: {0}'.format(p_errorCount))

    def getPages(self):
        # list of likes from user --> starting point
        l_request = 'https://graph.facebook.com/{0}/me/likes?access_token={1}'.format(
            EcAppParam.gcm_api_version, self.m_browserDriver.m_token_api)
        l_response = self.performRequest(l_request)

        self.m_logger.info('l_request:' + l_request)

        # each like is a page
        l_responseData = json.loads(l_response)
        l_finished = False
        while not l_finished:
            for l_liked in l_responseData['data']:
                l_pageId = l_liked['id']
                l_pageName = l_liked['name']
                self.m_logger.info('id   :' + l_pageId)
                self.m_logger.info('name :' + l_pageName)

                # store page information
                self.storeObject(
                    p_padding='',
                    p_type='Page',
                    p_FBType='Page',
                    p_id=l_pageId,
                    p_parentId='',
                    p_pageId='',
                    p_postId='',
                    p_date='',
                    p_likeCount=0,
                    p_shareCount=0,
                    p_name=l_pageName
                )

                # get posts from the page
                # getPostsFromPage(l_pageId)

            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                l_request = l_responseData['paging']['next']
                l_response = self.performRequest(l_request)

                l_responseData = json.loads(l_response)
            else:
                l_finished = True

    def storeObject(self, p_padding, p_type, p_date,
                    p_id, p_parentId, p_pageId, p_postId,
                    p_FBType, p_shareCount, p_likeCount,
                    p_name='',
                    p_caption='',
                    p_desc='',
                    p_story='',
                    p_message='',
                    p_link='',
                    p_picture='',
                    p_place='',
                    p_source='',
                    p_userId='',
                    p_raw=''):


        self.m_objectStoreAttempts += 1

        l_stored = False

        # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
        l_date = re.sub('T', ' ', p_date)
        l_date = re.sub(r'\+\d+$', '', l_date).strip()

        if len(l_date) == 0:
            l_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        l_conn = self.m_pool.getconn('BulkDownloader.storeObject()')
        l_cursor = l_conn.cursor()

        try:
            l_cursor.execute("""
                INSERT INTO "TB_OBJ"(
                    "ID"
                    ,"ID_FATHER"
                    ,"ID_PAGE"
                    ,"ID_POST"
                    ,"DT_CRE"
                    ,"ST_TYPE"
                    ,"ST_FB_TYPE"
                    ,"TX_NAME"
                    ,"TX_CAPTION"
                    ,"TX_DESCRIPTION"
                    ,"TX_STORY"
                    ,"TX_MESSAGE"
                    ,"ID_USER"
                    ,"N_LIKES"
                    ,"N_SHARES"
                    ,"TX_PLACE")
                VALUES(
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s) 
            """, (
                p_id,
                p_parentId,
                p_pageId,
                p_postId,
                l_date,
                p_type,
                p_FBType,
                p_name,
                p_caption,
                p_desc,
                p_story,
                p_message,
                p_userId,
                p_likeCount,
                p_shareCount,
                p_place
                )
            )

            self.m_objectStored += 1
            l_conn.commit()
            l_stored = True
        except psycopg2.IntegrityError as e:
            self.m_logger.info('{0}Object already in TB_OBJ [{1}]'.format(p_padding, repr(e)))
            l_conn.rollback()
        except Exception as e:
            self.m_logger.warning('TB_OBJ Unknown Exception: {0}/{1}'.format(repr(e), l_cursor.query))
            raise BulkDownloaderException('TB_OBJ Unknown Exception: {0}'.format(repr(e)))

        # store media if any
        if len(p_link + p_picture + p_raw + p_source) > 0:
            l_cursor = l_conn.cursor()
            try:
                l_cursor.execute("""
                        INSERT INTO "TB_MEDIA"("ID_OWNER","TX_URL_LINK","TX_SRC_PICTURE","TX_RAW")
                        VALUES(%s, %s, %s, %s)
                    """, (
                        p_id,
                        p_link,
                        # p_source is for videos, p_picture for images
                        p_source if len(p_source) > 0 else p_picture,
                        p_raw
                    )
                )
                l_conn.commit()
                l_stored = True
            except psycopg2.IntegrityError as e:
                self.m_logger.info('{0}Object already in TB_MEDIA[{1}]'.format(p_padding, repr(e)))
                l_conn.rollback()
            except Exception as e:
                self.m_logger.info('TB_MEDIA Unknown Exception: {0}/{1}'.format(repr(e), l_cursor.query))
                raise BulkDownloaderException('TB_MEDIA Unknown Exception: {0}'.format(repr(e)))

            l_cursor.close()

        self.m_pool.putconn(l_conn)

        self.m_logger.info(
            '{0}Object counts: {1} attempts / {2} stored / {3} posts retrieved / {4} comments retrieved'.format(
            p_padding, self.m_objectStoreAttempts, self.m_objectStored, self.m_postRetrieved, self.m_commentRetrieved))

        return l_stored

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB scraping web service for ROAD B SCORE                   |')
    print('|                                                            |')
    print('| POST request sending test client                           |')
    print('|                                                            |')
    print('| v. 1.0 - 28/02/2017                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

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
            l_connect0 = psycopg2.connect(
                host=EcAppParam.gcm_dbServer,
                database=EcAppParam.gcm_dbDatabase,
                user=EcAppParam.gcm_dbUser,
                password=EcAppParam.gcm_dbPassword
            )

            l_connect0.close()
            break
        except psycopg2.Error as e0:
            EcMailer.send_mail('WAITING: No PostgreSQL yet ...', repr(e0))
            time.sleep(1)
            continue

    # logging system init
    try:
        EcLogger.log_init()
    except Exception as e0:
        EcMailer.send_mail('Failed to initialize EcLogger', repr(e0))


    # l_phantomId0 = 'nicolas.reimen@gmail.com'
    # l_phantomPwd0 = 'murugan!'
    l_phantomId0, l_phantomPwd0 = 'kabir.abdulhami@gmail.com', '12Alhamdulillah',
    # l_vpn = 'India.Maharashtra.Mumbai.TCP.ovpn'
    l_vpn0 = None

    l_driver = BrowserDriver()
    l_pool = EcConnectionPool.get_new()

    l_driver.m_user_api = l_phantomId0
    l_driver.m_pass_api = l_phantomPwd0

    l_downloader = BulkDownloader(l_driver, l_pool)
    l_downloader.bulk_download()

    if EcAppParam.gcm_headless:
        l_driver.close()