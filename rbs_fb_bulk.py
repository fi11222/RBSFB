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

        # current page being downloaded
        self.m_page = None

    def bulk_download(self):
        """
        Performs the bulk-downloading tasks.
        
        :return: Nothing
        """

        self.m_browserDriver.get_fb_token()
        self.getPages()

        l_conn = self.m_pool.getconn('BulkDownloader.bulk_download()')
        l_cursor = l_conn.cursor()

        try:
            l_cursor.execute("""
                select "ID", "TX_NAME" from "TB_PAGES";
            """)
        except Exception as e:
            self.m_logger.warning('Error selecting from TB_PAGES: {0}/{1}'.format(repr(e), l_cursor.query))

        for l_id, l_name in l_cursor:
            self.m_logger.info('$$$$$$$$$ [{0}] $$$$$$$$$$'.format(l_name))
            self.m_page = l_name
            self.getPostsFromPage(l_id)

        l_cursor.close()
        self.m_pool.putconn(l_conn)

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

                self.m_logger.warning(
                    ('HTTPError (Non Critical)\n{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}' +
                     '\n{8} {9}\n{10} {11}\n{12} {13}').format(
                        'l_errCount     :', l_errCount,
                        'Request Problem:', repr(e),
                        '   Code        :', e.code,
                        '   Errno       :', e.errno,
                        '   Headers     :', l_headersDict,
                        '   Message     :', e.msg,
                        'p_request      :', p_request
                    )
                )

                # Facebook error
                if 'WWW-Authenticate' in l_headersDict.keys():
                    l_FBMessage = l_headersDict['WWW-Authenticate']

                    # Request limit reached --> wait G_WAIT_FB s and retry
                    if re.search(r'\(#17\) User request limit reached', l_FBMessage):
                        l_wait = EcAppParam.gcm_wait_fb
                        self.m_logger.info('FB request limit msg: {0} --> Waiting for {1} seconds'.format(
                            l_FBMessage, l_wait))

                        l_sleepPeriod = 5 * 60
                        for i in range(int(l_wait / l_sleepPeriod)):
                            time.sleep(l_sleepPeriod)
                            l_request = self.m_browserDriver.renew_token_and_request(l_request)

                    # Unknown FB error --> wait 10 s and retry 3 times max then return empty result
                    if re.search(r'An unexpected error has occurred', l_FBMessage) \
                            or re.search(r'An unknown error has occurred', l_FBMessage):
                        if l_errCount < 3:
                            l_wait = 10
                            self.m_logger.info('FB unknown error: {0} --> Waiting for {1} seconds'.format(
                                l_FBMessage,l_wait))

                            time.sleep(l_wait)
                            l_request = self.m_browserDriver.renew_token_and_request(l_request)
                        else:
                            l_response = '{"data": []}'

                            self.m_logger.warning('FB unknown error: {0} --> Returned: {1}\n'.format(
                                l_FBMessage, l_response))

                            l_finished = True

                    # Session expired ---> nothing to do
                    elif re.search(r'Session has expired', l_FBMessage):
                        l_msg = 'FB session expiry msg: {0}'.format(l_FBMessage)
                        self.m_logger.critical(l_msg)
                        raise BulkDownloaderException(l_msg)

                    # Unsupported get request ---> return empty data and abandon request attempt
                    elif re.search(r'Unsupported get request', l_FBMessage):
                        l_response = '{"data": []}'

                        self.m_logger.warning('FB unsupported get msg: {0} --> Returned: {1}'.format(
                            l_FBMessage, l_response))

                        l_finished = True

                    # Other FB error
                    else:
                        self.m_logger.critical('FB msg: {0}'.format(l_FBMessage))
                        raise BulkDownloaderException('FB msg: {0}'.format(l_FBMessage))

                # Non FB HTTPError
                else:
                    l_wait = self.getWait(l_errCount)
                    self.m_logger.warning('Non FB HTTPError {0} --> Waiting for {1} seconds'.format(
                        repr(e), l_wait))

                    time.sleep(l_wait)
                    if l_wait > 60 * 15:
                        l_request = self.m_browserDriver.renew_token_and_request(l_request)

                l_errCount += 1

            except urllib.error.URLError as e:
                self.m_logger.warning('URLError (Non Critical)\n{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}'.format(
                    'l_errCount     :', l_errCount,
                    'Request Problem:', repr(e),
                    '   Errno       :', e.errno,
                    '   Message     :', e.reason,
                    'p_request      :', p_request
                ))

                time.sleep(1)
                l_errCount += 1

            except Exception as e:
                self.m_logger.warning('Unknown Error\n{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}'.format(
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
            self.m_logger.critical('Too many errors: {0}'.format(p_errorCount))
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
            l_date = datetime.datetime.now()
        else:
            l_date = datetime.datetime.strptime(l_date, '%Y-%m-%d %H:%M:%S')

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

        l_cursor.close()

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

    def storeUser(self, p_id, p_name, p_date, p_padding):
        # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
        l_date = re.sub('T', ' ', p_date)
        l_date = re.sub(r'\+\d+$', '', l_date)

        if len(l_date) == 0:
            l_date = datetime.datetime.now()
        else:
            l_date = datetime.datetime.strptime(l_date, '%Y-%m-%d %H:%M:%S')

        l_conn = self.m_pool.getconn('BulkDownloader.storeUser()')
        l_cursor = l_conn.cursor()

        # print(l_query)
        try:
            l_cursor.execute("""
                INSERT INTO "TB_USER"("ID", "ST_NAME", "DT_CRE", "DT_MSG")
                VALUES( %s, %s, %s, %s )
            """, (
                p_id,
                p_name,
                datetime.datetime.now(),
                l_date
            ))
            l_conn.commit()
        except psycopg2.IntegrityError as e:
            self.m_logger.info('{0}User already known: [{1}]'.format(p_padding, e))
            # print('{0}PostgreSQL: {1}'.format(p_padding, e))
            l_conn.rollback()
        except Exception as e:
            self.m_logger.warning('TB_USER Unknown Exception: {0}/{1}'.format(repr(e), l_cursor.query))
            raise BulkDownloaderException('TB_USER Unknown Exception: {0}'.format(repr(e)))

        l_cursor.close()
        self.m_pool.putconn(l_conn)

    @classmethod
    def getOptionalField(self, p_json, p_field):
        l_value = ''
        l_valueShort = ''

        if p_field in p_json.keys():
            l_value = re.sub('\s+', ' ', p_json[p_field]).strip()
            if len(l_value) > 100:
                l_valueShort = l_value[0:100] + ' ... ({0})'.format(len(l_value))
            else:
                l_valueShort = l_value

        return l_value, l_valueShort

    def getPostsFromPage(self, p_id):
        # get list of posts in this page's feed

        l_fieldList = 'id,caption,created_time,description,from,icon,link,message,message_tags,name,object_id,' + \
                      'permalink_url,picture,place,properties,shares,source,status_type,story,to,type,' + \
                      'updated_time,with_tags'

        l_request = ('https://graph.facebook.com/{0}/{1}/feed?limit={2}&' +
                     'access_token={3}&fields={4}').format(
            EcAppParam.gcm_api_version, p_id, EcAppParam.gcm_limit, self.m_browserDriver.m_token_api, l_fieldList)

        # print('   l_request:', l_request)
        l_response = self.performRequest(l_request)

        l_responseData = json.loads(l_response)
        # print('   Paging:', l_responseData['paging'])
        if len(l_responseData['data']) > 0:
            self.m_logger.info('   Latest date:' + l_responseData['data'][0]['created_time'])

        l_postCount = 0
        l_finished = False
        while not l_finished:
            for l_post in l_responseData['data']:
                self.m_postRetrieved += 1

                l_postId = l_post['id']
                l_postDate = l_post['created_time']
                l_type = l_post['type']
                l_shares = int(l_post['shares']['count']) if 'shares' in l_post.keys() else 0
                self.m_logger.info(
                    '   =====[ {0}/{1} ]================POST========================='.format(
                        l_postCount, self.m_page))
                self.m_logger.info('   id          : ' + l_postId)
                self.m_logger.info('   date        : ' + l_postDate)

                # 2016-04-22T12:03:06+0000
                l_msgDate = datetime.datetime.strptime(
                    re.sub(r'\+\d+$', '', l_postDate), '%Y-%m-%dT%H:%M:%S')
                self.m_logger.info('   date (P)    : {0}'.format(l_msgDate))

                # if message older than G_DAYS_DEPTH days ---> break loop
                l_days_old = (datetime.datetime.now() - l_msgDate).days
                self.m_logger.info('   Days old    : {0}'.format(l_days_old))
                if l_days_old > EcAppParam.gcm_days_depth:
                    l_finished = True
                    break

                l_userId = ''
                if 'from' in l_post.keys():
                    l_userId, l_userIdShort = BulkDownloader.getOptionalField(l_post['from'], 'id')
                    l_userName, l_userNameShort = BulkDownloader.getOptionalField(l_post['from'], 'name')

                    if EcAppParam.gcm_verboseModeOn:
                        self.m_logger.info('   from        : {0} [{1}]'.format(l_userNameShort, l_userId))

                    # store user data
                    self.storeUser(l_userId, l_userName, l_postDate, '   ')

                l_name, l_nameShort = BulkDownloader.getOptionalField(l_post, 'name')
                l_caption, l_captionShort = BulkDownloader.getOptionalField(l_post, 'caption')
                l_description, l_descriptionSh = BulkDownloader.getOptionalField(l_post, 'description')
                l_story, l_storyShort = BulkDownloader.getOptionalField(l_post, 'story')
                l_message, l_messageShort = BulkDownloader.getOptionalField(l_post, 'message')

                l_link, x = BulkDownloader.getOptionalField(l_post, 'link')
                l_object_id, x = BulkDownloader.getOptionalField(l_post, 'object_id')
                l_picture, x = BulkDownloader.getOptionalField(l_post, 'picture')
                l_source, x = BulkDownloader.getOptionalField(l_post, 'source')

                l_icon, x = BulkDownloader.getOptionalField(l_post, 'icon')
                l_permalink_url, x = BulkDownloader.getOptionalField(l_post, 'permalink_url')
                l_status_type, x = BulkDownloader.getOptionalField(l_post, 'status_type')
                l_updated_time, x = BulkDownloader.getOptionalField(l_post, 'updated_time')

                l_place = ''
                if 'place' in l_post.keys():
                    l_place = l_post['place']

                l_tags = ''
                if 'message_tags' in l_post.keys():
                    l_tags = l_post['message_tags']

                l_with_tags = ''
                if 'with_tags' in l_post.keys():
                    l_with_tags = l_post['with_tags']

                l_properties = ''
                if 'properties' in l_post.keys():
                    l_properties = l_post['properties']

                self.m_logger.info('   name        : ' + l_nameShort)
                if EcAppParam.gcm_verboseModeOn:
                    self.m_logger.info('   caption     : ' + l_captionShort)
                    self.m_logger.info('   description : ' + l_descriptionSh)
                    self.m_logger.info('   story       : ' + l_storyShort)
                    self.m_logger.info('   message     : ' + l_messageShort)
                    self.m_logger.info('   permalink   : ' + l_permalink_url)
                    self.m_logger.info('   icon        : ' + l_icon)
                    self.m_logger.info('   object_id   : ' + l_object_id)
                    self.m_logger.info('   shares      : {0}'.format(l_shares))
                    self.m_logger.info('   type        : ' + l_type)
                    self.m_logger.info('   status type : ' + l_status_type)
                    self.m_logger.info('   link        : ' + l_link)
                    self.m_logger.info('   source      : ' + l_source)
                    self.m_logger.info('   picture     : ' + l_picture)
                    self.m_logger.info('   updated time: ' + l_updated_time)
                    self.m_logger.info('   with        : {0}'.format(l_with_tags))
                    self.m_logger.info('   tags        : {0}'.format(l_tags))
                    self.m_logger.info('   properties  : {0}'.format(l_properties))
                    self.m_logger.info('   place       : {0}'.format(l_place))

                # store post information
                if self.storeObject(
                        p_padding='   ',
                        p_type='Post',
                        p_FBType=l_type,
                        p_id=l_postId,
                        p_parentId=p_id,
                        p_pageId=p_id,
                        p_postId='',
                        p_date=l_postDate,
                        p_likeCount=0,
                        p_shareCount=l_shares,
                        p_name=l_name,
                        p_caption=l_caption,
                        p_desc=l_description,
                        p_story=l_story,
                        p_message=l_message,
                        p_link=l_link,
                        p_picture=l_picture,
                        p_place=l_place,
                        p_source=l_source,
                        p_userId=l_userId,
                        p_raw=json.dumps(l_post['attachment']) if 'attachment' in l_post.keys() else ''
                    ):
                    # get comments
                    self.getPostAttachments(l_postId)
                    # self.getComments(l_postId, l_postId, p_id, 0)
                    #time.sleep(5)

                else:
                    # if already in DB ---> break loop
                    l_finished = True
                    break

                l_postCount += 1
                if l_postCount > EcAppParam.gcm_max_post:
                    l_finished = True
                    break

                # End for l_post in l_responseData['data']:

            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                self.m_logger.info('   *** Getting next block ...')
                l_request = l_responseData['paging']['next']
                l_response = self.performRequest(l_request)

                l_responseData = json.loads(l_response)
            else:
                break

            # end while not l_finished:

    def getPostAttachments(self, p_id):
        # get list of attachments attached to this post
        l_fieldList = 'description,description_tags,media,target,title,type,url'

        l_request = ('https://graph.facebook.com/{0}/{1}/attachments?limit={2}&' +
                     'access_token={3}&fields={4}').format(
            EcAppParam.gcm_api_version, p_id, EcAppParam.gcm_limit, self.m_browserDriver.m_token_api, l_fieldList)

        # print('   l_request:', l_request)
        l_response = self.performRequest(l_request)

        l_responseData = json.loads(l_response)
        # print('   Paging:', l_responseData['paging'])

        l_attachmentCount = 0
        for l_attachment in l_responseData['data']:
            l_description, x = BulkDownloader.getOptionalField(l_attachment, 'description')
            l_title, x = BulkDownloader.getOptionalField(l_attachment, 'title')
            l_type, x = BulkDownloader.getOptionalField(l_attachment, 'type')
            l_url, x = BulkDownloader.getOptionalField(l_attachment, 'url')

            l_description_tags = ''
            if 'description_tags' in l_attachment.keys():
                l_description_tags = l_attachment['description_tags']
            l_media = ''
            if 'media' in l_attachment.keys():
                l_media = l_attachment['media']
            l_target = ''
            if 'target' in l_attachment.keys():
                l_target = l_attachment['target']

            self.m_logger.info(
                '   ++++[ {0}/{1} ]++++++++++++ATTACHMENT++++++++++++++++++++++++'.format(
                    l_attachmentCount, self.m_page))

            self.m_logger.info('   Description : ' + l_description)
            self.m_logger.info('   Title       : ' + l_title)
            self.m_logger.info('   Type        : ' + l_type)
            self.m_logger.info('   Url         : ' + l_url)
            self.m_logger.info('   Tags        : {0}'.format(l_description_tags))
            self.m_logger.info('   Media       : {0}'.format(l_media))
            self.m_logger.info('   Target      : {0}'.format(l_target))

            l_attachmentCount += 1

    def getComments(self, p_id, p_postId, p_pageId, p_depth):
        l_depthPadding = ' ' * ((p_depth + 2) * 3)

        # get list of comments attached to this post (or this comment)
        l_fieldList = 'id,created_time,from,story,message,user_likes,like_count,comment_count,attachment,object'

        l_request = ('https://graph.facebook.com/{0}/{1}/comments?limit={2}&' +
                     'access_token={3}&fields={4}').format(
            EcAppParam.gcm_api_version, p_id, EcAppParam.gcm_limit, self.m_browserDriver.m_token_api, l_fieldList)

        # print('   l_request:', l_request)
        l_response = self.performRequest(l_request)

        l_responseData = json.loads(l_response)
        # print('   Paging:', l_responseData['paging'])
        if len(l_responseData['data']) > 0:
            self.m_logger.info('{0}Latest date: '.format(l_depthPadding) + l_responseData['data'][0]['created_time'])

        l_commCount = 0
        while True:
            for l_comment in l_responseData['data']:
                self.m_commentRetrieved += 1

                l_commentId = l_comment['id']
                l_commentDate = l_comment['created_time']
                l_commentLikes = int(l_comment['like_count'])
                l_commentCCount = int(l_comment['comment_count'])
                if EcAppParam.gcm_verboseModeOn:
                    self.m_logger.info(
                        '{0}----[{1}]-----------COMMENT------------------------------'.format(
                            l_depthPadding, self.m_page))
                    self.m_logger.info('{0}id      : '.format(l_depthPadding) + l_commentId)
                    self.m_logger.info('{0}date    : '.format(l_depthPadding) + l_commentDate)
                    self.m_logger.info('{0}likes   : {1}'.format(l_depthPadding, l_commentLikes))
                    self.m_logger.info('{0}sub com.: {1}'.format(l_depthPadding, l_commentCCount))

                l_userId = ''
                if 'from' in l_comment.keys():
                    l_userId, l_userIdShort = BulkDownloader.getOptionalField(l_comment['from'], 'id')
                    l_userName, l_userNameShort = BulkDownloader.getOptionalField(l_comment['from'], 'name')

                    if EcAppParam.gcm_verboseModeOn:
                        self.m_logger.info('{0}from    : {1} [{2}]'.format(l_depthPadding, l_userNameShort, l_userId))

                    # store user data
                    self.storeUser(l_userId, l_userName, l_commentDate, l_depthPadding)

                l_story, l_storyShort = BulkDownloader.getOptionalField(l_comment, 'story')
                l_message, l_messageShort = BulkDownloader.getOptionalField(l_comment, 'message')

                if EcAppParam.gcm_verboseModeOn:
                    self.m_logger.info('{0}story   : '.format(l_depthPadding) + l_storyShort)
                    self.m_logger.info('{0}message : '.format(l_depthPadding) + l_messageShort)

                l_src = ''
                l_url = ''
                l_desc = ''
                l_title = ''
                if 'attachment' in l_comment.keys():
                    if 'media' in l_comment['attachment'].keys() and \
                                    'image' in l_comment['attachment']['media'].keys() and \
                                    'src' in l_comment['attachment']['media']['image'].keys():
                        l_src = l_comment['attachment']['media']['image']['src']

                    if 'url' in l_comment['attachment'].keys():
                        l_url = l_comment['attachment']['url']
                    if 'title' in l_comment['attachment'].keys():
                        l_title = l_comment['attachment']['title']
                    if 'description' in l_comment['attachment'].keys():
                        l_desc = l_comment['attachment']['description']

                if EcAppParam.gcm_verboseModeOn:
                    self.m_logger.info('{0}url     : '.format(l_depthPadding) + l_url)
                    self.m_logger.info('{0}src     : '.format(l_depthPadding) + l_src)

                # store comment information
                self.storeObject(
                    p_padding=l_depthPadding,
                    p_type='Comm',
                    p_FBType='Comment',
                    p_id=l_commentId,
                    p_parentId=p_id,
                    p_pageId=p_pageId,
                    p_postId=p_postId,
                    p_date=l_commentDate,
                    p_likeCount=l_commentLikes,
                    p_shareCount=0,
                    p_name='',
                    p_caption=l_title,
                    p_desc=l_desc,
                    p_story=l_story,
                    p_message=l_message,
                    p_link=l_url,
                    p_picture=l_src,
                    p_place='',
                    p_source='',
                    p_userId=l_userId,
                    p_raw=json.dumps(l_comment['attachment']) if 'attachment' in l_comment.keys() else ''
                )
                l_commCount += 1

                # get comments
                if l_commentCCount > 0:
                    self.getComments(l_commentId, p_postId, p_pageId, p_depth + 1)

            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                self.m_logger.info('{0}[{1}] *** Getting next block ...'.format(l_depthPadding, l_commCount))
                l_request = l_responseData['paging']['next']
                l_response = self.performRequest(l_request)

                l_responseData = json.loads(l_response)
            else:
                break

        self.m_logger.info('{0}comment download count --> {1}'.format(l_depthPadding[:-3], l_commCount))

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