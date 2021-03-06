import os
import bisect
from scipy.sparse import dok_matrix
import hashlib
import pickle
import sys
import threading
from aqplayer import Player
import urllib2
from spotipy import Spotify
import echonest.remix.audio as audio
import shutil

__author__ = 'parryrm'


AUDIO_EXTENSIONS = {'mp3', 'm4a', 'wav', 'ogg', 'au', 'mp4'}
PLAYLIST_DIR = 'playlist'
THRESHOLD = 80
SPOT_DIR = 'spotify'
SPOT_PLAY = PLAYLIST_DIR + os.sep + 'spotify.play.pkl'

def _is_audio(f_):
    _, ext = os.path.splitext(f_)
    # drop leading '.'
    ext = ext[1:]
    return ext in AUDIO_EXTENSIONS


def _is_playlist(f_):
    from re import search
    return search(r".*\.play\.pkl", f_) is not None


def _is_md5(x_):
    from re import match
    return match('[a-z0-9]{32}', x_) is not None


def get_md5(song_file_):
    return hashlib.md5(file(song_file_, 'rb').read()).hexdigest()


def get_all_songs(directory_):
    all_songs_ = []
    for f_ in os.listdir(directory_):
        path_ = os.path.join(directory_, f_)
        if os.path.isdir(path_):
            all_songs_.extend(get_all_songs(path_))
        elif _is_audio(path_):
            all_songs_.append(path_)

    return all_songs_


def get_segments(audio_file_):
    from numpy import hstack, array
    segments_ = audio_file_.analysis.segments
    n_ = len(segments_)
    pitches_ = array(segments_.pitches)
    timbre_ = array(segments_.timbre)
    duration_ = array(segments_.durations).reshape((n_, 1))
    loudness_max_ = array(segments_.loudness_max).reshape((n_, 1))
    loudness_start_ = array(segments_.loudness_begin).reshape((n_, 1))
    return hstack((10 * pitches_, timbre_, 100 * duration_, loudness_max_, loudness_start_))


def seg_distances(u_, v_=None):
    from scipy.spatial.distance import pdist, cdist, squareform
    from numpy import diag, ones
    if v_ is None:
        d_ = pdist(u_[:, 0:12], 'euclidean')
        d_ += pdist(u_[:, 12:24], 'euclidean')
        d_ += pdist(u_[:, 24:], 'cityblock')
        d_ = squareform(d_) + diag(float('NaN') * ones((u_.shape[0],)))
    else:
        d_ = cdist(u_[:, 0:12], v_[:, 0:12], 'euclidean')
        d_ += cdist(u_[:, 12:24], v_[:, 12:24], 'euclidean')
        d_ += cdist(u_[:, 24:], v_[:, 24:], 'cityblock')

    return d_


# faster version uses numpy matrix routines
def get_beat_distances(audio_i_, audio_j_):
    from numpy import minimum, array, ones, isnan, copy
    segments_i = get_segments(audio_i_)
    aq_beats_i = audio_i_.analysis.beats

    first_segment_index_i = array([audio_i_.analysis.segments.index(beat.segments[0]) for beat in aq_beats_i])\
        .reshape((len(aq_beats_i), 1))
    beat_length_i = array([len(beat.segments) for beat in aq_beats_i]).reshape((len(aq_beats_i), 1))

    segments_j = get_segments(audio_j_)
    aq_beats_j = audio_j_.analysis.beats

    first_segment_index_j = array([audio_j_.analysis.segments.index(beat.segments[0]) for beat in aq_beats_j])\
        .reshape((len(aq_beats_j), 1))
    beat_length_j = array([len(beat.segments) for beat in aq_beats_j]).reshape((len(aq_beats_j), 1))
    if audio_i_.filename == audio_j_.filename:
        segment_dist = seg_distances(segments_i)
    else:
        segment_dist = seg_distances(segments_i, segments_j)

    (m, n) = segment_dist.shape
    beat_dist_ = float('NaN') * ones((len(aq_beats_i), len(aq_beats_j)))
    # noinspection PyCallingNonCallable
    segment_dist2 = copy(segment_dist)
    for beat_length in range(1, 6):
        i_beat_index = [x for x in range(len(aq_beats_i)) if beat_length_i[x] == beat_length]
        j_beat_index = [x for x in range(len(aq_beats_j)) if beat_length_j[x] == beat_length]

        if len(i_beat_index) > 0 and len(j_beat_index) > 0:
            i_segment_index = first_segment_index_i[i_beat_index]
            j_segment_index = first_segment_index_j[j_beat_index]

            old_rows = beat_dist_[i_beat_index, :]
            new_rows = segment_dist2[i_segment_index, first_segment_index_j.T]
            is_nan = isnan(old_rows)
            old_rows[is_nan] = new_rows[is_nan]
            beat_dist_[i_beat_index, :] = old_rows

            old_cols = beat_dist_[:, j_beat_index]
            new_cols = segment_dist2[first_segment_index_i, j_segment_index.T]
            is_nan = isnan(old_cols)
            old_cols[is_nan] = new_cols[is_nan]
            beat_dist_[:, j_beat_index] = old_cols

        segment_dist2[:m-beat_length, :n-beat_length] += segment_dist[beat_length:, beat_length:]

    # divide by minimum number of segments per beat comparison
    num_segments = minimum(beat_length_i, beat_length_j.T)
    beat_dist_ /= num_segments

    # adjust for local_context of beat within bar
    beat_within_bar_i_ = array([beat.local_context()[0] for beat in aq_beats_i]).reshape((-1, 1))
    beat_within_bar_j_ = array([beat.local_context()[0] for beat in aq_beats_j]).reshape((1, -1))
    index = beat_within_bar_i_ * ones((1, beat_within_bar_j_.size)) != \
        ones((beat_within_bar_i_.size, 1)) * beat_within_bar_j_
    beat_dist_[index] = float('Inf')
    return beat_dist_


"""
# uses Luke Stack's beat distances
def get_beat_distances0(audio_i_, audio_j_):
    from numpy import ones
    beats_i = audio_i_.analysis.beats
    beats_j = audio_j_.analysis.beats
    beat_dist_ = float('NaN') * ones((len(beats_i), len(beats_j)))
    for i_ in range(len(beats_i)):
        beat_i_ = beats_i[i_]
        print 'Computing beat distances [%5.1f%%]\r' % (100.0 * i_ / len(beats_i)),
        for j in range(len(beats_j)):
            beat_j_ = beats_j[j]
            if beat_i_ != beat_j_:
                beat_dist_[i_, j] = get_beat_distance(beat_i_, beat_j_)

    return beat_dist_
"""


def robust_local_audio_file(audio_file_):
    from time import sleep
    from pyechonest.util import EchoNestAPIError
    try:
        laf_ = audio.LocalAudioFile(audio_file_)
        return laf_
    except EchoNestAPIError:
        print "Failed to retrieve analysis... wait to try again"
        sleep(10)
        return robust_local_audio_file(audio_file_)


def get_local_audio(all_songs_):
    from shutil import copyfile
    local_audio_ = {}
    for i_ in range(len(all_songs_)):
        print 'get song', (i_ + 1), '/', len(all_songs_)
        extension = os.path.splitext(all_songs_[i_])[1]
        track_md5_ = get_md5(all_songs_[i_])
        mp3_file = PLAYLIST_DIR + "/" + track_md5_ + extension
        if not os.path.isfile(mp3_file):
            print "copying original audio to", mp3_file
            if not os.path.exists(PLAYLIST_DIR):
                os.makedirs(PLAYLIST_DIR)
            copyfile(all_songs_[i_], mp3_file)

        print "loading local audio from", mp3_file
        laf_ = robust_local_audio_file(mp3_file)
        local_audio_[track_md5_] = laf_
    return local_audio_


def get_start_beats(local_audio_):
    start_ = 0
    start_beats_ = {}
    for md5_ in sorted(local_audio_.keys()):
        laf_ = local_audio_[md5_]
        start_beats_[md5_] = start_
        start_ += len(laf_.analysis.beats)
    start_beats_['total'] = start_
    return start_beats_


def update_edges(e_, m1_, i1_, m2_, i2_, d_):
    a = e_[m1_].get(i1_, [])
    bisect.insort(a, (d_, m2_, i2_))
    e_[m1_][i1_] = a


def get_edges(laf_i_, laf_j_):
    from numpy import isnan, where, vstack
    md5_i_ = laf_i_.analysis.pyechonest_track.md5
    md5_j_ = laf_j_.analysis.pyechonest_track.md5
    track_md5 = [md5_i_, md5_j_]
    track_md5.sort()
    edges_file_ = PLAYLIST_DIR + os.sep + track_md5[0] + "_" + track_md5[1] + ".edges.pkl"
    if os.path.isfile(edges_file_):
        print "loading", edges_file_
        with open(edges_file_, 'rb') as in_file_:
            edges_ = pickle.load(in_file_)
    else:
        num_edges = 0
        edges_ = {md5_i_: {}, md5_j_: {}}
        beat_distances = get_beat_distances(laf_i_, laf_j_)
        beat_distances[isnan(beat_distances)] = float('Inf')
        (ii, jj) = where(beat_distances < 80)
        for (i1, j1) in vstack((ii, jj)).T:
            d1 = beat_distances[i1, j1]
            update_edges(edges_, md5_i_, i1, md5_j_, j1, d1)
            if md5_i_ != md5_j_:
                update_edges(edges_, md5_j_, j1, md5_i_, i1, d1)
            num_edges += 1
        edges_['num_edges'] = num_edges
        print num_edges, "edges found"
        with open(edges_file_, 'wb') as output_:
            pickle.dump(edges_, output_)

    return edges_


def check_edges_ij(edges_ij_, md5_, max_key_):
    from numpy import array, all
    if md5_ in edges_ij_.keys():
        keys_ = array(edges_ij_[md5_].keys())
        okay_ = keys_ < max_key_
        if not all(okay_):
            print md5_, 'not okay.'
            print keys_[not okay_]
            raise


def update_all_edges(edges_, edges_ij_):
    for md5_ in edges_ij_.keys():
        if not _is_md5(md5_):
            continue
        a = edges_.get(md5_, {})
        for md5_beat_ in edges_ij_[md5_].keys():
            edge_list_ = edges_ij_[md5_][md5_beat_]
            b = a.get(md5_beat_, [])
            for edge in edge_list_:
                bisect.insort(b, edge)
            a[md5_beat_] = b
        edges_[md5_] = a


def get_all_edges(local_audio_):
    edges_ = {}
    for md5_i_ in local_audio_.keys():
        for md5_j_ in local_audio_.keys():
            print md5_i_, ",", md5_j_
            edges_ij_ = get_edges(local_audio_[md5_i_], local_audio_[md5_j_])
            check_edges_ij(edges_ij_, u'3da35fa9caab917eaf70f10d1b35753c', 821)
            check_edges_ij(edges_ij_, u'aa84896e81aa15ca98ff631ffc643532', 693)
            update_all_edges(edges_, edges_ij_)
    return edges_


class EdgesThread(threading.Thread):
    def __init__(self, all_songs):
        threading.Thread.__init__(self)
        self.all_songs = all_songs
        self.edges = {}

    def run(self):
        for song_i_ in self.all_songs:
            laf_i_ = audio.LocalAudioFile(song_i_)
            for song_j_ in self.all_songs:
                laf_j_ = audio.LocalAudioFile(song_j_)
                edges_ij_ = get_edges(laf_i_, laf_j_)
                update_all_edges(self.edges, edges_ij_)


def get_all_edges_background(all_songs_):
        thread_ = EdgesThread(all_songs_)
        thread_.start()


def get_adjacency_matrix(all_edges_, start_beats_, threshold_):
    from operator import itemgetter
    s_ = dok_matrix((start_beats_['total'], start_beats_['total']))
    md5_sorted_by_start = [x[0] for x in sorted(start_beats_.items(), key=itemgetter(1))]
    # get rid of the 'total' key
    del md5_sorted_by_start[-1]
    for i_ in md5_sorted_by_start:
        edges = all_edges_[i_]
        for i1, sorted_list in edges.iteritems():
            for (d1, j, j1) in sorted_list:
                if d1 < threshold_:
                    s_[start_beats_[i_] + i1, start_beats_[j] + j1] = d1
    return s_


class Playback(object):
    threshold = THRESHOLD
    min_branch_probability = 0.18
    max_branch_probability = 0.50
    step_branch_probability = 0.09
    curr_branch_probability = min_branch_probability
    ghost = 1

    def __init__(self, all_edges_, local_audio_, aq_players_, start_beats_, thread=None, curr_md5=None, curr_beat=None):
        from random import choice
        self.all_edges = all_edges_
        self.local_audio = local_audio_
        self.aq_players = aq_players_
        self.start_beats = start_beats_
        self.thread = thread
        if curr_md5 is not None:
            self.curr_md5 = curr_md5
        else:
            self.curr_md5 = choice(self.all_edges.keys())

        self.curr_player = self.aq_players[self.curr_md5]
        self.curr_laf = self.local_audio[self.curr_md5]

        if curr_beat is not None:
            self.curr_beat = curr_beat
        else:
            self.curr_beat = choice(range(len(self.curr_laf.analysis.beats)))
        self.last_branch = [self.curr_beat, self.curr_beat]

    def update(self, *args):
        from random import random, choice
        print "play", self.curr_md5, "beat", self.curr_beat
        cursor_ = args[0]
        branch_cursor_ = args[1]
        last_branch_cursor_ = args[2]
        self.curr_player.play(self.curr_laf.analysis.beats[self.curr_beat])
        self.curr_beat = (self.curr_beat + 1) % len(self.curr_laf.analysis.beats)
        # get candidates
        candidates = self.all_edges[self.curr_md5].get(self.curr_beat, [])
        candidates = [candidates[i] for i in range(len(candidates)) if candidates[i][0] < self.threshold]
        # restrict to local branches if we just changed songs and are resetting the data structures
        if self.thread is not None:
            if self.thread.ejecting():
                candidates = [candidates[i] for i in range(len(candidates)) if candidates[i][1] == self.curr_md5]
        branched = False
        if len(candidates) > 0:
            print len(candidates), "branch candidates, prob =", self.curr_branch_probability
            # print candidates
            # flip a coin
            if random() < self.curr_branch_probability:
                print "Branch!!!"
                branch = choice(candidates)
                changed_song = branch[1] != self.curr_md5
                self.last_branch[0] = [self.curr_beat + self.start_beats[self.curr_md5]]
                self.curr_md5 = branch[1]
                self.curr_beat = branch[2]
                self.curr_player = self.aq_players[self.curr_md5]
                self.curr_laf = self.local_audio[self.curr_md5]
                self.curr_branch_probability = self.min_branch_probability
                self.last_branch[1] = [self.curr_beat + self.start_beats[self.curr_md5]]
                branched = True

                if changed_song:
                    print "********** Changed song **********"
                    # signal that the data loading thread should reset
                    self.last_branch = [self.curr_beat, self.curr_beat]
                    if self.thread is not None:
                        self.thread.eject(self.curr_md5)

            else:
                self.curr_branch_probability = min(self.max_branch_probability,
                                                   self.curr_branch_probability + self.step_branch_probability)
        # update cursor
        t0 = self.curr_beat + self.start_beats[self.curr_md5]
        cursor_.set_xdata(t0)
        cursor_.set_ydata(t0)

        if len(candidates) > 0:
            from numpy import vstack, repeat, array
            t0 = repeat(t0, len(candidates), 0)
            t1 = array([self.start_beats[c[1]] for c in candidates]) + array([c[2] for c in candidates])
            branch_x = vstack((t0, t0, t1, t1, t0)).T.reshape((-1, 1))
            branch_y = vstack((t0, t1, t1, t0, t0)).T.reshape((-1, 1))
            branch_cursor_.set_xdata(branch_x)
            branch_cursor_.set_ydata(branch_y)
            self.ghost = 1
        elif self.ghost >= 4:
            branch_cursor_.set_xdata([])
            branch_cursor_.set_ydata([])
        else:
            self.ghost += 1

        if branched:
            if self.last_branch[0] < self.last_branch[1]:
                last_branch_cursor_.set_color('green')
            else:
                last_branch_cursor_.set_color('red')
            last_branch_x = [self.last_branch[i] for i in [0, 1, 1]]
            last_branch_y = [self.last_branch[i] for i in [0, 0, 1]]
            last_branch_cursor_.set_xdata(last_branch_x)
            last_branch_cursor_.set_ydata(last_branch_y)

        args[0].figure.canvas.draw()


def infinite_playlist(playlist_name, playlist_directory=None):
    all_edges_file = PLAYLIST_DIR + "/" + playlist_name + ".play.pkl"
    all_edges = None
    if os.path.isfile(all_edges_file):
        print "loading playlist edges"
        with open(all_edges_file, 'rb') as input_:
            all_edges = pickle.load(input_)
        all_songs = [PLAYLIST_DIR + os.sep + md5 + '.mp3' for md5 in all_edges.keys()]
    else:
        all_songs = get_all_songs(playlist_directory)

    print len(all_songs), "songs"

    aq_players = {}
    local_audio = {}
    local_audio = get_local_audio(all_songs)
    start_beats = get_start_beats(local_audio)
    print start_beats['total'], "total beats"

    if not os.path.isfile(all_edges_file):
        all_edges = get_all_edges(local_audio)
        with open(all_edges_file, 'wb') as output:
            pickle.dump(all_edges, output)

    """
    # for debugging
    import json
    with open('all_edges.json', 'w') as output:
        json.dump(all_edges, output)
    """

    total_edges = 0
    for song_i in all_edges.keys():
        song_i_edges = all_edges[song_i]
        for beat_i in song_i_edges.keys():
            song_i_beat_i_edges = song_i_edges[beat_i]
            for _, song_j, beat_j in song_i_beat_i_edges:
                total_edges += 1
    print total_edges, "total edges"

    s = get_adjacency_matrix(all_edges, start_beats, THRESHOLD)

    for md5, laf in local_audio.iteritems():
        aq_players[md5] = Player(laf)

    from matplotlib.pyplot import figure, plot, show
    fig = figure()
    ax = fig.add_subplot(111)
    ax.spy(s, markersize=1)
    # plot lines around song boundaries
    x = sorted(start_beats.values() * 2)[1:]
    y = sorted(start_beats.values() * 2)[:-1]
    boundaries = [0, 0]
    boundaries[0], = plot(x, y, marker='None', linestyle='-', color='gray')
    boundaries[1], = plot(y, x, marker='None', linestyle='-', color='gray')

    branch_cursor, = plot([], [], color='cyan', marker='s', markersize=5, linestyle='-')
    last_branch_cursor, = plot([], [], color='green', marker='s', markersize=5)
    cursor, = plot([], [], color='magenta', marker='s', markersize=5, linestyle='None')

    # start playing
    dt = 0.001
    # start_md5 = u'0bda1f637253fdeb3cd8e4fb7a3f3683'
    playback = Playback(all_edges, local_audio, aq_players, start_beats)
    timer = fig.canvas.new_timer(interval=dt*1000.0)
    timer.add_callback(playback.update, cursor, branch_cursor, last_branch_cursor)
    timer.start()
    show()
#    finally:
#        print "cleaning up"
#        for player in aq_players.values():
#            print "closing aq_player stream"
#            player.close_stream()
#        for laf in local_audio.values():
#            print "unloading local audio"
#            laf.unload()

class DataLoadingThread(threading.Thread):

    def __init__(self, sim, boundaries, edges, local_audio, aq_players, start_beats, curr_md5):
        print "creating new thread"
        threading.Thread.__init__(self)
        self.sim = sim
        self.boundaries = boundaries
        self.edges = edges
        self.local_audio = local_audio
        self.aq_players = aq_players
        self.start_beats = start_beats
        self.curr_md5 = curr_md5
        self._ejecting = threading.Event()
        self._stopping = threading.Event()

    def update(self):
        # clear out edges to other songs
        for beat, edges in self.edges[self.curr_md5].items():
            self.edges[self.curr_md5][beat] = [edge for edge in edges if edge[1] == self.curr_md5]

        # clear out edges from other songs
        for md5 in self.edges.keys():
            if md5 != self.curr_md5:
                del self.edges[md5]

        # clear out audio quantum players
        for md5, aqp in self.aq_players.items():
            if md5 != self.curr_md5:
                aqp.close_stream()
                del self.aq_players[md5]

        # clear out local audio files
        for md5, laf in self.local_audio.items():
            if md5 != self.curr_md5:
                laf.unload()
                del self.local_audio[md5]

        # clear out start_beats
        for md5 in self.start_beats.keys():
            if md5 != self.curr_md5:
                del self.start_beats[md5]
        self.start_beats[self.curr_md5] = 0
        self.start_beats['total'] = len(self.local_audio[self.curr_md5].analysis.beats)

    def run(self):
        from aqplayer import Player
        from scipy.sparse import find
        from re import match, search
        print "thread is running"
        while True:
            edge_files = [f for f in os.listdir(PLAYLIST_DIR)
                          if search(r"" + self.curr_md5 + ".*\.edges.pkl", f) is not None]
            edge_files = edge_files[:50]
            for edge_file in edge_files:
                print "load edge_file:", edge_file
                new_md5 = None
                m = match(r"" + self.curr_md5 + "_([a-z0-9]{32})", edge_file)
                if m is not None:
                    new_md5 = m.group(1)
                m = match(r"([a-z0-9]{32})_" + self.curr_md5, edge_file)
                if m is not None:
                    new_md5 = m.group(1)

                # skip if the new_md5 is the current one.
                if new_md5 == self.curr_md5:
                    continue

                audio_file = PLAYLIST_DIR + os.sep + new_md5 + '.mp3'
                self.local_audio[new_md5] = audio.LocalAudioFile(audio_file)

                new_edges = get_edges(self.local_audio[self.curr_md5], self.local_audio[new_md5])
                update_all_edges(self.edges, new_edges)

                new_edges = get_edges(self.local_audio[new_md5], self.local_audio[new_md5])
                update_all_edges(self.edges, new_edges)

                new_edges = get_edges(self.local_audio[new_md5], self.local_audio[self.curr_md5])
                update_all_edges(self.edges, new_edges)

                self.aq_players[new_md5] = Player(self.local_audio[new_md5])
                self.start_beats[new_md5] = self.start_beats['total']
                self.start_beats['total'] += len(self.local_audio[new_md5].analysis.beats)
                s = get_adjacency_matrix(self.edges, self.start_beats, THRESHOLD)
                fs = find(s)

                # update sim
                self.sim.set_data(fs[0], fs[1])
                self.sim.figure.gca().set_xlim([0, self.start_beats['total']])
                self.sim.figure.gca().set_ylim([self.start_beats['total'], 0])

                # update boundaries
                x = sorted(self.start_beats.values() * 2)[1:]
                y = sorted(self.start_beats.values() * 2)[:-1]
                self.boundaries[0].set_xdata(x)
                self.boundaries[0].set_ydata(y)
                self.boundaries[1].set_xdata(y)
                self.boundaries[1].set_ydata(x)

                print "************** REDRAW SELF-SIMILARITY ********************"
                self.sim.figure.canvas.draw()

                # song change, better stop this.
                if self.ejecting() or self.stopping():
                    break

            # wait for a song change
            self._ejecting.wait()

            if self.stopping():
                break

            # update the stuffs.
            self.update()
            self._ejecting.clear()

    def eject(self, curr_md5):
        self.curr_md5 = curr_md5
        self._ejecting.set()

    def ejecting(self):
        return self._ejecting.isSet()

    def stop(self):
        self._stopping.set()
        self._ejecting.set()

    def stopping(self):
        return self._stopping.isSet()


def infinite_out_of_core(curr_md5):
    from aqplayer import Player
    audio_file = PLAYLIST_DIR + os.sep + curr_md5 + '.mp3'
    curr_local_audio = {}
    curr_aq_players = {}
    thread = None
    try:
        curr_local_audio = get_local_audio([audio_file])
        curr_edges = get_all_edges(curr_local_audio)
        for md5, laf in curr_local_audio.iteritems():
            curr_aq_players[md5] = Player(laf)

        curr_start_beats = {curr_md5: 0, 'total': len(curr_local_audio[curr_md5].analysis.beats)}

        s = get_adjacency_matrix(curr_edges, curr_start_beats, THRESHOLD)

        from matplotlib.pyplot import figure, plot, show
        fig = figure()
        ax = fig.add_subplot(111)
        sim = ax.spy(s, markersize=1)

        x = sorted(curr_start_beats.values() * 2)[1:]
        y = sorted(curr_start_beats.values() * 2)[:-1]
        boundaries = [0, 0]
        boundaries[0], = plot(x, y, marker='None', linestyle='-', color='gray')
        boundaries[1], = plot(y, x, marker='None', linestyle='-', color='gray')
        branch_cursor, = plot([], [], color='cyan', marker='s', markersize=5, linestyle='-')
        last_branch_cursor, = plot([], [], color='green', marker='s', markersize=5)
        cursor, = plot([], [], color='magenta', marker='s', markersize=5, linestyle='None')

        # create a thread to start loading new data
        from re import search, match
        thread = DataLoadingThread(sim, boundaries, curr_edges, curr_local_audio,
                                   curr_aq_players, curr_start_beats, curr_md5)

        # start playing
        dt = 0.001
        # start_md5 = u'0bda1f637253fdeb3cd8e4fb7a3f3683'
        playback = Playback(curr_edges, curr_local_audio, curr_aq_players, curr_start_beats, thread=thread)
        timer = fig.canvas.new_timer(interval=dt*1000.0)
        timer.add_callback(playback.update, cursor, branch_cursor, last_branch_cursor)

        timer.start()
        thread.start()

        show()

    finally:
        print "cleaning up"
        if thread is not None:
            thread.stop()
            if thread.isAlive():
                thread.join()
        for player in curr_aq_players.values():
            print "closing aq_player stream"
            player.close_stream()
        for laf in curr_local_audio.values():
            print "unloading local audio"
            laf.unload()


def get_album(artist_uri, spot, playlist_dir):
    clear_spot_cache()
    results = spot.artist_albums(artist_uri)
    for i in range(len(results)):
        print i, results[u'items'][i][u'name']
    a_index = input('Enter album index: ')
    album = results[u'items'][a_index]
    tracks = spot.album_tracks(album[u'uri'])[u'items']
    get_spot_tracks(tracks)


def clear_spot_cache():
    if not os.path.exists(SPOT_DIR):
        os.makedirs(SPOT_DIR)
    else:
        shutil.rmtree(SPOT_DIR)
        os.makedirs(SPOT_DIR)

    if os.path.isfile(SPOT_PLAY):
        os.remove(SPOT_PLAY)


def get_spot_tracks(tracks):
    for t in tracks:
        try:
            url = t[u'preview_url']
            req2 = urllib2.Request(url)
            response = urllib2.urlopen(req2)
            data = response.read()
            mp3_file = SPOT_DIR + os.sep + t['name'] + '.mp3'
            with open(mp3_file, 'wb') as output_:
                output_.write(data)
            print 'track:' + t['name']
        except:
            pass


def get_top_ten(artist_uri, spot, playlist_dir):
    clear_spot_cache()
    results = spot.artist_top_tracks(artist_uri)
    tracks = results[u'tracks'][:10]
    get_spot_tracks(tracks)


def spot_search(output):
#    try:
    artist = raw_input("Please enter artist: ")
    spot = Spotify()
    results = spot.search(q='artist:' + artist, type='artist')
    print "Found:", results[u'artists'][u'items'][0][u'name']
    artist_uri = results[u'artists'][u'items'][0][u'uri']
    choice = raw_input("Top 10 [T] or album [A]: ")
    if choice == 't' or choice == 'T':
        get_top_ten(artist_uri, spot, output)
    else:
        get_album(artist_uri, spot, output)
    print "Found:", results[u'artists'][u'items'][0][u'name']

#    except:
#        print sys.exc_info()[0]
#        spot_search(output)


def run(ls):
    import getopt
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'o:', ["output="])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    input_ = ls
    output = "playlist"
    for o, a in optlist:
        if o in ("-p", "--output"):
            output = a
        else:
            assert False, "unhandled option"

    import re
    if re.match('spotify', input_, re.IGNORECASE):
        # takes the top search result
        output = SPOT_DIR
        spot_search(output)
        infinite_playlist(output, output)
    else:
        if os.path.isdir(input_):
            infinite_playlist(output, input_)
        elif os.path.isfile(input_):
            if _is_audio(input_):
                track_md5_ = get_md5(input_)
                infinite_out_of_core(track_md5_)
            else:
                infinite_playlist(input_)
        else:
            # md5
            infinite_out_of_core(input_)


def usage():
    print 'usage: python infinite_playlist.py <input> [OPTION]'
    print
    print '<input>'
    print '\tThe input directory, playlist file, song file, md5, or \'spotify\''
    print
    print 'Options:'
    print '-o, --output='
    print '\tThe output playlist file name (default: "playlist")'

# music_dir = 'N:\\MP3\\U2\\1991 - Achtung Baby'