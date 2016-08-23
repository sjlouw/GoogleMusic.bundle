import random
import string
import datetime
from gmusic import GMusic, CallFailure, API

ART            = 'art-default.jpg'
ICON           = 'icon-default.png'
SEARCH_ICON    = 'icon-search.png'
PREFS_ICON     = 'icon-prefs.png'
PREFIX         = '/music/googlemusic'
PAGE_SIZE      = 50
TWO_HOURS      = datetime.timedelta(seconds=7200)

################################################################################
def Prettify(str):
    return str.lower().replace('_', ' ').title()

def LoadAsync():
    API.load_data()

def LibraryRefresh():
    HTTP.ClearCache()
    Dict['refresh'] = datetime.datetime.now()
    API.reset_library()
    Thread.Create(LoadAsync)

################################################################################
def Start():
    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = L('Title')
    DirectoryObject.thumb = R(ICON)
    Dict['refresh'] = datetime.datetime.now()

################################################################################
def ValidatePrefs():
    return True

################################################################################
@handler(PREFIX, L('Title'), art=ART, thumb=ICON)
def MainMenu():
    if datetime.datetime.now() > Dict['refresh'] + TWO_HOURS:
        LibraryRefresh()

    oc = ObjectContainer(title2=L('Title'))

    if API.authenticated == False and Prefs['email'] and Prefs['password']:
        API.authenticate(Prefs['email'], Prefs['password'])
        Thread.Create(LoadAsync)

    if API.authenticated:
        oc.add(DirectoryObject(key=Callback(LibraryMenu), title=L('My Library')))
        oc.add(DirectoryObject(key=Callback(PlaylistsMenu), title=L('Playlists')))
        oc.add(DirectoryObject(key=Callback(StationsMenu), title=L('Stations')))

        if API.all_access:
            oc.add(DirectoryObject(key=Callback(GenresMenu), title=L('Genres')))
            oc.add(InputDirectoryObject(key=Callback(SearchMenu), title=L('Search'), prompt=L('Search Prompt'), thumb=R(SEARCH_ICON)))

    oc.add(DirectoryObject(key=Callback(RefreshMenu), title=L('Refresh')))
    oc.add(PrefsObject(title=L('Prefs Title'), thumb=R(PREFS_ICON)))
    return oc

################################################################################
@route(PREFIX + '/{name}/recentlyAdded')
def RecentlyAdded(name, stack):
    return ObjectContainer(title2=L('Title'))

################################################################################
@route(PREFIX + '/librarymenu')
def LibraryMenu():
    oc = ObjectContainer(title2=L('My Library'))
    oc.add(DirectoryObject(key=Callback(LibrarySubMenu, title='Artists'), title=L('Artists')))
    oc.add(DirectoryObject(key=Callback(LibrarySubMenu, title='Albums'), title=L('Albums')))
    oc.add(DirectoryObject(key=Callback(ShowSongs, title='Songs'), title=L('Songs')))
    oc.add(DirectoryObject(key=Callback(LibrarySubMenu, title='Genres'), title=L('Genres')))
    oc.add(DirectoryObject(key=Callback(LibrarySubMenu, title='Songs By Letter'), title=L('Songs By Letter')))
    oc.add(DirectoryObject(key=Callback(ShowSongs, title='Shuffle All', shuffle=True), title=L('Shuffle All')))

    return oc

################################################################################
@route(PREFIX + '/playlistsmenu')
def PlaylistsMenu(id=None):
    oc = ObjectContainer(title2=L('Playlists'))

    playlists = API.get_all_playlists()
    for playlist in playlists:
        # This block is for normal selection of playlists
        if id == None:
            if 'type' in playlist and playlist['type'].lower() == 'user_generated':
                oc.add(DirectoryObject(key=Callback(GetPlaylistContents, name=playlist['name'], id=playlist['id']), title=playlist['name']))
            else:
                oc.add(DirectoryObject(key=Callback(GetSharedPlaylist, name=playlist['name'], token=playlist['shareToken']), title=playlist['name']))
        # This block is for when a song is being added to a playlist
        else:
            oc.add(DirectoryObject(key=Callback(AddToCollection, id=id, playlist=playlist['id'], type=1), title=playlist['name']))

    oc.objects.sort(key=lambda obj: obj.title)
    return oc

################################################################################
@route(PREFIX + '/stationsmenu')
def StationsMenu():
    oc = ObjectContainer(title2=L('Stations'))
    oc.add(DirectoryObject(key=Callback(GetStationTracks, name=L('Lucky Radio'), id='IFL'), title=L('Lucky Radio')))

    stations = API.get_all_stations()
    for station in sorted(stations, key = lambda x: int(x.get('recentTimestamp')), reverse=True):
        do = DirectoryObject(key=Callback(GetStationTracks, name=station['name'], id=station['id']), title=station['name'])
        if 'imageUrl' in station:
            do.thumb = station['imageUrl']
        oc.add(do)

    return oc

################################################################################
@route(PREFIX + '/genresmenu')
def GenresMenu():
    oc = ObjectContainer(title2=L('Genres'))

    genres = API.get_genres()
    for genre in genres:
        if 'children' in genre:
            children = genre['children']
        else:
            children = None
        do = DirectoryObject(key=Callback(GenresSubMenu, name=genre['name'], id=genre['id'], children=children), title=genre['name'])
        if 'images' in genre:
            do.thumb = genre['images'][0]['url']
        oc.add(do)

    return oc

################################################################################
@route(PREFIX + '/searchmenu')
def SearchMenu(query):
    oc = ObjectContainer(title2=L('Search'))

    results = API.search_all_access(query, 100)
    for key, values in results.iteritems():
        if key == 'song_hits':
            for song in values:
                do = DirectoryObject(
                    key=Callback(AddItemMenu, song=song['track']),
                    title=song['track']['title'],
                    summary=L('Song')
                )

                if 'albumArtRef' in song['track']:
                    do.thumb = song['track']['albumArtRef'][0]['url']

                oc.add(do)

        if key == 'artist_hits':
            for artist in values:
                artist = artist['artist']
                artistObj = DirectoryObject(
                    key=Callback(GetArtistInfo, name=artist['name'], id=artist['artistId']),
                    title=artist['name'],
                    summary=L('Artist')
                )
                if 'artistArtRef' in artist:
                    artistObj.thumb = artist['artistArtRef']

                oc.add(artistObj)

        if key == 'album_hits':
            for album in values:
                album = album['album']
                albumObj = DirectoryObject(
                    key=Callback(GetAlbumInfo, name=album['name'], id=album['albumId']),
                    title=album['name'],
                    summary=L('Album')
                )

                if 'albumArtRef' in album:
                    albumObj.thumb = album['albumArtRef']

                oc.add(albumObj)

        if key == 'playlist_hits':
            for playlist in values:
               playlist = playlist['playlist']
               playlistObj = DirectoryObject(
                   key=Callback(GetSharedPlaylist, name=playlist['name'], token=playlist['shareToken']),
                   title=playlist['name'],
                   summary=L('Playlist')
               )

               if 'albumArtRef' in playlist:
                   playlistObj.thumb = playlist['albumArtRef'][0]['url']

               oc.add(playlistObj)

    return oc

################################################################################
@route(PREFIX + '/refreshmenu')
def RefreshMenu():
    LibraryRefresh()
    return ObjectContainer(header=L('Refresh'), message=L('RefreshInProgress'))

################################################################################
@route(PREFIX + '/additemmenu', song=dict)
def AddItemMenu(song):
    oc = ObjectContainer(title2='%s %s' % (L('Options for'), song['title']))
    oc.add(GetTrack(song, song['nid']))
    oc.add(DirectoryObject(key=Callback(AddToCollection, id=song['nid']), title='%s %s' % (L('Add to'), L('My Library'))))
    oc.add(DirectoryObject(key=Callback(PlaylistsMenu, id=song['nid']), title='%s %s' % (L('Add to'), L('Playlist'))))

    return oc

################################################################################
@route(PREFIX + '/addtocollection', type=int)
def AddToCollection(id, playlist=None, type=0):
    if type == 0:
        item = API.add_aa_track(id)
    else:
        item = API.add_songs_to_playlist(playlist, id)

    if item == None:
        message = L('Adding Fail')
    else:
        message = L('Adding Success')

    LibraryRefresh()
    return ObjectContainer(header=L('Adding Song'), message=message)

################################################################################
@route(PREFIX + '/librarysubmenu', page=int)
def LibrarySubMenu(title, page=1):
    oc = ObjectContainer(title2=L(title))
    items = {}

    if API.library_loaded:
        if title == 'Artists':
            items = API.artists
        elif title == 'Albums':
            items = API.albums
        elif title == 'Genres':
            items = API.genres
        elif title == 'Songs By Letter':
            items = API.letters

        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE

        for key in sorted(items)[start:end]:
            do = DirectoryObject(key=Callback(GetTrackList, name=key, type=title), title=key)
            if items[key]:
                do.thumb = items[key]
            oc.add(do)

        if end < len(items):
            oc.add(NextPageObject(key=Callback(LibrarySubMenu, title=title, page=page+1)))

    else:
        return ObjectContainer(header=L('Please Wait'), message=L('Loading'))

    return oc

################################################################################
@route(PREFIX + '/showsongs', shuffle=bool, page=int)
def ShowSongs(title, shuffle=False, page=1):
    oc = ObjectContainer(title2=L(title))

    if API.library_loaded:
        songs = API.all_songs
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE

        if shuffle == True:
            random.shuffle(songs)
            for song in songs[start:end]:
                oc.add(GetTrack(song, song['id']))
        else:
            for song in sorted(songs, key = lambda x: x.get('title'))[start:end]:
                oc.add(GetTrack(song, song['id']))

        if end < len(songs):
            oc.add(NextPageObject(key=Callback(ShowSongs, title=title, shuffle=shuffle, page=page+1)))

    else:
        return ObjectContainer(header=L('Please Wait'), message=L('Loading'))

    return oc

################################################################################
@route(PREFIX + '/getalbumsinlibrary')
def GetAlbumsInLibrary(name):
    oc = ObjectContainer(title2=name)

    albums = API.get_albums_in_library(name)
    for album in sorted(albums['albums'], key = lambda x: x.get('year')):
        albumObj = DirectoryObject(
            key=Callback(GetAlbumInfo, name=album['name'], id=album['albumId']),
            title=album['name']
        )

        if 'albumArtRef' in album:
            albumObj.thumb = album['albumArtRef']

        oc.add(albumObj)

    return oc

################################################################################
@route(PREFIX + '/gettracklist')
def GetTrackList(name, type):
    oc = ObjectContainer(title2=name)
    tracks = API.get_tracks_for_type(type, name)
    sort = 'title' if type == 'Songs By Letter' else 'trackType'
    for track in sorted(tracks, key = lambda x: x['track'].get(sort)):
        oc.add(GetTrack(track['track'], track['id']))

    return oc

################################################################################
@route(PREFIX + '/getplaylistcontents')
def GetPlaylistContents(name, id):
    oc = ObjectContainer(title2=name)

    tracks = API.get_all_user_playlist_contents(id)
    for track in tracks:
        if 'track' in track:
            data = track['track']
        else:
            data = API.get_song(track['trackId'])

        oc.add(GetTrack(data, track['id']))

    return oc

################################################################################
@route(PREFIX + '/getsharedplaylist')
def GetSharedPlaylist(name, token):
    oc = ObjectContainer(title2=name)

    tracks = API.get_shared_playlist_contents(token)
    for track in tracks:
        oc.add(GetTrack(track['track'], track['trackId']))

    return oc

################################################################################
@route(PREFIX + '/getstationtracks')
def GetStationTracks(name, id):
    oc = ObjectContainer(title2=name)

    tracks = API.get_station_tracks(id)
    for track in tracks:
        if API.all_access:
            if 'nid' in track:
                id = track['nid']
            else:
                id = track['id']
        else:
            id = track['id']
        oc.add(GetTrack(track, id))

    return oc

################################################################################
@route(PREFIX + '/genressubmenu', children=list)
def GenresSubMenu(name, id, children=None):
    oc = ObjectContainer(title2=name)
    oc.add(DirectoryObject(key=Callback(CreateStation, id=id), title='Play ' + name))

    if children != None:
        for child in children:
            oc.add(DirectoryObject(key=Callback(CreateStation, id=child), title='Play ' + Prettify(child)))
    return oc

################################################################################
@route(PREFIX + '/createstation')
def CreateStation(id):
    name = Prettify(id)
    station = API.create_station(name, id)
    return GetStationTracks(name=name, id=station)

################################################################################
@route(PREFIX + '/getartistinfo')
def GetArtistInfo(name, id, inLibrary=False):
    oc = ObjectContainer(title2=name)

    artist = API.get_artist_info(id)
    for album in sorted(artist['albums'], key = lambda x: x.get('year')):
        albumObj = DirectoryObject(
            key=Callback(GetAlbumInfo, name=album['name'], id=album['albumId']),
            title=album['name']
        )

        if 'albumArtRef' in album:
            albumObj.thumb = album['albumArtRef']

        oc.add(albumObj)

    return oc

################################################################################
@route(PREFIX + '/getalbuminfo')
def GetAlbumInfo(name, id):
    oc = ObjectContainer(title2=name)

    album = API.get_album_info(id)
    for track in album['tracks']:
        oc.add(GetTrack(track, track['nid']))

    return oc

################################################################################
@route(PREFIX + '/gettrack', song=dict)
def GetTrack(song, key, include_container=False):
    storeId = song['storeId'] if 'storeId' in song and API.all_access else 0
    id = song['id'] if 'id' in song else 0

    track = TrackObject(
        key = Callback(GetTrack, song=song, key=key, include_container=True),
        rating_key = key,
        title = song['title'],
        album = song['album'],
        artist = song['artist'],
        duration = int(song['durationMillis']),
        index = int(song.get('trackNumber', 0)),
        items = [
            MediaObject(
                parts = [PartObject(key=Callback(PlayAudio, id=id, storeId=storeId, ext='mp3'))],
                container = Container.MP3,
                audio_codec = AudioCodec.MP3
            )
        ]
    )

    if 'albumArtRef' in song:
        track.thumb = song['albumArtRef'][0]['url']

    if include_container:
        return ObjectContainer(objects=[track])
    else:
        return track

################################################################################
@route(PREFIX + '/playaudio.mp3')
def PlayAudio(id, storeId):
    if storeId != 0:
        try:
            song_url = API.get_stream_url(storeId)
        except CallFailure:
            song_url = API.get_stream_url(id)
    else:
        song_url = API.get_stream_url(id)

    return Redirect(song_url)
