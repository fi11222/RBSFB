__author__ = 'Pavan Mahalingam'


class LocalParam:
    """
    Static class containing the global parameters which (may) depend on the environment (dev/qualif/prod).
    """

    #: True --> Production environment
    gcm_prodEnv = False

    # HTTP server parameters
    #: domain name (= 'localhost' except fro prod environment)
    gcm_appDomain = 'localhost'
    #: TCP/IP port number on which the server is listening (use two different ones to have multiple
    #: servers on the same machine)
    gcm_httpPort = 9080

    # Database parameters
    #: Database server name (normally 'localhost' but could be different in non-prod env)
    gcm_dbServer = 'localhost'

    #: Database connection user name
    gcm_dbUserLocal = 'postgres'
    #: Database connection password
    gcm_dbPasswordLocal = 'murugan!'

    # Logging
    #: If True then maximum level of logging
    gcm_debugModeOn = True
    #: If True then only INFO level log messages are kept
    gcm_verboseModeOn = True

    #: If True then do not load browscap
    gcm_skipBrowscap = True

    #: Address of the sender for the e-mail messages generated by the logging system
    gcm_mailSender = 'nicolas.reimen@gmail.com'
    #: Address of the smtp server to send the e-mail messages generated by the logging system
    gcm_smtpServer = 'smtp.gmail.com'
    # Smtp2Go uses the same authentication sequence as Gmail
    #gcm_smtpServer = 'mail.smtp2go.com'


    #: If True, use Gmail TLS authentication to connect to the smtp server (SES)
    gcm_gmailSmtp = True

    #: Gmail/TLS password
    gcm_mailSenderPassword = '16Edhenas'

    #: If True, use Amazon AWS specific method to connect to the smtp server (SES)
    gcm_amazonSmtp = False

    #: Amazon SES ID (not used)
    gcm_sesIamUser = ''
    #: Amazon SES user
    gcm_sesUserName = ''
    #: Amazon SES pwd
    gcm_sesPassword = ''

    #: global root path
    gcm_appRoot = '/home/fi11222/disk-partage/Dev/RBSFB/'

