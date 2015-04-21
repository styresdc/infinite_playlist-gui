import echonest.remix.audio as audio
from aqplayer import Player

audio_file = audio.LocalAudioFile("lateralus30.wav")
bars = audio_file.analysis.bars

# creates a Player given an 'echonest.remix.audio.LocalAudioFile'
aq_player = Player(audio_file)

for bar in bars:
    # give play() any 'echonest.remix.audio.AudioQuantum' to be played (section, bar, beat, etc...)
    aq_player.play(bar)

# close the audiostream when done
aq_player.close_stream()
