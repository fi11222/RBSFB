#!/usr/bin/python3
# -*- coding: utf-8 -*-

from rbs_fb_connect import *

__author__ = 'Pavan Mahalingam'

class BulkDownloader:
    """
    Bogus class used to isolate the bulk downloading (FB API) features.
    """
    def __init__(self, p_browser_driver):
        # Local copy of the browser Driver
        self.m_driver = p_browser_driver.m_driver
        self.m_browserDriver = p_browser_driver

        # instantiates class logger
        self.m_logger = logging.getLogger('BulkDownloader')