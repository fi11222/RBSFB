#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Pavan Mahalingam'

import requests
import json
import random

def send(p_AT, p_pageID):
    l_pageId = p_pageID
    l_accessToken = p_AT

    print('------------ SEND -----------------')
    # page info (not needed, just for checking)
    l_request = ('https://graph.facebook.com/{0}/{1}?access_token={2}' +
                 '&fields=id,name,access_token').format('v2.8', l_pageId, l_accessToken)
    print('-->' + l_request)

    r = requests.get(l_request)
    print('   Status Code: {0}'.format(r.status_code))

    l_response = r.text
    print('   >> ' + l_response)

    # posting message
    l_request = ('https://graph.facebook.com/{0}/{1}/feed?access_token={2}').format('v2.8', l_pageId, l_accessToken)
    print('-->' + l_request)

    l_message = 'Message number: {0}'.format(random.randint(1,1000))
    print('   Message: ' + l_message)
    r = requests.post(l_request, {'message': l_message})
    print('   Status Code: {0}'.format(r.status_code))

    l_response = r.text
    print('   >> ' + l_response)


def receive(p_AT, p_pageID):
    l_pageId = p_pageID
    l_accessToken = p_AT

    print('------------ RECEIVE -----------------')

    # page info (in this case it is needed, in order to retrieve the page access token)
    l_request = ('https://graph.facebook.com/{0}/{1}?access_token={2}' +
                 '&fields=id,name,access_token').format('v2.8', l_pageId, l_accessToken)
    print('-->' + l_request)

    r = requests.get(l_request)
    print('   Status Code: {0}'.format(r.status_code))

    l_response = r.text
    print('   >> ' + l_response)

    # page access token
    l_pageAT = None
    if r.status_code == 200:
        l_responseData = json.loads(l_response)
        l_pageAT = l_responseData['access_token']
        print('Page Access Token : {0}'.format(l_pageAT))

    # page feed
    l_request = ('https://graph.facebook.com/{0}/{1}/feed?access_token={2}').format('v2.8', l_pageId, l_accessToken)
    print('-->' + l_request)

    r = requests.get(l_request)
    print('   Status Code: {0}'.format(r.status_code))

    l_response = r.text
    print('   >> ' + l_response)

    # retrieve post ID
    if r.status_code == 200:
        l_responseData = json.loads(l_response)
        # here I assume that the post is the first in the feed. In practice, it may be a little more complicated
        l_postId = l_responseData['data'][0]['id']
        print('Post ID : {0}'.format(l_postId))

        l_request = ('https://graph.facebook.com/{0}/{1}?access_token={2}' +
                     '&fields=id,message,from').format('v2.8', l_postId, l_accessToken)
        print('-->' + l_request)

        r = requests.get(l_request)
        print('   Status Code: {0}'.format(r.status_code))

        l_response = r.text
        print('   >> ' + l_response)

        # retrieve author ID
        if r.status_code == 200:
            l_responseData = json.loads(l_response)
            l_personId = l_responseData['from']['id']

            print('Person ID : {0}'.format(l_personId))

            l_request = ('https://graph.facebook.com/{0}/{1}?access_token={2}').format('v2.8', l_personId, l_accessToken)
            print('-->' + l_request)

            r = requests.get(l_request)
            print('   Status Code: {0}'.format(r.status_code))

            l_response = r.text
            print('   >> ' + l_response)

        # post deletion (optional. If not done, then page access token not needed)
        if l_pageAT is not None:
            l_request = ('https://graph.facebook.com/{0}/{1}?access_token={2}').format('v2.8', l_postId, l_pageAT)
            print('-->' + l_request)

            r = requests.get(l_request)
            print('   Status Code: {0}'.format(r.status_code))

            l_response = r.text
            print('   >> ' + l_response)


# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB scraping web service for ROAD B SCORE                   |')
    print('|                                                            |')
    print('| User ID transmission test script                           |')
    print('|                                                            |')
    print('| v. 1.1 - 19/02/2017                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

    l_pageID = '1644087245606719'

    # token associated with the User ID to be transmitted
    l_senderToken = 'EAACEdEose0cBAOfIxtMEgSJSZBBhAy0um6ZBZCL0y6fqK3NTNgCIqZB3jSXvILitOumYvg0kUH6IFpUUYRaR5mZArnyZADpp8ErFZAu5PuGTAnHToSsFC79GFCrRq2KxGYvAhRZAyLVeHLo3o3Kb90Rb5Gj8eMDfEZCkH4mbFP6acmTrR2iBH3BQNkcb8DmbDLDgZD'

    # token associated with a user who has admin privileges for the page (required for post deletion)
    l_receiverToken = 'EAACEdEose0cBAPKKAhvgN97rATWmZCA14H7aR6ZAo333Csd1PJ0o7UF68aakFygmF7aoPcUQqi1sZCw43UCZAdLeXbmlcH9G8iDYWtmKYPed2tgzXvYpxKGYKpl21F0Qt3yicKG9Y4Lc962bZAUxhg4tDOTcZBDZAcSkH0ZAjnz6BfZC6Subra9f6RawvsJsTZA7gZD'

    send(l_senderToken, l_pageID)
    receive(l_receiverToken, l_pageID)


