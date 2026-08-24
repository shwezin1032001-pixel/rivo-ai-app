from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
from google.genai import types
import edge_tts
import uuid
import os
import shutil
import subprocess

app = FastAPI(title="Auto Video Understanding & Movie Recap AI")

api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return """
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Auto Movie Recap AI Studio</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#0b0e14] text-white font-sans p-4 max-w-md mx-auto min-h-screen pb-16">
        <div class="flex justify-between items-center mb-5">
            <div class="flex items-center gap-2">
                <i class="fa-solid fa-clapperboard text-red-500 text-xl"></i>
                <h1 class="text-md font-bold">Auto Movie Recap Studio</h1>
            </div>
            <span class="bg-red-900/40 text-red-400 border border-red-500/30 text-xs px-3 py-1 rounded-full font-semibold">Gemini AI Vision</span>
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-5 mb-4 text-center cursor-pointer relative hover:border-red-500/50 transition">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleVideoUpload()">
            <div class="w-12 h-12 bg-red-600/20 text-red-500 rounded-full flex items-center justify-center mx-auto mb-2 text-xl">
                <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <p id="upload-label" class="text-xs font-semibold text-gray-300">Tap to Upload Source Video</p>
            <p class="text-[10px] text-gray-500 mt-1">MP4, MOV supported</p>
        </div>

        <button id="btn-generate-script" onclick="generateAIScript()" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 font-bold py-3 rounded-xl text-xs mb-4 flex items-center justify-center gap-2 shadow-lg">
            <i class="fa-solid fa-wand-magic-sparkles"></i> 🪄 ဗီဒီယိုထဲမှ AI ဇာတ်ညွှန်း အလိုအလျောက် ထုတ်ယူမည်
        </button>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4">
            <label class="text-xs font-bold text-gray-300 block mb-2 flex items-center gap-1">
                <i class="fa-solid fa-pen-nib text-yellow-400"></i> Recap Script (မြန်မာဇာတ်ညွှန်း)
            </label>
            <textarea id="recap-script" rows="4" class="w-full bg-[#0b0e14] border border-gray-700 rounded-xl p-3 text-xs focus:outline-none focus:border-red-500 text-gray-200" placeholder="အပေါ်က 'AI ဇာတ်ညွှန်းထုတ်ယူမည်' ကို နှိပ်ပါ သို့မဟုတ် ကိုယ်တိုင် စာသားပြင်ဆင်ပါ..."></textarea>
        </div>

        <div class="bg-[#151a23] border border-gray-800 rounded-2xl p-4 mb-4 text-xs space-y-3">
            <div class="flex justify-between items-center">
                <span>အသံအမျိုးအစား</span>
                <select id="voice-type" class="bg-[#0b0e14] border border-gray-700 rounded-lg px-2 py-1 text-xs text-white">
                    <option value="my-MM-ThihaNeural">မြန်မာ (အမျိုးသားသံ - Thiha)</option>
                    <option value="my-MM-NilarNeural">မြန်မာ (အမျိုးသမီးသံ - Nilar)</option>
                </select>
            </div>
            <label class="flex justify-between items-center">
                <span>စာတန်းဟောင်း ဖုံးအုပ်မည် (Blur Subtitle)</span>
                <input type="checkbox" id="blur-sub" checked class="w-4 h-4 accent-red-500 rounded">
            </label>
            <label class="flex justify-between items-center">
                <span>ဗီဒီယို ဘယ်/ညာ လှန်မည် (Flip)</span>
                <input type="checkbox" id="flip-video" class="w-4 h-4 accent-red-500 rounded">
            </label>
        </div>

        <button onclick="renderRecapVideo()" class="w-full bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 font-bold py-3.5 rounded-2xl text-sm transition shadow-lg flex items-center justify-center gap-2">
            <i class="fa-solid fa-film"></i> ✨ Render Recap Video
        </button>

        <div id="status-box" class="mt-5 hidden bg-[#151a23] border border-red-500/40 rounded-2xl p-4 text-center">
            <p id="status-text" class="text-xs text-red-400 mb-2 font-semibold">လုပ်ဆောင်နေပါသည်...</p>
            <div id="video-container"></div>
        </div>

        <script>
            let uploadedFileObj = null;

            function handleVideoUpload() {
                const input = document.getElementById('video-file');
                if (input.files && input.files[0]) {
                    uploadedFileObj = input.files[0];
                    document.getElementById('upload-label').innerText = "✅ " + uploadedFileObj.name;
                }
            }

            async function generateAIScript() {
                if (!uploadedFileObj) return alert("ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် အရင်ရွေးချယ်ပေးပါ");
                const btn = document.getElementById('btn-generate-script');
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI က ဗီဒီယိုကို နားထောင်ပြီး ဇာတ်ညွှန်းရေးနေပါသည်...';
                btn.disabled = true;

                const formData = new FormData();
                formData.append("file", uploadedFileObj);

                try {
                    const res = await fetch('/api/auto-transcribe-script', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        document.getElementById('recap-script').value = data.script;
                    } else {
                        alert("Error: " + data.error);
                    }
                } catch(e) {
                    alert("ချိတ်ဆက်မှု မအောင်မြင်ပါ");
                } finally {
                    btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> 🪄 ဗီဒီယိုထဲမှ AI ဇာတ်ညွှန်း အလိုအလျောက် ထုတ်ယူမည်';
                    btn.disabled = false;
                }
            }

            async function renderRecapVideo() {
                if (!uploadedFileObj) return alert("ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် ရွေးချယ်ပေးပါ");
                const script = document.getElementById('recap-script').value;
                if (!script) return alert("Recap Script ထည့်သွင်းပေးပါ");

                const voice = document.getElementById('voice-type').value;
                const flip = document.getElementById('flip-video').checked;
                const blur = document.getElementById('blur-sub').checked;

                const statusBox = document.getElementById('status-box');
                const statusText = document.getElementById('status-text');
                const videoContainer = document.getElementById('video-container');

                statusBox.classList.remove('hidden');
                videoContainer.innerHTML = '';
                statusText.innerText = "⏳ AI အသံသွင်းပြီး ဗီဒီယိုနှင့် ပေါင်းစပ်နေပါသည်...";

                const formData = new FormData();
                formData.append("file", uploadedFileObj);
                formData.append("script", script);
                formData.append("voice", voice);
                formData.append("flip", flip);
                formData.append("blur", blur);

                try {
                    const res = await fetch('/api/render-video', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        statusText.innerText = "✅ Recap Video ပြီးစီးပါပြီ!";
                        videoContainer.innerHTML = `
                            <video controls class="w-full rounded-xl border border-gray-700 mt-2" autoplay>
                                <source src="/get-file/${data.output_video}" type="video/mp4">
                            </video>
                            <a href="/get-file/${data.output_video}" download class="inline-block mt-3 bg-red-600 hover:bg-red-500 text-xs px-4 py-2 rounded-xl text-white font-semibold">
                                <i class="fa-solid fa-download"></i> Recap Video ဒေါင်းလုဒ်ဆွဲရန်
                            </a>
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

@app.post("/api/auto-transcribe-script")
async def auto_transcribe_script(file: UploadFile = File(...)):
    try:
        session_id = uuid.uuid4().hex[:8]
        temp_video = f"temp_in_{session_id}.mp4"
        with open(temp_video, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload to Gemini File API for Video Understanding
        if client:
            gemini_file = client.files.upload(file=temp_video)
            prompt = """
            ဤဗီဒီယိုဖိုင်ထဲတွင် ပါဝင်သော စကားပြောသံများ၊ ဇာတ်ကောင်များ၏ လှုပ်ရှားမှုနှင့် အခြေအနေများကို နားထောင်/ကြည့်ရှုပြီး Facebook/TikTok တွင် လူကြိုက်များသော Drama Movie Recap စတိုင် မြန်မာစကားပြော ဇာတ်ညွှန်းအဖြစ် တိုက်ရိုက် ရေးသားပေးပါ။
            
            ဥပမာ စတိုင် - 'သေလိုက်တော့... ငါ့အနား မလာနဲ့... ဒါက ဘယ်သူလဲ အတော်လေး ချောတာပဲ... မကြောက်နဲ့ ငါ မင်းကို အန္တရာယ် မပြုပါဘူး... အခု မင်းက ငါ့လူ ဖြစ်သွားပြီ...'
            
            လိုအပ်ချက်:
            - အပို နိဒါန်း၊ ခေါင်းစဉ်များ လုံးဝ မပါရ။
            - Voiceover အဖြစ် တန်းဖတ်ရုံ မြန်မာစာသားများ သာ သဘာဝကျကျ ထုတ်ပေးပါ။
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[gemini_file, prompt]
            )
            script = response.text.strip()
        else:
            script = "သေလိုက်တော့... ငါ့အနားမလာနဲ့။ ဒါက ဘယ်သူလဲ... အတော်လေး ချောလွန်းတယ်။ မကြောက်နဲ့ ငါ မင်းကို အန္တရာယ် မပြုပါဘူး။"

        if os.path.exists(temp_video):
            os.remove(temp_video)

        return {"success": True, "script": script}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/render-video")
async def render_video(
    file: UploadFile = File(...),
    script: str = Form(...),
    voice: str = Form("my-MM-ThihaNeural"),
    flip: bool = Form(False),
    blur: bool = Form(True)
):
    try:
        session_id = uuid.uuid4().hex[:8]
        input_vid = f"in_{session_id}.mp4"
        audio_path = f"audio_{session_id}.mp3"
        output_vid = f"recap_final_{session_id}.mp4"

        with open(input_vid, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. TTS Audio Generation
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(audio_path)

        # 2. FFmpeg Filters (Blur & Flip)
        filters = []
        if flip:
            filters.append("hflip")
        if blur:
            filters.append("split[v1][v2];[v2]crop=iw:ih*0.22:0:ih*0.78,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.78")

        vf_str = ",".join(filters) if filters else "null"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_vid,
            "-i", audio_path,
            "-vf", vf_str,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            output_vid
        ]
        subprocess.run(cmd, check=True)

        return {"success": True, "output_video": output_vid}
    except Exception as e:
        return {"success": False, "error": str(e)}
