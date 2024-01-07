from utils import get_logger, get_partial_str_matches_in_list
from lastfm import get_lastfm_track_tags
import csv
import os
from datetime import datetime
import ast

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

NOW = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
GENRE_CSV_HEADERS = ["track_id", "genres", "track_name", "artist_name"]
REDIRECT_URI = 'http://localhost:8888/callback/'
SPOTIFY_AUTH_SCOPE = 'playlist-modify-public playlist-modify-private'


class PlaylistSplitter:
    def __init__(self):
        # Load variables from the .env file
        load_dotenv()

        # FILES
        self.log_file_path = f"playlist_splitter_{NOW}.log"

        # STUFF
        self.logger = get_logger(self.log_file_path)
        self.sp_client = self._get_sp_client()
        self.tracks = []
        self.failed_tracks = []

    def _get_sp_client(self):
        """ authenticate with the spotify client """
        sp_client = self.sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=REDIRECT_URI,
            scope=SPOTIFY_AUTH_SCOPE
        ))
        self.logger.info("authenticated with spotify")
        return sp_client

    # USABLE-LEVEL FUNCTIONS
    def analyze_playlist(self, playlist_id: str):
        """ get and save a playlist's genres to CSV """
        self._get_all_tracks_genres(playlist_id)
        tracks_file_path = self._save_tracks_to_csv(playlist_id)
        return tracks_file_path

    def create_playlist_of_genre(self, genre, playlist_name='', playlist_id='') -> str:
        """ create a playlist with tracks from a given genre, or add them to an existing playlist """

        if not playlist_id and playlist_name:
            playlist_id = self.__create_playlist(playlist_name)
        elif not playlist_name and playlist_id:
            self.logger(f"adding songs to and existing playlist with ID: '{playlist_id}'")
        else:
            raise ValueError("supply one of playlist_id or playlist_name!")

        genre_csv_path = self._save_genre_tracks_to_csv(genre)
        self._add_tracks_from_csv_to_playlist(genre_csv_path, playlist_id)
        self.logger.info(f"created playlist '{playlist_name}' with ID: '{playlist_id}'")
        self.logger.info(f"genre's tracks are saved here: '{genre_csv_path}'")

        return genre_csv_path

    def load_tracks_from_csv(self, csv_file_path: str):
        """ load the playlist tracks from a previously saved CSV """
        data = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for track in reader:
                track['genres'] = ast.literal_eval(track['genres'])
                print(track['genres'])
                data.append(track)
        self.tracks = data
        self.logger.info(f"loaded {len(data)} tracks!")

    # LOW-LEVEL functions
    def _get_all_tracks_genres(self, playlist_id: str):
        """ save the genres of all the tracks in the playlist """
        offset = 0
        limit = 100  # maximum limit per request
        num_of_processed_tracks = 0
        already_prcessed_tracks = [f"{t['track_name']} - {t['artist_name']}" for t in self.tracks]
        self.logger.info(f"getting genres for playlist ID {playlist_id}...")
        while True:
            results = self.sp_client.playlist_items(playlist_id, offset=offset, limit=limit)
            tracks = results['items']
            for track in tracks:
                try:
                    artist_name = track['track']['artists'][0]['name']
                    track_name = track['track']['name']
                    if f"{track_name} - {artist_name}" not in already_prcessed_tracks:
                        genres = self.__get_track_genres(artist_name, track_name)
                        track_data = {
                            "track_id": track['track']['id'],
                            "genres": genres,
                            "artist_name": artist_name,
                            "track_name": track_name
                        }
                        self.tracks.append(track_data)
                        self.logger.debug(f"got genres for: {artist_name} - {track_name}")
                    else:
                        self.logger.debug(f"already processed '{artist_name} - {track_name}', skipping..")
                    num_of_processed_tracks += 1
                    self.logger.debug(f"done with {num_of_processed_tracks} tracks")
                except Exception as e:
                    self.logger.error(f"FAILED fetching for: \ntrack: {track}\nerror: {e}")
                    self.failed_tracks.append(track)
                    raise
            if not tracks:
                break  # No more tracks
            offset += limit
            self.logger.info(f"processed {offset} tracks...")
        self.logger.info(f"done! processed a total of {offset} tracks")

    def _save_genre_tracks_to_csv(self, genre: str) -> str:
        """ save tracks of the given genre from the playlist to a CSV """
        genre_csv_path = f"{genre}_{NOW}.csv"
        search_genre = genre.lower()
        num_of_songs_in_genre = 0

        with open(genre_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=GENRE_CSV_HEADERS)
            writer.writeheader()

            # save only tracks with partially/fully matching genres
            for track in self.tracks:
                track_genres = [element.lower() for element in track['genres']]
                matching_genres = get_partial_str_matches_in_list(track_genres, search_genre)
                if matching_genres:
                    track['genres'] = matching_genres
                    writer.writerow(track)
                    num_of_songs_in_genre += 1
        self.logger.info(f"saved {num_of_songs_in_genre} tracks to CSV to: {genre_csv_path}")
        return genre_csv_path

    def _add_tracks_from_csv_to_playlist(self, csv_file_path, playlist_id):
        """ create a playlist with tracks from a given CSV """
        tracks_num = 0
        existing_track_ids = self.__get_existing_track_ids_in_playlist(playlist_id)
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for track in reader:
                track_id = track['track_id']
                if track_id not in existing_track_ids:
                    self.sp_client.playlist_add_items(
                        playlist_id=playlist_id,
                        items=[track_id]
                    )
                    self.logger.info(f"added '{track_id}' to playlist")
                else:
                    self.logger.info(f"track with ID '{track_id}' already exists in playlist, skipping..")
                tracks_num += 1
                self.logger.info(f"done with {tracks_num} tracks")
        self.logger.info(f"added {tracks_num} songs to playlist with id '{playlist_id}'")

    def _save_tracks_to_csv(self, playlist_id):
        """ save the tracks to a CSV file """
        tracks_file_path = f"{playlist_id}_genres_{NOW}.csv"
        with open(tracks_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=GENRE_CSV_HEADERS)
            writer.writeheader()
            for track in self.tracks:
                writer.writerow(track)
        self.logger.info(f"saved tracks to: {tracks_file_path}")
        return tracks_file_path

    # PASTEN-LEVEL FUNCTIONS
    def __get_track_genres(self, artist_name: str, track_name: str):
        """ get a given track's genres. kind of LOL """
        return get_lastfm_track_tags(artist_name, track_name, self.logger)

    def __create_playlist(self, playlist_name):
        """ create a playlist, return its ID """
        playlist = self.sp_client.user_playlist_create(
            user=os.getenv("SPOTIPY_USERNAME"),
            name=playlist_name,
            public=True,
        )
        self.logger.info(f"created playlist '{playlist_name}'")
        return playlist['id']

    def __get_existing_track_ids_in_playlist(self, playlist_id):
        """ get existing track IDs in a playlist """
        offset = 0
        limit = 100  # maximum limit per request
        self.logger.info(f"getting track IDs from playlist ID {playlist_id}...")
        track_ids = []
        while True:
            results = self.sp_client.playlist_items(playlist_id, offset=offset, limit=limit)
            tracks = results['items']
            track_ids.extend([track['track']['id'] for track in tracks])
            if not tracks:
                break  # No more tracks
            offset += limit
        self.logger.info(f"done! got IDs of {offset} tracks")
        return track_ids
