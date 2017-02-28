#!/usr/bin/python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

import lxml.html as html
import time

__author__ = 'Pavan Mahalingam'


# opens a Selenium driven Firefox window
def get_driver():
    if g_browser == 'Firefox':
        # Create a new instance of the Firefox driver
        l_driver = webdriver.Firefox()
    else:
        # Create a new instance of the PhantomJS driver
        l_driver = webdriver.PhantomJS()

    # Resize the window to the screen width/height
    l_driver.set_window_size(1200, 1100)

    # Move the window to position x/y
    l_driver.set_window_position(800, 0)

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
# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB scraping web service for ROAD B SCORE                   |')
    print('|                                                            |')
    print('| POST request sending test client                           |')
    print('|                                                            |')
    print('| v. 1.0 - 28/02/2017                                        |')
    print('+------------------------------------------------------------+')

    g_browser = 'Firefox'

    l_phantomId = 'karim.elmoulaid@gmail.com'
    l_phantomPwd = '15Eyyaka'

    l_driver0 = login_as_scrape(l_phantomId, l_phantomPwd)

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