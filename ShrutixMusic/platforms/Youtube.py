import asyncio
import os
import re
import json
from typing import Union
import glob
import random
import logging
from http.cookiejar import MozillaCookieJar

from pytube import YouTube, Playlist
from pytube.extract import video_id
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from ShrutixMusic.utils.database import is_on_off
from ShrutixMusic.utils.formatters import time_to_seconds

def cookie_txt_file():
    folder_path = f"{os.getcwd()}/cookies"
    filename = f"{os.getcwd()}/cookies/logs.csv"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the specified folder.")
    cookie_txt_file = random.choice(txt_files)
    with open(filename, 'a') as file:
        file.write(f'Choosen File : {cookie_txt_file}\n')
    return f"cookies/{str(cookie_txt_file).split('/')[-1]}"

def get_yt_with_cookies(link):
    """Get YouTube object with cookies"""
    cookie_file = cookie_txt_file()
    
    # Create a cookie jar and load cookies
    cookie_jar = MozillaCookieJar(cookie_file)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    
    # Create YouTube object with cookies
    yt = YouTube(
        link,
        use_oauth=False,
        allow_oauth_cache=True
    )
    
    # Set cookies in the request handler
    for cookie in cookie_jar:
        yt._author.headers['Cookie'] = f"{cookie.name}={cookie.value}; {yt._author.headers.get('Cookie', '')}"
    
    return yt

async def check_file_size(link):
    try:
        yt = get_yt_with_cookies(link)
        # Get the highest resolution stream to check approximate size
        stream = yt.streams.get_highest_resolution()
        if stream:
            return stream.filesize_approx
    except Exception as e:
        print(f"Error checking file size: {e}")
        return None
    return None

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            yt = get_yt_with_cookies(link)
            # Get the best progressive stream (video + audio)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            if stream:
                return 1, stream.url
            else:
                # If no progressive stream, get best video stream
                video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
                return 1, video_stream.url if video_stream else None
        except Exception as e:
            print(f"Error in video method: {e}")
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            # PyTube Playlist doesn't directly support cookies, so we'll use a workaround
            pl = Playlist(link)
            video_urls = []
            count = 0
            
            for video_url in pl.video_urls:
                if count >= limit:
                    break
                try:
                    # Extract video ID from URL
                    vid_id = video_url.split('v=')[1].split('&')[0]
                    video_urls.append(vid_id)
                    count += 1
                except Exception as e:
                    print(f"Error processing video URL: {e}")
                    continue
                    
            return video_urls
        except Exception as e:
            print(f"Error getting playlist: {e}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            yt = get_yt_with_cookies(link)
            formats_available = []
            
            # Progressive streams (video + audio)
            for stream in yt.streams.filter(progressive=True):
                formats_available.append({
                    "format": f"{stream.resolution} (progressive)",
                    "filesize": stream.filesize_approx,
                    "format_id": stream.itag,
                    "ext": stream.mime_type.split('/')[-1],
                    "format_note": "video+audio",
                    "yturl": link,
                })
            
            # Adaptive video streams
            for stream in yt.streams.filter(adaptive=True, only_video=True):
                formats_available.append({
                    "format": f"{stream.resolution} (video only)",
                    "filesize": stream.filesize_approx,
                    "format_id": stream.itag,
                    "ext": stream.mime_type.split('/')[-1],
                    "format_note": "video only",
                    "yturl": link,
                })
            
            # Audio streams
            for stream in yt.streams.filter(only_audio=True):
                formats_available.append({
                    "format": f"audio ({stream.abr})",
                    "filesize": stream.filesize_approx,
                    "format_id": stream.itag,
                    "ext": stream.mime_type.split('/')[-1],
                    "format_note": "audio only",
                    "yturl": link,
                })
                
            return formats_available, link
        except Exception as e:
            print(f"Error getting formats: {e}")
            return [], link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        
        loop = asyncio.get_running_loop()

        def audio_dl():
            try:
                yt = get_yt_with_cookies(link)
                # Get the best audio stream
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                if audio_stream:
                    # Download audio
                    output_file = audio_stream.download(
                        output_path="downloads", 
                        filename=f"{yt.video_id}"
                    )
                    # Rename to mp3 if needed
                    if not output_file.endswith('.mp3'):
                        base, ext = os.path.splitext(output_file)
                        new_file = base + '.mp3'
                        os.rename(output_file, new_file)
                        return new_file
                    return output_file
            except Exception as e:
                print(f"Error in audio download: {e}")
                return None

        def video_dl():
            try:
                yt = get_yt_with_cookies(link)
                # Get the best progressive stream (video + audio)
                stream = yt.streams.filter(
                    progressive=True, 
                    file_extension='mp4'
                ).order_by('resolution').desc().first()
                
                if stream:
                    output_file = stream.download(
                        output_path="downloads", 
                        filename=f"{yt.video_id}"
                    )
                    return output_file
                else:
                    # Fallback to adaptive streams
                    stream = yt.streams.filter(
                        adaptive=True, 
                        file_extension='mp4'
                    ).order_by('resolution').desc().first()
                    if stream:
                        output_file = stream.download(
                            output_path="downloads", 
                            filename=f"{yt.video_id}"
                        )
                        return output_file
            except Exception as e:
                print(f"Error in video download: {e}")
                return None

        def song_video_dl():
            try:
                yt = get_yt_with_cookies(link)
                # Get stream by itag (format_id)
                stream = yt.streams.get_by_itag(int(format_id))
                if stream:
                    output_file = stream.download(
                        output_path="downloads", 
                        filename=title
                    )
                    return output_file
            except Exception as e:
                print(f"Error in song video download: {e}")
                return None

        def song_audio_dl():
            try:
                yt = get_yt_with_cookies(link)
                # Get audio stream by itag
                stream = yt.streams.get_by_itag(int(format_id))
                if stream:
                    output_file = stream.download(
                        output_path="downloads", 
                        filename=title
                    )
                    # Convert to mp3 if needed
                    if not output_file.endswith('.mp3'):
                        base, ext = os.path.splitext(output_file)
                        new_file = base + '.mp3'
                        os.rename(output_file, new_file)
                        return new_file
                    return output_file
            except Exception as e:
                print(f"Error in song audio download: {e}")
                return None

        if songvideo:
            downloaded_file = await loop.run_in_executor(None, song_video_dl)
            return downloaded_file, True
        elif songaudio:
            downloaded_file = await loop.run_in_executor(None, song_audio_dl)
            return downloaded_file, True
        elif video:
            if await is_on_off(1):
                direct = True
                downloaded_file = await loop.run_in_executor(None, video_dl)
            else:
                try:
                    yt = get_yt_with_cookies(link)
                    stream = yt.streams.filter(
                        progressive=True, 
                        file_extension='mp4'
                    ).order_by('resolution').desc().first()
                    
                    if stream:
                        downloaded_file = stream.url
                        direct = False
                    else:
                        file_size = await check_file_size(link)
                        if not file_size:
                            print("None file Size")
                            return None, None
                        total_size_mb = file_size / (1024 * 1024)
                        if total_size_mb > 250:
                            print(f"File size {total_size_mb:.2f} MB exceeds the 250MB limit.")
                            return None, None
                        direct = True
                        downloaded_file = await loop.run_in_executor(None, video_dl)
                except Exception as e:
                    print(f"Error: {e}")
                    return None, None
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        
        return downloaded_file, direct
