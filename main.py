from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import edge_tts
import uuid
import os
import re
import subprocess

app = FastAPI(title="Auto Video Recap AI Studio")

# Gemini API Client
api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

def extract_video_id(url: str):
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return """
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Auto Recap AI Studio</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#0b0e14] text-white font-sans p-4 max-w-md mx-auto min-h-screen pb-16">
        <div class="flex justify-between items-center mb-5">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles text-purple-400 text-lg"></i>
                <h1 class="text-md font-bold">Auto Movie/Video Recap AI</h1>
            </div>
            <span class="bg-purple-900/40 text-purple-400 border border-purple-500/30 text-xs px-3 py-1 rounded-full font-semibold">1-Click Auto</span>
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4">
            <label class="text-xs font-bold text-gray-300 block mb-2 flex items-center gap-1">
                <i class="fa-brands fa-youtube text-red-500"></i> YouTube Video Link
            </label>
            <input type="text" id="yt-url" class="w-full bg-[#0b0e14] border border-gray-700 rounded-xl p-3 text-xs focus:outline-none focus:border-purple-500" placeholder="https://www.youtube.com/watch?v=...">
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4">
            <h3 class="text-xs font-bold text-gray-300 mb-3 flex items-center gap-1">
                <i class="fa-solid fa-sliders text-blue-400"></i> Recap Options
            </h3>
            <div class="space-y-3 text-xs">
                <div class="flex justify-between items-center">
                    <span>AI Voice Type</span>
                    <select id="voice-type" class="bg-[#0b0e14] border border-gray-700 rounded-lg px-2 py-1 text-xs">
                        <option value="my-MM-NilarNeural">မြန်မာ (အမျိုးသမီးသံ)</option>
                        <option value="my-MM-ThihaNeural">မြန်မာ (အမျိုးသားသံ)</option>
                    </select>
                </div>
                <label class="flex justify-between items-center">
                    <span>Flip Video (မူပိုင်ခွင့်လွတ်စေရန်)</span>
                    <input type="checkbox" id="flip-video" checked class="w-4 h-4 accent-purple-500 rounded">
                </label>
                <label class="flex justify-between items-center">
                    <span>Blur Subtitle (စာတန်းဟောင်း ဖုံးအုပ်မည်)</span>
                    <input type="checkbox" id="blur-sub" checked class="w-4 h-4 accent-purple-500 rounded">
                </label>
            </div>
        </div>

        <button onclick="startAutoRecap()" class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 font-bold py-3.5 rounded-2xl text-sm transition">
            <i class="fa-solid fa-bolt"></i> 1-Click Auto Recap စတင်ရန်
        </button>

        <div id="status-box" class="mt-5 hidden bg-[#151a23] border border-purple-500/50 rounded-2xl p-4 text-center">
            <p id="status-text" class="text-xs text-purple-400 mb-2 font-semibold">လုပ်ဆောင်နေပါသည်...</p>
            <div id="script-preview" class="text-[11px] text-gray-400 text-left bg-[#0b0e14] p-3 rounded-lg max-h-32 overflow-y-auto mb-3 hidden"></div>
            <div id="video-container"></div>
        </div>

        <script>
            async function startAutoRecap() {
                const url = document.getElementById('yt-url').value;
                const voice = document.getElementById('voice-type').value;
                const flip = document.getElementById('flip-video').checked;
                const blur = document.getElementById('blur-sub').checked;

                if (!url) return alert("YouTube Link ထည့်သွင်းပေးပါ");

                const statusBox = document.getElementById('status-box');
                const statusText = document.getElementById('status-text');
                const scriptPreview = document.getElementById('script-preview');
                const videoContainer = document.getElementById('video-container');

                statusBox.classList.remove('hidden');
                scriptPreview.classList.add('hidden');
                videoContainer.innerHTML = '';
                statusText.innerText = "⏳ YouTube Transcript ရယူပြီး Gemini AI ဖြင့် ဇာတ်ညွှန်း ရေးနေပါသည်...";

                const formData = new FormData();
                formData.append("url", url);
                formData.append("voice", voice);
                formData.append("flip", flip);
                formData.append("blur", blur);

                try {
                    const res = await fetch('/api/auto-recap', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        statusText.innerText = "✅ Auto Recap ပြီးစီးပါပြီ!";
                        scriptPreview.classList.remove('hidden');
                        scriptPreview.innerHTML = "<b>Recap Script:</b><br>" + data.script;
                        videoContainer.innerHTML = `
                            <video controls class="w-full rounded-xl border border-gray-700 mt-2" autoplay>
                                <source src="/get-file/${data.output_video}" type="video/mp4">
                            </video>
                        `;
                    } else {
                        statusText.innerText = "❌ အမှားဖြစ်သွားပါသည်: " + data.error;
                    }
                } catch(err) {
                    statusText.innerText = "❌ ချိတ်ဆက်မှု မအောင်မြင်ပါ";
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/get-file/{filename}")
def get_file(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/auto-recap")
async def auto_recap(
    url: str = Form(...),
    voice: str = Form("my-MM-NilarNeural"),
    flip: bool = Form(True),
    blur: bool = Form(True)
):
    try:
        session_id = uuid.uuid4().hex[:8]
        video_id = extract_video_id(url)
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL"}

        # 1. Transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'my', 'zh-Hans', 'ja', 'ko', 'hi'])
            raw_text = " ".join([item['text'] for item in transcript_list])
        except Exception:
            raw_text = "Action and dramatic video recap storyline."

        # 2. AI Script
        script_prompt = f"အောက်ပါ ဗီဒီယို ဇာတ်လမ်းကို လူကြိုက်များသော Facebook/TikTok Movie Recap ပုံစံဖြင့် စိတ်ဝင်စားဖွယ် မြန်မာစကားပြော ဇာတ်ညွှန်းအဖြစ် တိုတိုရှင်းရှင်း ပြန်ရေးပေးပါ: '{raw_text[:2500]}'"
        if client:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=script_prompt
            )
            recap_script = response.text
        else:
            recap_script = "ဒီဇာတ်ကားထဲမှာတော့ အဓိကဇာတ်ကောင်ဟာ စိတ်လှုပ်ရှားဖွယ် အဖြစ်အပျက်တွေနဲ့ ကြုံတွေ့ခဲ့ရပါတယ်။"

        # 3. Audio TTS
        audio_path = f"audio_{session_id}.mp3"
        communicate = edge_tts.Communicate(recap_script, voice)
        await communicate.save(audio_path)

        # 4. Download Video
        input_vid_path = f"video_{session_id}.mp4"
        output_vid_path = f"recap_final_{session_id}.mp4"

        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': input_vid_path,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 5. FFmpeg
        filters = []
        if flip:
            filters.append("hflip")
        if blur:
            filters.append("split[v1][v2];[v2]crop=iw:ih*0.18:0:ih*0.82,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.82")

        vf_str = ",".join(filters) if filters else "null"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_vid_path,
            "-i", audio_path,
            "-vf", vf_str,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            output_vid_path
        ]
        subprocess.run(cmd, check=True)

        return {"success": True, "script": recap_script, "output_video": output_vid_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
