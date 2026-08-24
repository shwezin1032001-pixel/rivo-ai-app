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

app = FastAPI(title="Professional Movie Recap AI Studio")

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
        <title>Professional Movie Recap AI</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#0b0e14] text-white font-sans p-4 max-w-md mx-auto min-h-screen pb-16">
        <div class="flex justify-between items-center mb-5">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-clapperboard text-red-500 text-xl"></i>
                <h1 class="text-md font-bold">Pro Movie/Drama Recap AI</h1>
            </div>
            <span class="bg-red-900/40 text-red-400 border border-red-500/30 text-xs px-3 py-1 rounded-full font-semibold">Short-Drama Edition</span>
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4 shadow-lg">
            <label class="text-xs font-bold text-gray-300 block mb-2 flex items-center gap-1">
                <i class="fa-brands fa-youtube text-red-500"></i> Video / YouTube URL
            </label>
            <input type="text" id="yt-url" class="w-full bg-[#0b0e14] border border-gray-700 rounded-xl p-3 text-xs focus:outline-none focus:border-red-500 text-gray-200" placeholder="https://www.youtube.com/watch?v=... သို့မဟုတ် ဗီဒီယိုလင့်ခ်">
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4">
            <h3 class="text-xs font-bold text-gray-300 mb-3 flex items-center gap-1">
                <i class="fa-solid fa-sliders text-yellow-400"></i> Recap Options
            </h3>
            <div class="space-y-3 text-xs">
                <div class="flex justify-between items-center">
                    <span>အသံအမျိုးအစား</span>
                    <select id="voice-type" class="bg-[#0b0e14] border border-gray-700 rounded-lg px-2 py-1 text-xs text-white">
                        <option value="my-MM-ThihaNeural">မြန်မာဇာတ်လမ်းပြော (အမျိုးသားသံ - Thiha)</option>
                        <option value="my-MM-NilarNeural">မြန်မာဇာတ်လမ်းပြော (အမျိုးသမီးသံ - Nilar)</option>
                    </select>
                </div>
                <label class="flex justify-between items-center">
                    <span>မူရင်းစာတန်းဟောင်း ဖျောက်/ဖုံးအုပ်မည်</span>
                    <input type="checkbox" id="blur-sub" checked class="w-4 h-4 accent-red-500 rounded">
                </label>
                <label class="flex justify-between items-center">
                    <span>ဗီဒီယို ဘယ်/ညာ လှန်မည် (Flip)</span>
                    <input type="checkbox" id="flip-video" checked class="w-4 h-4 accent-red-500 rounded">
                </label>
            </div>
        </div>

        <button onclick="startAutoRecap()" class="w-full bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 font-bold py-3.5 rounded-2xl text-sm transition shadow-lg flex items-center justify-center gap-2">
            <i class="fa-solid fa-film"></i> Pro Recap ဗီဒီယို စတင်ထုတ်လုပ်မည်
        </button>

        <div id="status-box" class="mt-5 hidden bg-[#151a23] border border-red-500/40 rounded-2xl p-4 text-center">
            <p id="status-text" class="text-xs text-red-400 mb-2 font-semibold">လုပ်ဆောင်နေပါသည်...</p>
            <div id="script-preview" class="text-[12px] leading-relaxed text-gray-300 text-left bg-[#0b0e14] p-3 rounded-lg max-h-36 overflow-y-auto mb-3 hidden border border-gray-800"></div>
            <div id="video-container"></div>
        </div>

        <script>
            async function startAutoRecap() {
                const url = document.getElementById('yt-url').value;
                const voice = document.getElementById('voice-type').value;
                const flip = document.getElementById('flip-video').checked;
                const blur = document.getElementById('blur-sub').checked;

                if (!url) return alert("ဗီဒီယို Link ထည့်ပေးပါ");

                const statusBox = document.getElementById('status-box');
                const statusText = document.getElementById('status-text');
                const scriptPreview = document.getElementById('script-preview');
                const videoContainer = document.getElementById('video-container');

                statusBox.classList.remove('hidden');
                scriptPreview.classList.add('hidden');
                videoContainer.innerHTML = '';
                statusText.innerText = "⏳ AI ဖြင့် ဇာတ်ညွှန်းရေးဖွဲ့ပြီး Movie Recap ဗီဒီယို ဖန်တီးနေပါသည်...";

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
                        statusText.innerText = "✅ Recap Video ထွက်ရှိပါပြီ!";
                        scriptPreview.classList.remove('hidden');
                        scriptPreview.innerHTML = "<b>🎬 ထွက်ရှိလာသော Recap ဇာတ်ညွှန်း:</b><br><br>" + data.script.replace(/\\n/g, '<br>');
                        videoContainer.innerHTML = `
                            <video controls class="w-full rounded-xl border border-gray-700 mt-2" autoplay>
                                <source src="/get-file/${data.output_video}" type="video/mp4">
                            </video>
                            <a href="/get-file/${data.output_video}" download class="inline-block mt-3 bg-gray-800 hover:bg-gray-700 text-xs px-4 py-2 rounded-xl text-white font-semibold">
                                <i class="fa-solid fa-download"></i> Recap Video ဒေါင်းလုဒ်ဆွဲရန်
                            </a>
                        `;
                    } else {
                        statusText.innerText = "❌ အမှားဖြစ်သွားပါသည်: " + data.error;
                    }
                } catch(err) {
                    statusText.innerText = "❌ စနစ် ချိတ်ဆက်မှု မအောင်မြင်ပါ";
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
    voice: str = Form("my-MM-ThihaNeural"),
    flip: bool = Form(True),
    blur: bool = Form(True)
):
    try:
        session_id = uuid.uuid4().hex[:8]
        video_id = extract_video_id(url)
        raw_text = ""

        if video_id:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'my', 'zh-Hans', 'zh-Hant', 'ja', 'ko', 'hi', 'id'])
                raw_text = " ".join([item['text'] for item in transcript_list])
            except Exception:
                raw_text = ""

        if not raw_text:
            raw_text = "ဇာတ်ကောင်ဟာ အန္တရာယ်ကြီးနဲ့ ကြုံတွေ့နေရပြီး အံ့သြဖွယ် အဖြစ်အပျက်တွေ ဆက်တိုက် ဖြစ်ပေါ်လာခဲ့ပါတယ်။"

        # Pro Recap Myanmar Script Prompt
        script_prompt = f"""
        သင်သည် Facebook နှင့် TikTok တွင် လူကြိုက်များသော နာမည်ကြီး Short Drama / Movie Recap Channel တစ်ခု၏ အသံသွင်းဇာတ်ညွှန်းဆရာ ဖြစ်သည်။
        အောက်ပါ မူရင်း ဗီဒီယို စာသား/ဇာတ်လမ်းကို အခြေခံပြီး တကယ့် Movie Recap စစ်စစ် အတိုင်း စိတ်ဝင်စားဖွယ် မြန်မာစကားပြော ဇာတ်ညွှန်းအဖြစ် ပြန်လည်ရေးသားပေးပါ:
        
        "{raw_text[:3000]}"
        
        လိုအပ်ချက်များ:
        - ဇာတ်ကောင်ပြောစကားများနှင့် ဇာတ်လမ်းအခြေအနေကို ဆွဲဆောင်မှုရှိရှိ သဘာဝကျကျ မြန်မာလို ပြောပေးပါ (ဥပမာ- 'သေလိုက်တော့... ငါ့အနား မလာနဲ့... တကယ်ကြီး ဖြစ်နေတာလား... အခု မင်းက ငါ့လူ ဖြစ်သွားပြီ' စသည့် ခံစားချက်ပါသော စကားပြောဟန်များ)။
        - မလိုအပ်သော နိဒါန်း၊ ခေါင်းစဉ်များ လုံးဝ မပါရ။ Voiceover အသံဖတ်ရန် သက်သက် မြန်မာစာသားများသာ ထုတ်ပေးပါ။
        """

        if client:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=script_prompt
            )
            recap_script = response.text.strip()
        else:
            recap_script = "သေလိုက်တော့... ငါ့အနားမလာနဲ့။ ဒါက ဘယ်သူလဲ... အတော်လေး ချောလွန်းတယ်။ မကြောက်နဲ့ ငါ မင်းကို အန္တရာယ် မပြုပါဘူး။"

        # Generate Audio TTS
        audio_path = f"audio_{session_id}.mp3"
        communicate = edge_tts.Communicate(recap_script, voice)
        await communicate.save(audio_path)

        # Download Video
        input_vid_path = f"video_{session_id}.mp4"
        output_vid_path = f"recap_pro_{session_id}.mp4"

        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': input_vid_path,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # FFmpeg Video Processing (Blur subtitle area, flip, overlay AI voice)
        filters = []
        if flip:
            filters.append("hflip")
        if blur:
            # Blur bottom 20% to cover hardcoded subtitles
            filters.append("split[v1][v2];[v2]crop=iw:ih*0.20:0:ih*0.80,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.80")

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

        return {
            "success": True,
            "script": recap_script,
            "output_video": output_vid_path
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
