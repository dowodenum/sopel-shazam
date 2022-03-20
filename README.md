A rather basic Sopel plugin that attempts to identify whatever song is
playing on a (configurable) stream.
Ported from [cottongin/StreamStuff](https://github.com/cottongin/StreamStuff).

### Setup

```bash
cd "~/.sopel/plugins/"
wget https://raw.githubusercontent.com/dowodenum/sopel-shazam/main/nowplaying.py
wget https://raw.githubusercontent.com/dowodenum/sopel-shazam/main/streamscrobbler.py
sudo apt install ffmpeg
pip install shazamio
pip install requests
```

### Configuration

Add the following block in your sopel config file (~/.sopel/default.cfg by default):
```
[nowplaying]
channel_stream_urls =
	"#yourtestchannel;http://example.stream.com/radio/8000/.mp3"
	"#general;http://example2.stream.com/radio/live"
announceListening = 
	"#yourtestchannel;Channel"
	"#general;Silent"
mismatches =
	"#yourtestchannel;Channel"
	"#general;Silent"
```
- `channel_stream_urls`:
  - a semicolon-separated pair of the channel and its associated stream URL

- `announceListening`:
  - Where/if the bot should announce that it's listening to the stream ('One second, listening...')
  - a semicolon-separated pair of the channel and its setting
    - choose from `Channel`, `Notice`, `Private`, or `Silent`
- `mismatches`:
  - Where/if the bot should announce that it found no results ('Sorry, Shazam could not identify what is playing. | <title>')
  - a semicolon-separated pair of the channel and its setting
    - choose from `Channel`, `Notice`, `Private`, or `Silent`

### Usage

From the IRC channel you configured in the last step (adjust from `.` to your bot's configured prefix):
```
<you> /msg bot .load nowplaying
<you> .np
<bot> One second, listening...
<bot> 🎵 Now Playing: A Song by Some Artist | via Shazam
```
