import requests
from bs4 import BeautifulSoup

LASTFM_BASE_URL = 'https://www.last.fm/music'


def get_lastfm_track_tags(artist_name, track_name, logger):
    """ get the track's tags from lastfm, mostly the tags are the track's genres. please kill me. """
    tags = []
    artist_name_f = artist_name.replace(" ", "+")
    track_name_f = track_name.replace(" ", "+")
    scrape_url = f"{LASTFM_BASE_URL}/{artist_name_f}/_/{track_name_f}/+tags"

    response = requests.get(scrape_url)
    if response.status_code == 200:
        # extract tags from the <a> elements within the class 'link-block-target'
        soup = BeautifulSoup(response.text, 'html.parser')
        tag_items = soup.find_all('a', {'class': 'link-block-target'})
        for tag_item in tag_items:
            tags.append(tag_item.text)
    else:
        logger.error(f"ERROR - failed getting tags for '{artist_name} - {track_name}': {response.status_code}")
    return tags
