from .utils import get_logger, get_partial_str_matches_in_list
from .lastfm import get_lastfm_track_tags
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
SCOPE = 'playlist-modify-public playlist-modify-private'


class PlaylistSplitter:
    def __init__(self, src_playlist_id):
        # Load variables from the .env file
        load_dotenv()

        # INPUTS
        self.playlist_id = src_playlist_id

        # FILES
        self.log_file_path = f"playlist_splitter_{NOW}.log"
        self.playlist_data_file_path = f"playlist_splitter_{NOW}.csv"

        # STUFF
        self.spotify_username = os.getenv("SPOTIPY_USERNAME")
        self.logger = get_logger(self.log_file_path)
        self.sp_client = self._get_sp_client()
        self.tracks_data = []
        self.failed_tracks = []

    def _get_sp_client(self):
        """ authenticate with the spotify client """
        sp_client = self.sp_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))
        self.logger.info("authenticated with spotify")
        return sp_client

    def get_playlist_tracks_genres(self):
        """ get the genres of all the tracks in a given playlist """
        offset = 0
        limit = 100  # maximum limit per request
        num_of_processed_tracks = 0
        already_prcessed_tracks = [f"{t['track_name']} - {t['artist_name']}" for t in self.tracks_data]
        self.logger.info(f"getting genres for playlist ID {self.playlist_id}...")

        while True:
            results = self.sp_client.playlist_items(self.playlist_id, offset=offset, limit=limit)
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
                        self.tracks_data.append(track_data)
                        self.logger.info(f"got genres for: {artist_name} - {track_name}")
                    else:
                        self.logger.info(f"already processed '{artist_name} - {track_name}', skipping..")
                    num_of_processed_tracks += 1
                    self.logger.info(f"done with {num_of_processed_tracks} tracks")
                except Exception as e:
                    self.logger.error(f"FAILED fetching for: \ntrack: {track}\nerror: {e}")
                    self.failed_tracks.append(track)
                    raise
            if not tracks:
                break  # No more tracks
            offset += limit
            self.logger.info(f"processed {offset} tracks...")
        self.logger.info(f"done! processed a total of {offset} tracks")
        self.__save_playlist_data_to_csv()

    def __save_playlist_data_to_csv(self):
        """ save the playlist tracks data to a CSV file """
        with open(self.playlist_data_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=GENRE_CSV_HEADERS)
            writer.writeheader()
            for track in self.tracks_data:
                writer.writerow(track)
        self.logger.info(f"saved CSV to: {self.playlist_data_file_path}")

    def load_playlist_data_from_csv(self, csv_file_path: str):
        """ load the playlist tracks data form a previously saved CSV """
        data = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for track in reader:
                track['genres'] = ast.literal_eval(track['genres'])
                data.append(track)
        self.tracks_data = data
        self.logger.info(f"loaded {len(data)} tracks!")

    def __get_track_genres(self, artist_name: str, track_name: str):
        """ get a given track's genres. kind of LOL """
        return get_lastfm_track_tags(artist_name, track_name, self.logger)

    def _save_tracks_from_genres_to_csv(self, genre: str) -> str:
        """ save tracks of the given genre from the playlist to a CSV """
        genre_csv_path = f"{genre}_{NOW}.csv"
        search_genre = genre.lower()
        num_of_songs_in_genre = 0

        with open(genre_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=GENRE_CSV_HEADERS)
            writer.writeheader()

            for track in self.tracks_data:
                # save only tracks with partially/fully matching genres
                track_genres = [element.lower() for element in track['genres']]
                matching_genres = get_partial_str_matches_in_list(track_genres, search_genre)
                if matching_genres:
                    track['genres'] = matching_genres
                    writer.writerow(track)
                    num_of_songs_in_genre += 1
        self.logger.info(f"saved {num_of_songs_in_genre} tracks to CSV to: {genre_csv_path}")
        return genre_csv_path

    def _create_playlist_from_csv(self, csv_file_path, playlist_name, public=True):
        """ create a playlist with tracks from a given CSV """
        playlist = self.sp_client.user_playlist_create(
            user=self.spotify_username,
            name=playlist_name,
            public=True if public == True else False,
        )
        self.logger.info(f"created plalyist '{playlist_name}'")

        track_ids = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for track in reader:
                track_id = track.get('track_id')
                if track_id:
                    track_ids.append(track_id)

        self.sp_client.playlist_add_items(
            playlist_id=playlist['id'],
            items=track_ids
        )
        self.logger.info(f"added {len(track_ids)} songs to '{playlist_name}'")

    def create_playlist_of_genre(self, playlist_name, genre, public=True):
        """ create a playlist with tracks from a given genre """
        genre_csv_path = self._save_tracks_from_genre_to_csv(genre)  # save genre's track to a CSV
        self._create_playlist_from_csv(genre_csv_path, playlist_name, public)  # create the playlist
