#!/usr/bin/python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
from selenium.webdriver.common.action_chains import ActionChains

import lxml.html as html
import sys

from ec_utilities import *

__author__ = 'Pavan Mahalingam'


# opens a Selenium driven Firefox window
def get_driver():
    if g_browser == 'Firefox':
        # Create a new instance of the Firefox driver
        l_driver = webdriver.Firefox()

        # Resize the window to the screen width/height
        l_driver.set_window_size(1200, 1100)

        # Move the window to position x/y
        l_driver.set_window_position(800, 0)
    else:
        # Create a new instance of the PhantomJS driver
        l_driver = webdriver.PhantomJS()

        # Resize the window to the screen width/height
        l_driver.set_window_size(1200, 1100)

    return l_driver


def login_as_scrape(p_user, p_passwd):
    l_driver = get_driver()

    l_driver.get('http://www.facebook.com')

    try:
        l_userInput = WebDriverWait(l_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//td/input[@id="email"]')))

        l_userInput.send_keys(p_user)

        l_pwdInput = WebDriverWait(l_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//td/input[@id="pass"]')))

        l_pwdInput.send_keys(p_passwd)

        # loginbutton
        l_driver.find_element_by_xpath('//label[@id="loginbutton"]/input').click()

        # wait for mainContainer
        WebDriverWait(l_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="mainContainer"]')))
    except EX.TimeoutException:
        print('Did not find user ID input or post-login mainContainer')
        return None

    return l_driver

# get a unique element attribute through lxml, with a warning mark ('¤')
# inside the string if more than one was found
def get_unique_attr(p_frag, p_xpath, p_attribute):
    return '¤'.join([str(l_span.get(p_attribute)) for l_span in p_frag.xpath(p_xpath)]).strip()

# get a unique text element through lxml, with a warning mark ('¤')
# inside the string if more than one was found
def get_unique(p_frag, p_xpath):
    return '¤'.join([str(l_span.text_content()) for l_span in p_frag.xpath(p_xpath)]).strip()

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
            l_date = get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')
            l_from = get_unique(l_tree, '//a[contains(@class, "profileLink")]')

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

def get_profile_ff(p_driver):
    EcLogger.cm_logger.info("get_profile()")

    WebDriverWait(p_driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "hyperfeed_story_id_")]')))

    EcLogger.cm_logger.info("presence of hyperfeed_story_id_")


    WebDriverWait(p_driver, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "more_pager_pagelet_")]')))

    EcLogger.cm_logger.info("presence of more_pager_pagelet_")

    l_expansionCount = 3

    while True:
        l_pagers_found = 0
        l_last_pager = None
        for l_last_pager in p_driver.find_elements_by_xpath('//div[contains(@id, "more_pager_pagelet_")]'):
            l_pagers_found += 1

        EcLogger.cm_logger.info('Expanding pager #{0}'.format(l_pagers_found))
        if l_last_pager is not None:
            p_driver.execute_script("return arguments[0].scrollIntoView();", l_last_pager)

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

    p_driver.execute_script('window.scrollTo(0, 0);')
    l_curY = 0
    l_iter_disp = 0
    for l_story in p_driver.find_elements_by_xpath('//div[contains(@id, "hyperfeed_story_id_")]'):
        try:
            l_html = l_story.get_attribute('outerHTML')
            l_id = l_story.get_attribute('id')
            l_id = re.sub('hyperfeed_story_id_', '', l_id).strip()
            # extract a full xml/html tree from the page
            l_tree = html.fromstring(l_html)

            # class="_5ptz"
            l_date = get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')
            l_from = get_unique(l_tree, '//a[contains(@class, "profileLink")]')

            l_htmlShort = l_html[:500]
            if len(l_html) != len(l_htmlShort):
                l_htmlShort += '...'
            print("-------- {0} --------\n{1}".format(l_iter_disp, l_htmlShort))

            l_location = l_story.location

            print('Id       : ' + l_id)
            print('Date     : ' + l_date)
            print('From     : ' + l_from)
            print('Location : {0}'.format(l_location))
            print('l_curY   : {0}'.format(l_curY))

            l_yTop = l_location['y'] - 100 if l_location['y'] > 100 else 0
            l_deltaY = l_yTop - l_curY
            l_curY = l_yTop

            print('l_yTop   : {0}'.format(l_yTop))
            print('l_deltaY : {0}'.format(l_deltaY))

            #p_driver.execute_script("return arguments[0].scrollIntoView();", l_story)
            #p_driver.execute_script("window.scrollBy(0, -100);")
            p_driver.execute_script('window.scrollBy(0, {0});'.format(l_deltaY))
            WebDriverWait(l_driver0, 15).until(EC.visibility_of(l_story))

            l_baseName = '{0:03}-'.format(l_iter_disp) + l_id
            p_driver.get_screenshot_as_file(l_baseName + '.png')

            #l_story.screenshot(l_baseName + '_.png')
            with open(l_baseName + '.xml', "w") as l_xml_file:
                l_xml_file.write(l_html)

            l_iter_disp += 1
        except EX.StaleElementReferenceException:
            print('***** STALE ! ******')


def old_1():
    WebDriverWait(l_driver0, 15).until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@id, "hyperfeed_story_id_")]')))

    l_iter = 0
    while True:
        print('+++++++++++++++++ {0} +++++++++++++++++'.format(l_iter))
        l_iter += 1

        l_iter_inner = 0
        for l_story in l_driver0.find_elements_by_xpath('//div[contains(@id, "hyperfeed_story_id_")]'):
            try:
                l_html = l_story.get_attribute('outerHTML')

                # extract a full xml/html tree from the page
                l_tree = html.fromstring(l_html)

                # class="_5ptz"
                l_date = get_unique_attr(l_tree, '//abbr[contains(@class, "_5ptz")]', 'title')
                l_from = get_unique(l_tree, '//a[contains(@class, "profileLink")]')

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
    g_browser = 'xxx'

    l_phantomId = 'aziz.sharjahulmulk@gmail.com'
    l_phantomPwd = '15Eyyaka'

    EcLogger.cm_logger.info("logging in ...")
    l_driver0 = login_as_scrape(l_phantomId, l_phantomPwd)

    if g_browser == 'Firefox':
        get_profile_ff(l_driver0)
    else:
        get_profile_pjs(l_driver0)
