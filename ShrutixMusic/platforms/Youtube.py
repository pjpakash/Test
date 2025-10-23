# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Modified to use pytubefix instead of yt-dlp

import asyncio
import os
import re
from typing import Union

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress

from ShrutixMusic.utils.database import is_on_off
from ShrutixMusic.utils.formatters import time_to_seconds


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
            loop = asyncio.get_running_loop()
            
            def get_video_url():
                yt = YouTube(link, on_progress_callback=on_progress)
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                if stream:
                    return stream.url
                return None
            
            video_url = await loop.run_in_executor(None, get_video_url)
            if video_url:
                return 1, video_url
            else:
                return 0, "No suitable stream found"
        except Exception as e:
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        try:
            loop = asyncio.get_running_loop()
            
            def get_playlist_videos():
                pl = Playlist(link)
                video_ids = []
                for i, video in enumerate(pl.videos):
                    if i >= limit:
                        break
                    video_ids.append(video.video_id)
                return video_ids
            
            result = await loop.run_in_executor(None, get_playlist_videos)
            return result
        except Exception as e:
            print(f"Playlist error: {e}")
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
            loop = asyncio.get_running_loop()
            
            def get_formats():
                yt = YouTube(link)
                formats_available = []
                
                for stream in yt.streams.filter(progressive=True):
                    formats_available.append({
                        "format": f"{stream.resolution} - {stream.mime_type}",
                        "filesize": stream.filesize or 0,
                        "format_id": stream.itag,
                        "ext": stream.subtype,
                        "format_note": stream.resolution or "audio only",
                        "yturl": link,
                    })
                
                return formats_available
            
            formats_available = await loop.run_in_executor(None, get_formats)
            return formats_available, link
        except Exception as e:
            print(f"Formats error: {e}")
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
                yt = YouTube(link, on_progress_callback=on_progress)
                audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                
                if not audio_stream:
                    return None
                
                filename = f"downloads/{yt.video_id}.{audio_stream.subtype}"
                
                if os.path.exists(filename):
                    return filename
                
                audio_stream.download(output_path="downloads", filename=f"{yt.video_id}.{audio_stream.subtype}")
                return filename
            except Exception as e:
                print(f"Audio download error: {e}")
                return None

        def video_dl():
            try:
                yt = YouTube(link, on_progress_callback=on_progress)
                video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                
                if not video_stream:
                    video_stream = yt.streams.filter(file_extension='mp4').first()
                
                if not video_stream:
                    return None
                
                filename = f"downloads/{yt.video_id}.mp4"
                
                if os.path.exists(filename):
                    return filename
                
                video_stream.download(output_path="downloads", filename=f"{yt.video_id}.mp4")
                return filename
            except Exception as e:
                print(f"Video download error: {e}")
                return None

        def song_video_dl():
            try:
                yt = YouTube(link, on_progress_callback=on_progress)
                stream = yt.streams.get_by_itag(format_id)
                
                if not stream:
                    stream = yt.streams.filter(progressive=True).first()
                
                if stream:
                    fpath = f"downloads/{title}.mp4"
                    stream.download(output_path="downloads", filename=f"{title}.mp4")
                    return fpath
            except Exception as e:
                print(f"Song video download error: {e}")
                return None

        def song_audio_dl():
            try:
                yt = YouTube(link, on_progress_callback=on_progress)
                
                if format_id:
                    stream = yt.streams.get_by_itag(format_id)
                else:
                    stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                
                if stream:
                    fpath = f"downloads/{title}"
                    stream.download(output_path="downloads", filename=title)
                    
                    # Convert to mp3 if needed
                    downloaded_file = f"downloads/{title}.{stream.subtype}"
                    mp3_file = f"downloads/{title}.mp3"
                    
                    if os.path.exists(downloaded_file) and downloaded_file != mp3_file:
                        # You'll need ffmpeg for conversion
                        import subprocess
                        subprocess.run(['ffmpeg', '-i', downloaded_file, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', mp3_file])
                        os.remove(downloaded_file)
                    
                    return mp3_file
            except Exception as e:
                print(f"Song audio download error: {e}")
                return None

        if songvideo:
            fpath = await loop.run_in_executor(None, song_video_dl)
            return fpath
        elif songaudio:
            fpath = await loop.run_in_executor(None, song_audio_dl)
            return fpath
        elif video:
            if await is_on_off(1):
                direct = True
                downloaded_file = await loop.run_in_executor(None, video_dl)
            else:
                # Try to get direct URL first
                try:
                    yt = YouTube(link)
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    
                    if stream and stream.filesize and stream.filesize / (1024 * 1024) <= 250:
                        downloaded_file = stream.url
                        direct = False
                    else:
                        direct = True
                        downloaded_file = await loop.run_in_executor(None, video_dl)
                except:
                    direct = True
                    downloaded_file = await loop.run_in_executor(None, video_dl)
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        
        return downloaded_file, direct


# ©️ Copyright Reserved - @NoxxOP  Nand Yaduwanshi
# Modified to use pytubefix for better reliability
