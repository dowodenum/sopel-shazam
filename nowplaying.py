###
# Copyright (c) 2021, cottongin
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import asyncio
import io
import tempfile
import sys, traceback

import time

import requests
from shazamio import Shazam

# https://github.com/Horrendus/streamscrobbler-python
from streamscrobbler import *

threaded = True
from sopel import config, trigger
from sopel.module import commands, example
from sopel.config.types import StaticSection, ChoiceAttribute, ListAttribute

class NowplayingSection(StaticSection):
    channel_stream_urls = ListAttribute('channel_stream_urls', default=None)
    announceListening = ListAttribute('announceListening', default='Channel')
    mismatches = ListAttribute('mismatches', default='Channel')

def configure(config):
    config.define_section('nowplaying', NowplayingSection, validate=False)
    config.nowplaying.configure_setting('channel_stream_urls', 'List of <channel;stream URL> pairs, semicolon separated.')
    config.nowplaying.configure_setting('announceListening', '[Channel/Private/Notice/Silent] Where/how/if the bot should announce it is listening to the stream.')
    config.nowplaying.configure_setting('mismatches', '[Channel/Private/Notice/Silent] Where/how/if the bot should announce that it cannot identify what is playing.')

def setup(bot):
    bot.config.define_section('nowplaying', NowplayingSection)

def _channelConfig(config, channel):
    # checking the calling-user's channel against the list of channel;setting pairs
    for item in config:
        pair = item.split(';')
        # found a match, return variable
        if channel in pair[0]:
            return pair[1]
        else:
            bot.reply('This channel (' + channel + ') has no stream URL configured - please contact your resident bot herder!')
            bot.error(trigger)
            return

def _fetch_mp3(url: str):
    # this is (still) really dumb
    # TODO: handle unexpected content better in the request

    data = None

    with requests.Session() as conn:
        response = conn.get(url, stream=True, timeout=5)

        data = bytes()
        loops = 0

        for chunk in response.iter_content(1024*5):
            loops += 1
            if loops >= 25 or not chunk:
                break
            data += chunk

    return data

async def _parse_shazam(stream_info=None, audio_segment=None):
    # this is also really dumb

    out = {}
    shazam = Shazam()
    if not audio_segment:
        # TODO: fix this so it honors fs permissions etc
        try:
            out = await shazam.recognize_song('stream.mp3')
        except Exception as err:
            print(f"[FILE method] {err}")
            traceback.print_exc(file=sys.stdout)
            pass
    else:
        try:
            # so we make a NamedTemporaryFile because on *NIX we don't
            # always get a path or link to a regular TemporaryFile
            with tempfile.NamedTemporaryFile() as fake_file:
                # TODO: abstract this out into a AudioSegmentClass
                fake_file.write(audio_segment)
                out = await shazam.recognize_song(fake_file.name)
        except Exception as err:
            print(f"[FAKE method] {err}")
            traceback.print_exc(file=sys.stdout)
            pass


    append = ""
    if stream_info:
        metadata = stream_info.get('metadata')
        if metadata:
            append = " | {}".format(metadata.get('song', '???'))

    message = (
        f"Sorry, Shazam could not identify what is playing.{append}"
    )
    match = out.get('track')
    if match:
        message = "🎵 Now Playing: {title} by {subtitle} | {url}{append}"
        message = message.format(
            title=match.get('title', 'Unknown'),
            subtitle=match.get('subtitle', 'Unknown'),
            url=match.get('share', {}).get('href', 'via Shazam'),
            append=append,
        )

    return match, message

@commands('np', 'nowplaying')
@example('!np - asks Shazam to listen to the stream and return any identified tracks')
def nowplaying(bot, trigger):
    url = _channelConfig(bot.config.nowplaying.channel_stream_urls, trigger.sender)
    announceDest = _channelConfig(bot.config.nowplaying.announceListening, trigger.sender)
    mismatchDest = _channelConfig(bot.config.nowplaying.mismatches, trigger.sender)

    announceText = "One second, listening..."
    if 'Private' in announceDest:
        bot.say(announceText, trigger.nick)
    elif 'Notice' in announceDest:
        bot.notice(announceText, trigger.nick)
    elif 'Channel' in announceDest:
        bot.reply(announceText, trigger.sender)
    elif 'Silent' in announceDest:
        pass
    else:
        bot.reply('Invalid configuration. Choose from: Channel/Notice/Private/Silent')
        bot.error(trigger)
        return

    audio = _fetch_mp3(url)

    stream_info = get_server_info(url)

    match, reply = asyncio.run(
        _parse_shazam(
            stream_info=stream_info,
            audio_segment=audio,
        )
    )
    if not match:
        if 'Private' in mismatchDest:
            bot.say(reply, trigger.nick)
            return
        elif 'Notice' in mismatchDest:
            bot.notice(reply, trigger.nick)
            return
        elif 'Channel' in mismatchDest:
            bot.reply(reply, trigger.sender)
            return
        elif 'Silent' in mismatchDest:
            return
        else:
            bot.reply('Invalid configuration. Choose from: Channel/Notice/Private/Silent')
            bot.error(trigger)
            return
