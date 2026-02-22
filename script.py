class script(object):

    START_TXT = """<b>Hey, {}!</b>

<b>I am a professional Video Screenshot Generator Bot 🎬</b>
<b>Send me any video file and choose what you want:</b>
<b>• Screenshots</b>
<b>• Sample clip</b>
<b>• Trim video</b>
<b>• Media info</b>
<b>• Thumbnails</b>
"""

    HELP_TXT = """<b>

Send any video.

Then choose:

Screenshots → generate frames
Sample → short preview clip
Trim → cut part of video
Info → video technical details
Thumbs → extract thumbnails

Supports large MKV / MP4 files.
</b>"""

    ABOUT_TXT = """<b>

Bot Name : Video Screenshot Generator
Developer : <a href="https://t.me/Venuboyy">ZeroDev</a>
Library : Pyrogram
Language : Python 3
Database : MongoDB
Engine : FFmpeg
</b>"""

    FORCE_SUB_TXT = """<b>⚠️ Access Restricted!</b>

You must join our channels to use this bot.

🔔 Please join both channels below and try again.
"""

    SETTINGS_TXT = """<b>⚙️ Your Settings</b>

Configure how the bot behaves for you.
All settings are saved to your account.
"""

    MANUAL_SS_TXT = """<b>📸 Manual Screenshot</b>

Send timestamps one per line in format:
<code>HH:MM:SS</code>  or  <code>MM:SS</code>  or  <code>SS</code>

Example:
<code>00:01:30
00:05:00
00:10:45</code>

Send /cancel to abort.
"""

    TRIM_START_TXT = """<b>✂️ Trim Video – Step 1</b>

Send the <b>start time</b> in format:
<code>HH:MM:SS</code>  or  <code>MM:SS</code>

Example: <code>00:01:30</code>

Send /cancel to abort.
"""

    TRIM_END_TXT = """<b>✂️ Trim Video – Step 2</b>

Send the <b>end time</b> in format:
<code>HH:MM:SS</code>  or  <code>MM:SS</code>

Example: <code>00:05:00</code>

Send /cancel to abort.
"""

    PROCESSING_TXT   = "⚙️ <b>Processing your request, please wait...</b>"
    DOWNLOADING_TXT  = "⬇️ <b>Downloading video...</b>"
    UPLOADING_TXT    = "📤 <b>Uploading...</b>"
    CANCELLED_TXT    = "❌ <b>Operation cancelled.</b>"
    DONE_TXT         = "✅ <b>Done!</b>"
