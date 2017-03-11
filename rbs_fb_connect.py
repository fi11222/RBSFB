#!/usr/bin/python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
from selenium.webdriver.chrome.options import Options

from pyvirtualdisplay import Display
from PIL import Image

import lxml.html as html
import sys
import io
import random

from ec_utilities import *

__author__ = 'Pavan Mahalingam'


class BrowserDriverException(Exception):
    def __init__(self, p_msg):
        self.m_msg = p_msg


class BrowserDriver:
    @staticmethod
    def get_unique_attr(p_frag, p_xpath, p_attribute):
        """
        get a unique element attribute through lxml, with a warning mark ('¤')
        inside the string if more than one was found

        :param p_frag: lxml fragment from which to extract the value
        :param p_xpath: XPath pointing to the element
        :param p_attribute: Attribute name
        :return: Attribute value with possible warning mark ('¤') if more than one found
        """
        return '¤'.join([str(l_span.get(p_attribute)) for l_span in p_frag.xpath(p_xpath)]).strip()

    # get a unique text element through lxml, with a warning mark ('¤')
    # inside the string if more than one was found
    @staticmethod
    def get_unique(p_frag, p_xpath):
        """
        get a unique text element through lxml, with a warning mark ('¤')
        inside the string if more than one was found

        :param p_frag: lxml fragment from which to extract the value
        :param p_xpath: XPath pointing to the element
        :return: Text content of the element with possible warning mark ('¤') if more than one found
        """
        return '¤'.join([str(l_span.text_content()) for l_span in p_frag.xpath(p_xpath)]).strip()

    def __init__(self):
        self.m_logger = logging.getLogger('BrowserDriver')

        if EcAppParam.gcm_headless:
            self.m_logger.info("Launching xvfb")
            self.m_display = Display(visible=0, size=(EcAppParam.gcm_headlessWidth, EcAppParam.gcm_headlessHeight))
            self.m_display.start()
        else:
            self.m_display = None

        if EcAppParam.gcm_browser == 'Chrome':
            l_option = Options()

            l_option.add_argument('disable-notifications')

            # Create a new instance of the Chrome driver
            self.m_logger.info("Launching Chrome")
            self.m_driver = webdriver.Chrome(chrome_options=l_option)

            if not EcAppParam.gcm_headless:
                # Move the window to position x/y
                self.m_driver.set_window_position(700, 0)
                # Resize the window to the screen width/height
                self.m_driver.set_window_size(1200, 1000)

        elif EcAppParam.gcm_browser == 'Firefox':
            # Create a new instance of the Firefox driver
            self.m_logger.info("Launching Firefox")
            self.m_driver = webdriver.Firefox()

            if not EcAppParam.gcm_headless:
                # Resize the window to the screen width/height
                self.m_driver.set_window_size(1200, 1000)
                # Move the window to position x/y
                self.m_driver.set_window_position(800, 0)
        else:
            l_message = '[BrowserDriver] Browser type not supported: {0}'.format(EcAppParam.gcm_browser)
            self.m_logger.critical(l_message)
            raise BrowserDriverException(l_message)

    def close(self):
        self.m_driver.close()

        if self.m_display is not None:
            self.m_display.stop()

    def login_as_scrape(self, p_user, p_passwd):
        # load logging page
        self.m_driver.get('http://www.facebook.com')

        try:
            l_userInput = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//td/input[@id="email"]')))

            l_userInput.send_keys(p_user)

            l_pwdInput = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//td/input[@id="pass"]')))

            l_pwdInput.send_keys(p_passwd)

            # loginbutton
            self.m_driver.find_element_by_xpath('//label[@id="loginbutton"]/input').click()

            # wait for mainContainer
            WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="mainContainer"]')))
        except EX.TimeoutException:
            self.m_logger.critical('Did not find user ID input or post-login mainContainer')
            raise

    def go_random(self):
        l_connect = psycopg2.connect(
            host=EcAppParam.gcm_dbServer,
            database=EcAppParam.gcm_dbDatabase,
            user=EcAppParam.gcm_dbUser,
            password=EcAppParam.gcm_dbPassword
        )

        # TB_USER row count
        l_query = """
                    select count(1)
                    from
                        "TB_USER"
                    ;"""

        l_cursor = l_connect.cursor()
        l_cursor.execute(l_query)
        for l_count, in l_cursor:
            pass

        # choose random row
        l_row_choice = random.randrange(l_count)

        self.m_logger.info('User count: {0}'.format(l_count))
        self.m_logger.info('Row choice: {0}'.format(l_row_choice))

        # retrieve ID of chosen row
        l_query = """
                    select "ID"
                    from
                        "TB_USER"
                    order by
                        "ID_INTERNAL"
                    offset {0};""".format(l_row_choice)

        l_cursor = l_connect.cursor()
        l_cursor.execute(l_query)
        for l_id, in l_cursor:
            break

        self.m_logger.info('ID: {0}'.format(l_id))
        l_connect.close()

        self.m_driver.get('http://www.facebook.com/{0}'.format(l_id))
        try:
            # wait for mainContainer
            WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="mainContainer"]')))
        except EX.TimeoutException:
            self.m_logger.critical('Did not find user ID input or post-login mainContainer')
            raise

        self.m_logger.info('user page for ID [{0}] loaded'.format(l_id))

    def get_fb_profile(self):
        self.m_logger.info("get_fb_profile()")

        l_storyPrefix = 'tl_unit_'

        WebDriverWait(self.m_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "{0}")]'.format(l_storyPrefix))))

        self.m_logger.info('presence of {0}'.format(l_storyPrefix))

        l_storyList = []
        l_fruitlessTries = 0
        l_curY = 0
        l_storyCount = 0
        while True:
            l_fruitlessTry = True
            print('###')
            for l_story in self.m_driver.find_elements_by_xpath('//div[contains(@id, "{0}")]'.format(l_storyPrefix)):
                try:
                    l_id = l_story.get_attribute('id')
                    if l_id not in l_storyList:
                        l_fruitlessTry = False
                        l_fruitlessTries = 0
                        print('+++ ' + l_id)
                        l_storyList.append(l_id)

                        l_curY = self.analyze_story(l_story, l_storyCount, l_curY, p_storyPrefix=l_storyPrefix)

                        #self.m_driver.execute_script("return arguments[0].scrollIntoView();", l_story)
                        #WebDriverWait(self.m_driver, 15).until(EC.visibility_of(l_story))

                        l_storyCount += 1
                    else:
                        print('--- ' + l_id)
                except EX.StaleElementReferenceException:
                    continue

            if l_fruitlessTry:
                l_fruitlessTries += 1

            if l_storyCount > EcAppParam.gcm_max_story_count or l_fruitlessTries > 3:
                break


    def get_fb_feed(self):
        self.m_logger.info("get_fb_feed()")

        l_storyPrefix = 'hyperfeed_story_id_'

        WebDriverWait(self.m_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "{0}")]'.format(l_storyPrefix))))

        self.m_logger.info('presence of {0}'.format(l_storyPrefix))

        WebDriverWait(self.m_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "more_pager_pagelet_")]')))

        self.m_logger.info("presence of more_pager_pagelet_")

        l_expansionCount = EcAppParam.gcm_expansionCount

        while True:
            l_pagers_found = 0
            l_last_pager = None
            for l_last_pager in self.m_driver.find_elements_by_xpath('//div[contains(@id, "more_pager_pagelet_")]'):
                l_pagers_found += 1

            self.m_logger.info('Expanding pager #{0}'.format(l_pagers_found))
            if l_last_pager is not None:
                self.m_driver.execute_script("return arguments[0].scrollIntoView();", l_last_pager)

            if l_pagers_found >= l_expansionCount:
                break

        l_stab_iter = 0
        while True:
            l_finished = True
            for l_story in self.m_driver.find_elements_by_xpath('//div[contains(@id, "{0}")]'.format(l_storyPrefix)):
                try:
                    l_data_ft = l_story.get_attribute('data-ft')

                    if l_data_ft is not None:
                        l_finished = False
                except EX.StaleElementReferenceException:
                    continue

            self.m_logger.info('Stab loop #{0}'.format(l_stab_iter))
            l_stab_iter += 1
            if l_finished:
                break

        self.m_driver.execute_script('window.scrollTo(0, 0);')
        l_curY = 0
        l_iter_disp = 0
        for l_story in self.m_driver.find_elements_by_xpath('//div[contains(@id, "{0}")]'.format(l_storyPrefix)):
            try:
                l_curY = self.analyze_story(l_story, l_iter_disp, l_curY)

                l_iter_disp += 1
            except EX.StaleElementReferenceException:
                print('***** STALE ! ******')

    def analyze_story(self, p_story, p_iter, p_curY, p_storyPrefix='hyperfeed_story_id_'):
        l_html = p_story.get_attribute('outerHTML')
        l_htmlShort = l_html[:500]
        if len(l_html) != len(l_htmlShort):
            l_htmlShort += '...'
        print("-------- {0} --------\n{1}".format(p_iter, l_htmlShort))

        l_id = p_story.get_attribute('id')
        l_id = re.sub(p_storyPrefix, '', l_id).strip()

        l_location = p_story.location
        l_size = p_story.size

        if l_location['x'] == 0 or l_location['y'] == p_curY:
            self.m_logger.info('Location anomaly: {0}'.format(l_location))
            return p_curY

        l_yTop = l_location['y'] - 100 if l_location['y'] > 100 else 0
        l_deltaY = l_yTop - p_curY
        l_curY = l_yTop
        l_overshoot = l_location['y'] + l_size['height'] + 50

        self.m_driver.execute_script('window.scrollTo(0, {0});'.format(l_overshoot))
        self.m_driver.execute_script('window.scrollTo(0, {0});'.format(l_yTop))
        #self.m_driver.execute_script('window.scrollBy(0, {0});'.format(l_deltaY))
        WebDriverWait(self.m_driver, 15).until(EC.visibility_of(p_story))

        l_dataWait = 0
        while True:
            l_data_ft = p_story.get_attribute('data-ft')
            if l_data_ft is None:
                break
            else:
                l_dataWait += 1
                print('l_data_ft: ' + l_data_ft)

            if l_dataWait > 30:
                return p_curY

        # extract a full xml/html tree from the page
        l_tree = html.fromstring(l_html)

        # Date(s)
        l_date = BrowserDriver.get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')

        # extract text
        l_postText = BrowserDriver.get_unique(l_tree,
            '//div[contains(@class, "userContent") and not(contains(@class, "userContentWrapper"))]')

        # determining from
        l_shareTypes = ['photo', 'post', 'link', 'event', 'video']
        l_from = []
        l_fromDict = dict()
        for l_xpath in ['//div[contains(@class, "_5x46")]//a[contains(@class, "profileLink")]', '//h5/span/span/a']:
            for l_profLink in l_tree.xpath(l_xpath):
                l_fromName =  l_profLink.text_content()

                l_fromUser = l_profLink.get('href')
                if l_fromUser is not None and len(l_fromUser) > 0:
                    # 'https\:\/\/www\.facebook\.com\/Sergei1970sk'
                    # https://www.facebook.com/solanki.jagdish.75098?hc_ref=NEWSFEED
                    if re.search('\.php\?id\=', l_fromUser):
                        l_match = re.search('\.php\?id\=(\d+)(\&|$)', l_fromUser)
                        if l_match:
                            l_fromUser = l_match.group(1)
                    else:
                        l_match = re.search('\.com/([^\?]+)(\?|$)', l_fromUser)
                        if l_match:
                            l_fromUser = l_match.group(1)

                l_fromId = l_profLink.get('data-hovercard')
                if l_fromId is not None and len(l_fromId) > 0:
                    l_match = re.search('\.php\?id\=(\d+)(\&|$)', l_fromId)
                    if l_match:
                        l_fromId = l_match.group(1)

                if not(l_fromName in l_shareTypes and l_fromId is None):
                    l_from += [(l_fromName, l_fromId, l_fromUser)]
                    l_fromDict[l_fromId] = (l_fromName, l_fromUser)

            if len(l_from) > 0:
                break

        #l_from = BrowserDriver.get_unique(l_tree, '//a[contains(@class, "profileLink")]')

        # _5vra --> post header
        l_sharedList = []
        for l_type in l_shareTypes:
            for l in l_tree.xpath('.//h5[contains(@class, "_5vra")]//a[text()="{0}"]'.format(l_type)):
                l_sharedList.append((l_type, l.get('href')))

        l_sponsored = (len(l_tree.xpath('.//a[text()="Sponsored"]')) > 0)

        # determining type
        l_fromHeader = BrowserDriver.get_unique(l_tree, '//h5[contains(@class, "_5vra")]')
        l_fromHeaderSub = BrowserDriver.get_unique(l_tree, '//h6[contains(@class, "_5vra")]')

        l_hasWith = False
        if re.search('with', l_fromHeader) or re.search('with', l_fromHeaderSub):
            l_hasWith = True

        l_type = 'post'
        if l_sponsored:
            l_type = 'sponsored'
        else:
            if re.search('shared|liked', l_fromHeader):
                if re.search('shared', l_fromHeader):
                    l_type = 'share'
                else:
                    l_type = 'like'

                if len(l_sharedList) > 0:
                    l_type += '/{0}'.format(l_sharedList[0][0])
            elif re.search('commented on this', l_fromHeader):
                l_type = 'comment'
            elif re.search('updated (his|her) profile picture', l_fromHeader):
                l_type = 'narcissistic/PP'
            elif re.search('updated (his|her) cover photo', l_fromHeader):
                l_type = 'narcissistic/CP'
            elif re.search('updated (his|her) profile video', l_fromHeader):
                l_type = 'narcissistic/PV'
            else:
                l_fromHeader2 = BrowserDriver.get_unique(l_tree, '//div[contains(@class, "fwn fcg")]')
                # <div class="fwn fcg"><span class="fwb fcb">People you may know</span></div>
                if re.search('People you may know', l_fromHeader2):
                    l_type = 'FB/PYMK'

        if l_hasWith:
            l_type += '/with'

        print('Id             : ' + l_id)
        print('l_fromHeader   : ' + l_fromHeader)
        print('Sponsored      : ' + repr(l_sponsored))
        print('Type           : ' + l_type)
        print('Shared objects : ' + repr(l_sharedList))
        print('Has with       : ' + repr(l_hasWith))
        print('Date           : ' + l_date)
        print('From           : ' + repr(l_from))
        print('From (dict)    : ' + repr(l_fromDict))
        print('Text           : ' + l_postText)
        print('Size           : {0}'.format(l_size))
        print('Location       : {0}'.format(l_location))
        print('l_curY         : {0}'.format(p_curY))
        print('l_yTop         : {0}'.format(l_yTop))
        print('l_deltaY       : {0}'.format(l_deltaY))
        print('l_overshoot    : {0}'.format(l_overshoot))
        print('*** scrollBy(l_deltaY) ***')

        # store html source and image of complete story
        l_baseName = '{0:03}-'.format(p_iter) + l_id

        l_imgStory = Image.open(io.BytesIO(self.m_driver.get_screenshot_as_png()))
        x = l_location['x']
        y = l_location['y'] - l_yTop

        l_img = l_imgStory.crop((x, y, x + l_size['width'], y + l_size['height']))

        l_img.save(l_baseName + '.png')
        # self.m_driver.get_screenshot_as_file(l_baseName + '.png')
        # l_story.screenshot(l_baseName + '_.png')

        with open(l_baseName + '.xml', "w") as l_xml_file:
            l_xml_file.write(l_html)

        # extract images from the story
        l_imgCount = 0
        for l_xpath in ['.//div[./img[contains(@class, "img")]]', './/img[contains(@class, "img")]']:
            for l_image in p_story.find_elements_by_xpath(l_xpath):
                l_height = l_image.size['height']
                l_width = l_image.size['width']
                if l_width >= EcAppParam.gcm_minImageSize and l_height >= EcAppParam.gcm_minImageSize:
                    l_htmlHeight = l_image.get_attribute('height')
                    l_htmlwidth = l_image.get_attribute('width')

                    print('[{0}] S:({1} {2}) H:({3} {4}): '.format(
                            l_imgCount, l_width, l_height, l_htmlwidth, l_htmlHeight) +
                          l_image.get_attribute('outerHTML'))

                    #for i in range(0,10):
                    #    print('Loaded: ' + repr(self.m_driver.execute_script('return arguments[0].complete', l_image)))

                    l_img_location = l_image.location
                    xi = l_img_location['x']
                    yi = l_img_location['y'] - l_yTop

                    l_imgInStory = l_imgStory.crop((xi, yi, xi + l_width, yi + l_height))
                    l_imgInStory.save(l_baseName + '_{0:02}.png'.format(l_imgCount))
                    l_imgCount += 1

            if l_imgCount > 0:
                break

        return l_curY


def get_profile_pjs(p_driver):
    EcLogger.cm_logger.info("get_profile()")

    WebDriverWait(p_driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "hyperfeed_story_id_")]')))

    EcLogger.cm_logger.info("presence of hyperfeed_story_id_")


    WebDriverWait(p_driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "more_pager_pagelet_")]')))

    EcLogger.cm_logger.info("presence of more_pager_pagelet_")

    for i in range(0):
        p_driver.get_screenshot_as_file('FeedLoad_{0:02}.png'.format(i))
        time.sleep(.1)

    l_expansionCount = 3
    while True:
        l_pagers_found = 0
        l_last_pager = None
        for l_last_pager in p_driver.find_elements_by_xpath('//div[contains(@id, "more_pager_pagelet_")]'):
            l_pagers_found += 1

        EcLogger.cm_logger.info('Expanding pager #{0}'.format(l_pagers_found))
        if l_last_pager is not None:
            p_driver.execute_script("return arguments[0].scrollIntoView();", l_last_pager)

        p_driver.get_screenshot_as_file('ExpansionLoad_{0:02}.png'.format(l_pagers_found))

        if l_pagers_found >= l_expansionCount:
            break

    l_stab_iter = 0
    while True:
        l_finished = True
        for l_story in p_driver.find_elements_by_xpath('//div[contains(@id, "hyperfeed_story_id_")]'):
            try:
                l_data_ft = l_story.get_attribute('data-ft')

                if l_data_ft is not None:
                    l_finished = False
            except EX.StaleElementReferenceException:
                continue

        EcLogger.cm_logger.info('Stab loop #{0}'.format(l_stab_iter))
        l_stab_iter += 1
        if l_finished:
            break

    p_driver.get_screenshot_as_file('ExpansionLoad_98_Stab.png')

    l_iter_disp = 0
    for l_story in p_driver.find_elements_by_xpath('//div[contains(@id, "hyperfeed_story_id_")]'):
        try:
            l_html = l_story.get_attribute('outerHTML')
            l_id = l_story.get_attribute('id')
            l_id = re.sub('hyperfeed_story_id_', '', l_id).strip()
            # extract a full xml/html tree from the page
            l_tree = html.fromstring(l_html)

            # class="_5ptz"
            l_date = BrowserDriver.get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')
            l_from = BrowserDriver.get_unique(l_tree, '//a[contains(@class, "profileLink")]')

            l_htmlShort = l_html[:500]
            if len(l_html) != len(l_htmlShort):
                l_htmlShort += '...'
            print("-------- {0} --------\n{1}".format(l_iter_disp, l_htmlShort))

            l_location = l_story.location

            print('Id       : ' + l_id)
            print('Date     : ' + l_date)
            print('From     : ' + l_from)
            print('Location : {0}'.format(l_location))

            l_iter_disp += 1
        except EX.StaleElementReferenceException:
            print('***** STALE ! ******')

    for i in range(2):
        p_driver.get_screenshot_as_file('ExpansionLoad_99_Final_{0:02}.png'.format(i))
        time.sleep(.1)

    p_driver.quit()


def old_1(p_driver):
    WebDriverWait(p_driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "hyperfeed_story_id_")]')))

    l_iter = 0
    while True:
        print('+++++++++++++++++ {0} +++++++++++++++++'.format(l_iter))
        l_iter += 1

        l_iter_inner = 0
        for l_story in p_driver.find_elements_by_xpath('//div[contains(@id, "hyperfeed_story_id_")]'):
            try:
                l_html = l_story.get_attribute('outerHTML')

                # extract a full xml/html tree from the page
                l_tree = html.fromstring(l_html)

                # class="_5ptz"
                l_date = BrowserDriver.get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')
                l_from = BrowserDriver.get_unique(l_tree, '//a[contains(@class, "profileLink")]')

                l_data_ft = l_story.get_attribute('data-ft')

                l_htmlShort = l_html[:500]
                if len(l_html) != len(l_htmlShort):
                    l_htmlShort += '...'
                print("-------- {0} --------\n{1}".format(l_iter_inner, l_htmlShort))
                l_iter_inner += 1

                print('FT  : {0}'.format(l_data_ft))
                print('Date: ' + l_date)
                print('From: ' + l_from)
            except EX.StaleElementReferenceException:
                print('***** STALE ! ******')

        time.sleep(.10)

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
    gcm_maxiter = 20
    l_iter = 0
    while True:
        if l_iter >= gcm_maxiter:
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

    #g_browser = 'Firefox'
    #g_browser = 'xxx'
    g_browser = 'Chrome'

    l_phantomId = 'aziz.sharjahulmulk@gmail.com'
    l_phantomPwd = '15Eyyaka'

    l_driver = BrowserDriver()
    l_driver.login_as_scrape(l_phantomId, l_phantomPwd)
    l_driver.go_random()
    l_driver.get_fb_profile()

    if EcAppParam.gcm_headless:
        l_driver.close()