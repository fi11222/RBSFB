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
from subprocess import run, PIPE

import lxml.html as html
import sys
import io
import random
import subprocess
import json
import base64

from ec_utilities import *
import openvpn

__author__ = 'Pavan Mahalingam'


class BrowserDriverException(Exception):
    def __init__(self, p_msg):
        self.m_msg = p_msg


class BrowserDriver:
    """
    The class driving the data extraction process.

    At instantiation, creates a Selenium Chrome driver and a headless (or non-headless) instance of chrome.
    After that, all operations are handled by this class.
    """

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

    def __init__(self, p_user, p_pwd, p_vpn):
        """
        Instantiates Selenium WebDriver and Chrome instance. Chrome is headless or not
        depending on the value of :any:`EcAppParam.gcm_headless` (boolean)
        """
        # instantiates class logger
        self.m_logger = logging.getLogger('BrowserDriver')

        # creation date/time (for staleness)
        self.m_creationDate = datetime.datetime.now(tz=pytz.utc)
        l_lifespan = EcAppParam.gcm_bdLifeAverage + \
                     (EcAppParam.gcm_bdLifeDiameter/2.0 - random.random()*EcAppParam.gcm_bdLifeDiameter)
        self.m_expirationDate = datetime.datetime.now(tz=pytz.utc) + datetime.timedelta(hours=l_lifespan)
        self.m_logger.info('lifespan: {0} hours'.format(l_lifespan))


        if EcAppParam.gcm_headless:
            # if headless mode requested, starts the pyvirtualdisplay xvfb driver
            self.m_logger.info("Launching xvfb")
            self.m_display = Display(visible=0, size=(EcAppParam.gcm_headlessWidth, EcAppParam.gcm_headlessHeight))
            self.m_display.start()
        else:
            self.m_display = None

        # Launch Chrome (or Firefox) Webdriver
        if EcAppParam.gcm_browser == 'Chrome':
            # option object to be passed to chrome
            l_option = Options()

            # notification disabling option to be passed to Chrome
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

        self.login_as_scrape(p_user, p_pwd, p_vpn)

    def isStale(self):
        """
        Past expiration date flag.
        :return: Boolean. True if past expiration date.
        """
        return self.m_expirationDate < datetime.datetime.now(tz=pytz.utc)

    def close(self):
        """
        Closing method. Closes Chrome and the associated WebDriver. If headless then also close xvfb.
        :return: Nothing
        """
        self.m_driver.close()
        self.m_driver = None

        if self.m_display is not None:
            self.m_display.stop()
            self.m_display = None

        if self.m_vpn_handle is not None:
            self.m_vpn_handle.close()
            self.m_vpn_handle = None

        l_result = run(['sudo', 'killall', '-9', 'chromedriver'], stdout=PIPE, stderr=PIPE)
        self.m_logger.info('Killing chromedriver : ' + repr(l_result))
        l_result = run(['sudo', 'killall', '-9', 'chromium-browser'], stdout=PIPE, stderr=PIPE)
        self.m_logger.info('Killing Chromium : ' + repr(l_result))

    def login_as_scrape(self, p_user, p_passwd, p_vpn):
        """
        Logging-in method.

        :param p_user: FB user ID
        :param p_passwd: FB password
        :return: nothing (if there were problems --> raise errors)
        """

        # open vpn
        if p_vpn is not None and len(p_vpn) > 0:
            self.m_vpn_handle = openvpn.OpenvpnWrapper(p_vpn)
        else:
            self.m_vpn_handle = None

        # load logging page
        self.m_driver.get('http://www.facebook.com')

        try:
            # wait for the presence of the user ID (or e-mail) text input field.
            l_userInput = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//td/input[@id="email"]')))

            # sends the user ID string to it
            l_userInput.send_keys(p_user)

            # wait for the presence of the user password (or e-mail) text input field.
            l_pwdInput = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//td/input[@id="pass"]')))

            # sends the password string to it
            l_pwdInput.send_keys(p_passwd)

            # finds the log-in button and clicks it
            self.m_driver.find_element_by_xpath('//label[@id="loginbutton"]/input').click()

            # wait for the presence of the `mainContainer` element, indicating post login page load
            WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="mainContainer"]')))
        except EX.TimeoutException:
            self.m_logger.critical('Did not find user ID/pwd input or post-login mainContainer')
            raise

    def log_out(self):
        try:
            # wait for the presence of the settings arrow down button
            l_settings = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(@class, "_5lxs")]')))

            l_settings.click()
        except EX.TimeoutException:
            self.m_logger.critical('Did not find settings arrow down button')
            raise

        try:
            # wait for the presence of the log-out button
            l_logoutButton = WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//a[@class="_54nc" and contains(@data-gt, "menu_logout")]')))

            l_logoutButton.click()
        except EX.TimeoutException:
            self.m_logger.critical('Did not find logout button')
            raise

        # close vpn if present
        if self.m_vpn_handle is not None:
            self.m_vpn_handle.close()
            self.m_vpn_handle = None

    def go_random(self):
        """
        Selects a user ID from TB_USER and display its FB profile
        :return: The chosen user ID
        """
        # connects to the database
        l_connect1 = psycopg2.connect(
            host=EcAppParam.gcm_dbServer,
            database=EcAppParam.gcm_dbDatabase,
            user=EcAppParam.gcm_dbUser,
            password=EcAppParam.gcm_dbPassword
        )

        # TB_USER total row count
        l_count = 0
        l_query = """
                    select count(1)
                    from
                        "TB_USER"
                    ;"""

        l_cursor = l_connect1.cursor()
        l_cursor.execute(l_query)
        for l_count, in l_cursor:
            pass

        # choose random row
        l_row_choice = random.randrange(l_count)

        self.m_logger.info('User count: {0}'.format(l_count))
        self.m_logger.info('Row choice: {0}'.format(l_row_choice))

        # retrieve ID of chosen row
        l_id = ''
        l_query = """
                    select "ID"
                    from
                        "TB_USER"
                    order by
                        "ID_INTERNAL"
                    offset {0};""".format(l_row_choice)

        l_cursor = l_connect1.cursor()

        # timing counter
        t0 = time.perf_counter()
        l_cursor.execute(l_query)
        self.m_logger.info('execute(): {0:.3}'.format(time.perf_counter() - t0))
        for l_id, in l_cursor:
            break


        self.m_logger.info('ID: {0}'.format(l_id))
        # close database connection
        l_connect1.close()

        # go to the user's page and wait for the page to load
        self.m_driver.get('http://www.facebook.com/{0}'.format(l_id))
        try:
            # wait for mainContainer
            WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="mainContainer"]')))
        except EX.TimeoutException:
            self.m_logger.critical('Did not find user\'s page mainContainer. Id: {0}'.format(l_id))
            raise

        self.m_logger.info('user page for ID [{0}] loaded'.format(l_id))
        return l_id

    def get_fb_profile(self, p_isOwnFeed=False):
        """
        Downloads the profile of a user. Before calling this method, the user's page must already have been loaded.
        :return: Nothing
        """
        self.m_logger.info("get_fb_profile()")

        # erase all images and xml files in the directory
        if EcAppParam.gcm_verboseModeOn:
            for l_path in [EcAppParam.gcm_appRoot + '*.png', EcAppParam.gcm_appRoot + '*.xml']:
                l_result = subprocess.run(
                    'rm -f ' + l_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                self.m_logger.info('Erasing files : ' + repr(l_result))

        # prefix in the id attribute for all stories blocks (different for user's page and own feed)
        l_storyPrefix = 'tl_unit_'
        if p_isOwnFeed:
            l_storyPrefix = 'hyperfeed_story_id_'

        # wait for the presence of at least one such block
        try:
            WebDriverWait(self.m_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "{0}")]'.format(l_storyPrefix))))
        except EX.TimeoutException as e:
            self.m_logger.warning('could not find prefix: {0}/{1}'.format(l_storyPrefix, repr(e)))
            raise

        self.m_logger.info('presence of {0}'.format(l_storyPrefix))

        # repeat calls to analyze_story until no more stories can be obtained
        # list of story ids to avoid processing them twice
        l_storyList = []
        # a fruitless try occurs when no new stories could be found while scanning all stories on the page
        l_fruitlessTries = 0
        # current y position of the top of the viewport
        l_curY = 0
        # total number of stories retrieved so far
        l_storyCount = 0

        # just in case
        self.m_driver.execute_script('window.scrollTo(0, 0);')

        while l_storyCount <= EcAppParam.gcm_max_story_count and l_fruitlessTries < 3:
            # main loop will continue until the desired number of stories is reached or 3 fruitless
            # tries have occurred
            l_fruitlessTry = True
            self.m_logger.info(
                '### main loop. l_storyCount={0} l_fruitlessTries={1}'.format(l_storyCount, l_fruitlessTries))
            for l_story in self.m_driver.find_elements_by_xpath('//div[contains(@id, "{0}")]'.format(l_storyPrefix)):
                # inner loop: scans all stories present on the page
                try:
                    # get the stories id attribute
                    l_id = l_story.get_attribute('id')
                    if l_id not in l_storyList:
                        # if the story's id is not in the list --> it is a new one

                        # so this cycle is not a fruitless try
                        l_fruitlessTry = False
                        l_fruitlessTries = 0

                        # add the story's id to the list to avoid processing it again
                        l_storyList.append(l_id)

                        # analyze the story (includes scrolling past the story block to trigger the loading
                        # of new ones, if any). This call affects the current y position.
                        l_curY, l_retStory = \
                            self.analyze_story(l_story, l_storyCount, l_curY, p_storyPrefix=l_storyPrefix)

                        l_retStory['date'] = l_retStory['date'].strftime('%Y%m%d %H:%M')
                        l_retStory['date_quoted'] = [d.strftime('%Y%m%d %H:%M') for d in l_retStory['date_quoted']]
                        l_retStory['images'] = [i[:100] + '...' for i in l_retStory['images']]
                        print('json: ' + json.dumps(l_retStory))

                        l_storyCount += 1
                    else:
                        self.m_logger.debug('--- Story already analyzed: ' + l_id)
                except EX.StaleElementReferenceException as e:
                    self.m_logger.warning('Stale element: {0}'.format(repr(e)))
                    continue

            if l_fruitlessTry:
                l_fruitlessTries += 1

            if l_storyCount > EcAppParam.gcm_max_story_count or l_fruitlessTries > 3:
                break

    def get_fb_feed_old(self):
        """
        Get the user's own feed

        :return: Nothing
        """
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
        l_iter_dispo = 0
        for l_story in self.m_driver.find_elements_by_xpath('//div[contains(@id, "{0}")]'.format(l_storyPrefix)):
            try:
                l_curY = self.analyze_story(l_story, l_iter_dispo, l_curY)

                l_iter_dispo += 1
            except EX.StaleElementReferenceException:
                print('***** STALE ! ******')

    def scroll_obfuscate(self, y):
        l_stepCount = random.randint(5,15)

        for i in range(l_stepCount, 0, -1):
            d = l_stepCount * 10
            l_yTarget = y + random.randint(-d/2, d/2)
            self.m_driver.execute_script('window.scrollTo(0, {0});'.format(l_yTarget))
            time.sleep(.01)
            
        self.m_driver.execute_script('window.scrollTo(0, {0});'.format(y))

    def analyze_story(self, p_story, p_iter, p_curY, p_storyPrefix='hyperfeed_story_id_', p_obfuscate=True):
        """
        Story analysis method.
        :param p_story: WebDriver element positioned on the story
        :param p_iter: Story number (starting at 0)
        :param p_curY: Current scrolling Y position in the browser
        :param p_storyPrefix: Prefix of the `id` attribute of the story's outermost `<div>`
        :return: the new y scroll value
        """
        # timing counter
        t0 = time.perf_counter()

        # raw html for this story
        l_html = p_story.get_attribute('outerHTML')

        if EcAppParam.gcm_debugModeOn:
            l_htmlShort = l_html[:500]
            if len(l_html) != len(l_htmlShort):
                l_htmlShort += '...'
            print("-------- {0} --------\n{1}".format(p_iter, l_htmlShort))

        # story ID without prefix
        l_id = p_story.get_attribute('id')
        l_id = re.sub(p_storyPrefix, '', l_id).strip()

        # location and size
        l_location = p_story.location
        l_size = p_story.size

        # detection of abnormal location parameters --> skip story
        if l_location['x'] == 0 or l_location['y'] == p_curY:
            self.m_logger.info('Location anomaly: {0}'.format(l_location))
            return p_curY

        # calculation of scroll parameters
        l_yTop = l_location['y'] - 100 if l_location['y'] > 100 else 0
        l_deltaY = l_yTop - p_curY
        l_curY = l_yTop
        l_overshoot = l_location['y'] + l_size['height'] + 50

        if p_obfuscate:
            self.scroll_obfuscate(l_overshoot)
            self.scroll_obfuscate(l_yTop)
        else:
            # first scroll to the bottom of the story (overshoot) to trigger loading of next stories, if any
            self.m_driver.execute_script('window.scrollTo(0, {0});'.format(l_overshoot))
            # then scroll to the top of the story
            self.m_driver.execute_script('window.scrollTo(0, {0});'.format(l_yTop))

        # previous method with delta, kept for now in reserve
        # self.m_driver.execute_script('window.scrollBy(0, {0});'.format(l_deltaY))

        # waiting for story availability
        # first wait for visibility DOM attribute
        try:
            WebDriverWait(self.m_driver, 15).until(EC.visibility_of(p_story))
        except EX.TimeoutException as e:
            self.m_logger.warning('Story [{0}] failed to become visible: {1}'.format(l_id, repr(e)))

        #l_wait_cycles = 0
        #while not self.m_driver.execute_script('return arguments[0].complete', p_story):
        #    time.sleep(.05)
        #    l_wait_cycles += 1
        #    if l_wait_cycles % 10 == 0:
        #        self.m_logger.info('Wait for complete: {0}'.format(l_wait_cycles))

        #    if l_wait_cycles > 100:
        #        break

        # for safety's sake, wait for the absence of data-ft attribute
        l_dataWait = 0
        while l_dataWait < 100:
            l_data_ft = p_story.get_attribute('data-ft')
            if l_data_ft is None:
                break
            else:
                l_dataWait += 1
                if l_dataWait % 10 == 0:
                    print('l_data_ft [{0}]: {1}'.format(l_dataWait, l_data_ft[:50]))

            time.sleep(.05)

        # build an lxml analyser out of the html
        l_tree = html.fromstring(l_html)

        # DATA: (1) Date(s)
        l_date = None
        l_dateQuoted = []
        for l_dateContainer in p_story.find_elements_by_xpath('.//abbr[contains(@class, "_5ptz")]'):
            l_txtDt = re.sub('\,', '', l_dateContainer.get_attribute('title'))
            try:
                l_dt = datetime.datetime.strptime(l_txtDt, '%A %d %B %Y at %H:%M')
            except ValueError:
                try:
                    l_dt = datetime.datetime.strptime(l_txtDt, '%A %d %B %Y at %I:%M%p')
                except ValueError:
                    l_dt = datetime.datetime.now()

            if EcAppParam.gcm_debugModeOn:
                print('l_txtDt: ' + l_txtDt)

            if l_date is None:
                # first date found considered as main story date
                l_date = l_dt
            else:
                # other dates considered as coming from quoted parts (shared post, ...)
                l_dateQuoted.append(l_dt)

        # DATA: (2) main text
        l_postText = ''
        # text found in the 'userContent' marked section. But 'userContentWrapper' must be avoided
        for l_pt in p_story.find_elements_by_xpath(
                './/div[contains(@class, "userContent") and not(contains(@class, "userContentWrapper"))]'):
            l_ptHtml = l_pt.get_attribute('innerHTML')

            # removes html tags and replaces them with spaces
            if l_ptHtml is not None:
                l_postText = re.sub('<[^>]+>', ' ', l_ptHtml)
                l_postText = re.sub('\s+', ' ', l_postText).strip()

            if l_postText is not None and len(l_postText) > 0:
                break

        # DATA: (3) quoted text
        l_quotedText = ''
        # _5r69 --> Quoted portion (normally) otherwise, class containing 'mtm'
        for l_xpath in ['.//div[@class="_5r69"]', './/div[contains(@class, "mtm")]']:
            for l_quote in p_story.find_elements_by_xpath(l_xpath):
                l_quoteHtml = l_quote.get_attribute('innerHTML')

                # removes html tags and replaces them with spaces
                if l_quoteHtml is not None:
                    l_quotedText = re.sub('<[^>]+>', ' ', l_quoteHtml)
                    l_quotedText = re.sub('\s+', ' ', l_quotedText).strip()

                if l_quotedText is not None and len(l_quotedText) > 0:
                    break

            # if _5r69 yielded tex, 'mtm' must not be used
            if l_quotedText is not None and len(l_quotedText) > 0:
                break

        # DATA: (4) determining from
        # types of shared documents (may be found in the same form as from authors and must thus be eliminated)
        l_shareTypes = ['photo', 'post', 'link', 'event', 'video', 'live video']
        # list of author (no deduplication but order preserved)
        l_from = []
        # dictionary of authors (deduplication but order lost)
        l_fromDict = dict()
        # _5x46 --> whole post header
        # _5vra --> part of the post header containing the names of the post authors

        # first case below correspond to multiple authors and the second to single authors
        for l_xpath in ['//div[contains(@class, "_5x46")]//a[contains(@class, "profileLink")]',
                        '//h5[contains(@class, "_5vra")]//a']:
            for l_profLink in l_tree.xpath(l_xpath):
                # a. full name --> text content of the link
                l_fromName =  l_profLink.text_content()

                # b. FB user name
                l_fromUser = l_profLink.get('href')
                if l_fromUser is not None and len(l_fromUser) > 0:
                    # 'https\:\/\/www\.facebook\.com\/Sergei1970sk'
                    # https://www.facebook.com/solanki.jagdish.75098?hc_ref=NEWSFEED
                    if re.search('\.php\?id=', l_fromUser):
                        # human users
                        l_match = re.search('\.php\?id=(\d+)(&|$)', l_fromUser)
                        if l_match:
                            l_fromUser = l_match.group(1)
                    else:
                        # page users
                        l_match = re.search('\.com/([^?]+)(\?|$)', l_fromUser)
                        if l_match:
                            l_fromUser = l_match.group(1)

                # c. FB user ID
                l_fromId = l_profLink.get('data-hovercard')
                if l_fromId is not None and len(l_fromId) > 0:
                    l_match = re.search('\.php\?id=(\d+)(&|$)', l_fromId)
                    if l_match:
                        l_fromId = l_match.group(1)

                # only record user data if it is not a 'false' user corresponding to a share or like
                if l_fromName not in l_shareTypes:
                    # store both in a list and dict
                    l_from += [(l_fromName, l_fromId, l_fromUser)]
                    l_fromDict[l_fromId] = (l_fromName, l_fromUser)

            if len(l_from) > 0:
                break

        # DATA: (5) shared object list (post, photo, video ...)
        l_sharedList = []
        # _5vra --> part of the post header containing the names of the post authors
        for l_type in l_shareTypes:
            for l in l_tree.xpath('.//h5[contains(@class, "_5vra")]//a[text()="{0}"]'.format(l_type)):
                l_sharedList.append((l_type, l.get('href')))

        # DATA: (6) detection of sponsored content
        l_sponsored = (len(l_tree.xpath('.//a[text()="Sponsored"]')) > 0)

        # raw text from the main header and of the sub-header (quoted content), if any
        l_fromHeader = BrowserDriver.get_unique(l_tree, '//h5[contains(@class, "_5vra")]')
        l_fromHeaderSub = BrowserDriver.get_unique(l_tree, '//h6[contains(@class, "_5vra")]')

        # DATA: (7) determines if the list of authors contains a 'with' marker
        l_hasWith = False
        if re.search('with', l_fromHeader) or re.search('with', l_fromHeaderSub):
            l_hasWith = True

        # DATA: (8) determining story type
        # by default, it is a post
        l_type = 'post'
        if l_sponsored:
            # sponsored type
            l_type = 'sponsored'
        else:
            # cases of share or like of previously existing content
            if re.search('shared|liked', l_fromHeader):
                if re.search('shared', l_fromHeader):
                    l_type = 'share'
                else:
                    l_type = 'like'

                # subtype of share/like given by the type of the first element of the quoted content list
                if len(l_sharedList) > 0:
                    l_type += '/{0}'.format(l_sharedList[0][0])

            # other types of posts
            elif re.search('commented on this', l_fromHeader):
                l_type = 'comment'
            elif re.search('updated (his|her) profile picture', l_fromHeader):
                l_type = 'narcissistic/PP'
            elif re.search('updated (his|her) cover photo', l_fromHeader):
                l_type = 'narcissistic/CP'
            elif re.search('updated (his|her) profile video', l_fromHeader):
                l_type = 'narcissistic/PV'
            else:
                # case of 'people you may know' stories (found only in user's own feed)
                l_fromHeader2 = BrowserDriver.get_unique(l_tree, '//div[contains(@class, "fwn fcg")]')
                # <div class="fwn fcg"><span class="fwb fcb">People you may know</span></div>
                if re.search('People you may know', l_fromHeader2):
                    l_type = 'FB/PYMK'

        # DATA: (9) image extraction
        l_imageList = []
        if EcAppParam.gcm_getImages:
            # gets a full screenshot of the browser viewport
            l_imgStory = Image.open(io.BytesIO(self.m_driver.get_screenshot_as_png()))
            x = l_location['x']
            y = l_location['y'] - l_yTop

            l_baseName = '{0:03}-'.format(p_iter) + l_id

            if EcAppParam.gcm_verboseModeOn:
                # store html source and image of complete story
                l_img = l_imgStory.crop((x, y, x + l_size['width'], y + l_size['height']))

                l_img.save(l_baseName + '.png')

                with open(l_baseName + '.xml', "w") as l_xml_file:
                    l_xml_file.write(l_html)

            # extract actual images from the story, if any
            l_imgCount = 0
            # use, if possible, the div above the <img> tag itself because its size is more often correct
            for l_xpath in ['.//div[./img[contains(@class, "img")]]', './/img[contains(@class, "img")]']:
                for l_image in p_story.find_elements_by_xpath(l_xpath):
                    l_height = l_image.size['height']
                    l_width = l_image.size['width']
                    if l_width >= EcAppParam.gcm_minImageSize and l_height >= EcAppParam.gcm_minImageSize:
                        l_htmlHeight = l_image.get_attribute('height')
                        l_htmlWidth = l_image.get_attribute('width')

                        if EcAppParam.gcm_debugModeOn:
                            print(
                                '*** IMG [{0}] S:({1} {2}) H:({3} {4}): '.format(
                                    l_imgCount, l_width, l_height, l_htmlWidth, l_htmlHeight) +
                                l_image.get_attribute('outerHTML')
                            )

                        # for i in range(0,10):
                        #    print('Loaded: ' + repr(self.m_driver.execute_script('return arguments[0].complete', l_image)))

                        l_img_location = l_image.location
                        xi = l_img_location['x']
                        yi = l_img_location['y'] - l_yTop

                        # do the crop of the whole screen image in order to keep only the image
                        l_imgInStory = l_imgStory.crop((xi, yi, xi + l_width, yi + l_height))
                        if EcAppParam.gcm_verboseModeOn:
                            l_imgInStory.save(l_baseName + '_{0:02}.png'.format(l_imgCount))
                        l_imgCount += 1

                        l_outputBuffer = io.BytesIO()
                        l_imgInStory.save(l_outputBuffer, format='PNG')
                        l_imageList.append(base64.b64encode(l_outputBuffer.getvalue()).decode())

                # if first xpath worked --> no nee to try the second
                if l_imgCount > 0:
                    break

        l_retStory = dict()
        l_retStory['id'] = l_id
        l_retStory['date'] = l_date
        l_retStory['with'] = l_hasWith
        l_retStory['sponsored'] = l_sponsored
        l_retStory['type'] = l_type
        l_retStory['shared'] = l_sharedList
        l_retStory['from_list'] = l_from
        l_retStory['from_dict'] = l_fromDict
        l_retStory['text'] = l_postText
        l_retStory['text_quoted'] = l_quotedText
        l_retStory['date_quoted'] = l_dateQuoted
        l_retStory['images'] = l_imageList

        if EcAppParam.gcm_verboseModeOn:
            print('l_fromHeader   : ' + l_fromHeader)
            print('Id             : ' + l_id)
            print('Sponsored      : ' + repr(l_sponsored))
            print('Type           : ' + l_type)
            print('Shared objects : ' + repr(l_sharedList))
            print('Has with       : ' + repr(l_hasWith))
            print('Date           : ' + repr(l_date))
            print('Dates quoted   : ' + repr(l_dateQuoted))
            print('From           : ' + repr(l_from))
            print('From (dict)    : ' + repr(l_fromDict))
            print('Text           : ' + l_postText)
            print('Quoted Text    : ' + l_quotedText)
            print('Size           : {0}'.format(l_size))
            print('Location       : {0}'.format(l_location))
            print('l_curY         : {0}'.format(p_curY))
            print('l_yTop         : {0}'.format(l_yTop))
            print('l_deltaY       : {0}'.format(l_deltaY))
            print('l_overshoot    : {0}'.format(l_overshoot))

        self.m_logger.info(
            'Processing story {0} complete. Elapsed time: {1:.3}'.format(p_iter, time.perf_counter() - t0))
        return l_curY, l_retStory

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

    # g_browser = 'Firefox'
    g_browser = 'Chrome'

    l_phantomId = 'nicolas.reimen@gmail.com'
    l_phantomPwd = 'murugan!'
    # l_vpn = 'India.Maharashtra.Mumbai.TCP.ovpn'
    l_vpn = None

    l_driver = BrowserDriver(l_phantomId, l_phantomPwd, l_vpn)
    l_driver.go_random()
    #l_driver.get_fb_profile()
    l_driver.log_out()

    l_driver.login_as_scrape(l_phantomId, l_phantomPwd, l_vpn)
    l_driver.go_random()
    l_driver.get_fb_profile()
    l_driver.log_out()

    if EcAppParam.gcm_headless:
        l_driver.close()
