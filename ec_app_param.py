#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
from ec_local_param import LocalParam

__author__ = 'Pavan Mahalingam'


class EcAppParamOld:
    """
    Static class containing all the global parameters which do not depend on the environment (dev/qualif/prod).
    """

    # transfer of local params from LocalParam to EcAppParam
    gcm_prodEnv = LocalParam.gcm_prodEnv
    gcm_appDomain = LocalParam.gcm_appDomain
    gcm_httpPort = LocalParam.gcm_httpPort
    gcm_dbServer = LocalParam.gcm_dbServer
    gcm_dbUserLocal = LocalParam.gcm_dbUserLocal
    gcm_dbPasswordLocal = LocalParam.gcm_dbPasswordLocal
    gcm_debugModeOn = LocalParam.gcm_debugModeOn
    gcm_verboseModeOn = LocalParam.gcm_verboseModeOn
    gcm_mailSender = LocalParam.gcm_mailSender
    gcm_smtpServer = LocalParam.gcm_smtpServer
    gcm_amazonSmtp = LocalParam.gcm_amazonSmtp
    gcm_sesIamUser = LocalParam.gcm_sesIamUser
    gcm_sesUserName = LocalParam.gcm_sesUserName
    gcm_sesPassword = LocalParam.gcm_sesPassword
    gcm_appRoot = LocalParam.gcm_appRoot
    gcm_gmailSmtp = LocalParam.gcm_gmailSmtp
    gcm_mailSenderPassword = LocalParam.gcm_mailSenderPassword
    gcm_browser = LocalParam.gcm_browser
    gcm_headless = LocalParam.gcm_headless
    gcm_expansionCount = LocalParam.gcm_expansionCount
    gcm_max_story_count = LocalParam.gcm_max_story_count
    gcm_getImages = LocalParam.gcm_getImages
    gcm_startGathering = LocalParam.gcm_startGathering
    gcm_debugToDB = LocalParam.gcm_debugToDB


# general parameters -----------------------------------------------------------------------------------------------
class EcAppParamGeneral(LocalParam):
    """
    General application parameters
    """
    #: Static files root (copied from :any:`LocalParam`)
    gcm_staticRoot = LocalParam.gcm_appRoot
    #: Application name (used in many contexts like logger names, cookie name, etc)
    gcm_appName = 'RBSFB'
    #: Application version (dev version with three figures)
    gcm_appVersion = '0.0.0'
    #: App description (used in title of HTML pages ...)
    gcm_appTitle = 'FB scraping Web Service for ROAD B SCORE'


# HTTP server parameters -------------------------------------------------------------------------------------------
class EcAppParamHttp(LocalParam):
    """
    HTTP server parameters
    """
    #: Cookie lifetime in days (100 years)
    gcm_cookiePersistence = 365*100
    #: Cookie name for the terminal ID
    gcm_sessionName = 'ECTerminalID_{0}'.format(EcAppParamGeneral.gcm_appName)


# Database parameters ----------------------------------------------------------------------------------------------
class EcAppParamDatabase(LocalParam):
    """
    Database parameters
    """
    #: Database name
    gcm_dbDatabase = 'RBSFB'
    #: Database username (copied from :any:`LocalParam`)
    gcm_dbUser = LocalParam.gcm_dbUserLocal
    #: Database password (copied from :any:`LocalParam`)
    gcm_dbPassword = LocalParam.gcm_dbPasswordLocal
    #: Min size of DB connection pool
    gcm_connectionPoolMinCount = 3
    #: Max size of DB connection pool
    gcm_connectionPoolMaxCount = 10
    #: Flag to disable the connection pool feature. If `True` then new connection creation on each request.
    #: Not active at the moment.
    gcm_noConnectionPool = False


# Logging parameters -----------------------------------------------------------------------------------------------
class EcAppParamLogging(LocalParam):
    """
    Logging parameters
    """
    #: Recipients of e-mail messages generated by the logging system
    gcm_mailRecipients = ['nicolas.reimen@gmail.com', 'nrtmp@free.fr']
    #: Location of CSV log file
    gcm_logFile = os.path.join(EcAppParamGeneral.gcm_appRoot, 'Log/ec_log.csv')


# Facebook specific parameters -------------------------------------------------------------------------------------
class EcAppParamFacebook(LocalParam):
    """
    Facebook download parameters
    """
    #: Average browser driver life span (in hours)
    gcm_bdLifeAverage = 2
    #: +/- value (in hours) around average between which the browser driver life span is chosen at random
    gcm_bdLifeDiameter = .25
    #: Minimum size of images to be downloaded (in both directions)
    gcm_minImageSize = 100
    #: True --> Expand comments list for each story
    gcm_expandComments = True
    #: Version of the FB API
    gcm_api_version = 'v2.6'
    #: max number of posts retrieved from a page
    gcm_max_post = 500

    #: max number of days a post will be updated after its creation
    gcm_days_depth = 14
    #: number of days after which the detailed liked list of a post will be fetched
    gcm_likes_depth = 8
    #: number of elements retrieved in one request (API param)
    gcm_limit = 100
    #: wait period after a request limit hit (in seconds)
    gcm_wait_fb = 60 * 60
    #: number of requests after which the token must be renewed
    gcm_token_lifespan = 2000


# Browser driver parameters ----------------------------------------------------------------------------------------
class EcAppParamBrowser(LocalParam):
    """
    Browser driver parameters
    """
    #: Headless browser screen size (Width)
    gcm_headlessWidth = 1200
    #: Headless browser screen size (Height)
    gcm_headlessHeight = 2000
    #: Non-headless browser screen size (Width)
    gcm_width = 1200
    #: Non-headless browser screen size (Height)
    gcm_height = 1000


# Results display parameters ---------------------------------------------------------------------------------------
class EcAppParamDisplay(LocalParam):
    """
    Display application parameters
    """
    #: Maximum number of sessions to show
    gcm_sessionDisplayCount = 300


class EcAppParam(EcAppParamDisplay,
                 EcAppParamBrowser,
                 EcAppParamFacebook,
                 EcAppParamLogging,
                 EcAppParamDatabase,
                 EcAppParamHttp,
                 EcAppParamGeneral):
    """
    Static class containing all the global parameters which do not depend on the environment (dev/qualif/prod).
    """


class TestA:
    cm1 = 'toto'


class TestB(TestA):
    cm2 = 'tutu'

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print(TestA.cm1)
    print(TestB.cm1)

    print(EcAppParam.gcm_httpPort)
