#!/usr/bin/python
from __future__ import print_function
import urllib2, os, sys, time, smtplib
from datetime import datetime
import feedparser

import secrets

def get_playlist_id(webcast_url):
    return webcast_url.split("#")[1].split(",")[-1]

def get_yt_url(webcast_url):
    """
        Returns the full url to the YT Atom feed, given the webcast url
    """
    playlist_id = get_playlist_id(webcast_url)
    return "http://gdata.youtube.com/feeds/api/playlists/%s" % playlist_id

def fetch_feed(webcast_url):
    """
        Returns the feedparser representation of the Atom feed.
    """
    yt_url = get_yt_url(webcast_url)

    try:
        response = urllib2.urlopen(yt_url)
    except urllib2.HTTPError as e:
        print("Failed to fetch Atom feed; error was:")
        print(e)
        return False

    return feedparser.parse(response.read())

def get_cache_path(playlist_id):
    return os.path.join(os.path.dirname(__file__), ".cache-%s" % playlist_id)

def get_last_updated_time(webcast_url):
    pl_id = get_playlist_id(webcast_url)
    path = get_cache_path(pl_id)

    if not os.path.exists(path):
        return datetime.min

    with open(path) as f:
        ts = datetime.fromtimestamp(float(f.read()))
    return ts

def update_cache_time(webcast_url):
    pl_id = get_playlist_id(webcast_url)
    path = get_cache_path(pl_id)

    with open(path, "w") as f:
        f.write(str(time.time()))


def check_new(webcast_url):
    feed = fetch_feed(webcast_url)
    last_updated = get_last_updated_time(webcast_url)
    new_items = []

    for entry in feed.entries:
        if datetime.fromtimestamp(time.mktime(entry.published_parsed)) > last_updated:
            new_items.append(entry)

    if len(new_items) > 0:
        send_email(feed['feed'].title, new_items)

    update_cache_time(webcast_url)

def pluralize(num):
    if num == 1:
        return ''
    return 's'

def send_email(feed_title, new_items):
    gmail_user = secrets.EMAIL_USER
    gmail_pwd = secrets.EMAIL_PASS
    FROM = "Webcast Notifier <%s>" % gmail_user
    TO = [secrets.TO_EMAIL] #must be a list
    num_new_items = len(new_items)
    SUBJECT = "%s new video%s in %s!" % (num_new_items, pluralize(num_new_items), feed_title)
    TEXT = "\n".join([entry.link for entry in new_items])

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        #server = smtplib.SMTP(SERVER) 
        server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        #server.quit()
        server.close()
    except:
        print("failed to send mail")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Provide the url to the webcast.")
    else:
        check_new(sys.argv[1])
