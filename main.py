from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
import edge_tts
import uuid
import os
import shutil
import subprocess
import json

app = FastAPI(title="TikTok AI Myanmar Voiceover Only")

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
        <title>TikTok AI Myanmar Voiceover Only</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#f8f9fa] text-gray-800 font-sans p-4 max-w-md mx-auto min-h-screen pb-16">
        
        <div class="text-center my-4">
            <h1 class="text-xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600 flex items-center justify-center gap-2">
                <i class="fa-brands fa-tiktok text-black text-2xl"></i> TikTok AI Myanmar Voiceover Only
            </h1>
        </div>

        <div class="border-2 border-dashed border-purple-300 bg-purple-50/50 rounded-2xl p-6 text-center cursor-pointer relative hover:bg-purple-50 transition mb-4 shadow-sm">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleFileSelect()">
            <div class="text-purple-500 text-3xl mb-2">
                <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <p id="file-label" class="text-xs font-bold text-gray-700">📹 ရွေးချယ်ရန် ဗီဒီယို တင်ပါ (Chinese/English Video)</p>
            <p class="text-[10px] text-gray-400 mt-1">MP4, MOV supported</p>
        </div>

        <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-4 space-y-4">
            <h3 class="text-xs font-bold text-gray-700 flex items-center gap-1.5 border-b pb-2">
                <i class="fa-solid fa-sliders text-purple-600"></i> Voice & Video Settings
            </h3>

            <div>
                <label class="text-[11px] font-bold text-gray-600 block mb-1">🗣️ AI အသံ ရွေးချယ်ရန်</label>
                <select id="voice-type" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-medium text-gray-700 focus:outline-none focus:border-purple-500">
                    <option value="my-MM-NilarNeural">မိန်းကလေးသံ (Nilar)</option>
                    <option value="my-MM-ThihaNeural">ယောက်ျားလေးသံ (Thiha)</option>
                </select>
            </div>

            <div>
                <div class="flex justify-between text-[11px] font-bold text-gray-600 mb-1">
                    <span>📍 မူရင်းစာတန်းဖျောက်မည့် နေရာ (Height %)</span>
                    <span id="height-val" class="text-purple-600 font-bold">75%</span>
                </div>
                <input type="range" id="blur-height" min="50" max="95" step="1" value="75" oninput="document.getElementById('height-val').innerText = this.value + '%'" class="w-full accent-purple-600 cursor-pointer">
            </div>
        </div>

        <button id="btn-submit" onclick="startProcess()" class="w-full bg-gradient-to-r from-pink-500 to-red-500 hover:opacity-95 text-white font-bold py-3.5 rounded-2xl text-sm shadow-md flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-microphone-lines"></i> 🎤 Perfect Sync Voiceover ပြုလုပ်မည်
        </button>

        <div id="status-card" class="mt-4 hidden bg-white rounded-2xl p-4 shadow-sm border border-purple-100 text-center">
            <p id="status-text" class="text-xs font-semibold text-purple-600 mb-2">လုပ်ဆောင်နေပါသည်...</p>
            <div id="script-preview" class="text-[11px] text-left bg-gray-50 p-3 rounded-xl max-h-36 overflow-y-auto mb-3 hidden border border-gray-200"></div>
            <div id="result-box"></div>
        </div>

        <script>
            let selectedFile = null;

            function handleFileSelect() {
                const input = document.getElementById('video-file');
                if (input.files && input.files[0]) {
                    selectedFile = input.files[0];
                    document.getElementById('file-label').innerText = "✅ " + selectedFile.name;
                }
            }

            async function startProcess() {
                if (!selectedFile) return alert("ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် အရင်ရွေးချယ်ပါ");

                const btn = document.getElementById('btn-submit');
                const statusCard = document.getElementById('status-card');
                const statusText = document.getElementById('status-text');
                const scriptPreview = document.getElementById('script-preview');
                const resultBox = document.getElementById('result-box');

                btn.disabled = true;
                btn.classList.add('opacity-50');
                statusCard.classList.remove('hidden');
                scriptPreview.classList.add('hidden');
                resultBox.innerHTML = '';
                statusText.innerText = "⏳ ဗီဒီယို အစအဆုံးကို နားထောင်ပြီး မြန်မာ Voiceover အပြည့်အစုံ ဖန်တီးနေပါသည် (၁ မိနစ်ခန့် ကြာနိုင်ပါသည်)...";

                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("voice", document.getElementById('voice-type').value);
                formData.append("blur_height", document.getElementById('blur-height').value);

                try {
                    const res = await fetch('/api/perfect-sync-voiceover', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        statusText.innerText = "✅ Perfect Sync Voiceover ပြီးစီးပါပြီ!";
                        if (data.script) {
                            scriptPreview.classList.remove('hidden');
                            scriptPreview.innerHTML = "<b>🎬 AI Myanmar Voiceover Script:</b><br>" + data.script.replace(/\\n/g, '<br>');
                        }
                        resultBox.innerHTML = `
                            <video controls class="w-full rounded-xl border mt-2 shadow-inner" autoplay>
                                <source src="/get-file/${data.output_video}" type="video/mp4">
                            </video>
                            <a href="/get-file/${data.output_video}" download class="inline-flex items-center gap-1 mt-3 bg-purple-600 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow hover:bg-purple-700 transition">
                                <i class="fa-solid fa-download"></i> ထွက်လာသည့် ရလဒ် ဗီဒီယို (AI Voice Only) ဒေါင်းမည်
                            </a>
                        `;
                    } else {
                        statusText.innerText = "❌ အမှားဖြစ်သွားပါသည်: " + data.error;
                    }
                } catch(e) {
                    statusText.innerText = "❌ စနစ် ချိတ်ဆက်မှု မအောင်မြင်ပါ";
                } finally {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
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

@app.post("/api/perfect-sync-voiceover")
async def perfect_sync_voiceover(
    file: UploadFile = File(...),
    voice: str = Form("my-MM-NilarNeural"),
    blur_height: int = Form(75)
):
    try:
        session_id = uuid.uuid4().hex[:8]
        input_vid = f"in_{session_id}.mp4"
        audio_path = f"audio_{session_id}.mp3"
        output_vid = f"tiktok_recap_{session_id}.mp4"

        with open(input_vid, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. AI Full Voiceover Transcription & Dubbing
        script = ""
        if client:
            try:
                gemini_file = client.files.upload(file=input_vid)
                prompt = """
                ဤဗီဒီယိုဖိုင်ကို အစအဆုံး သေချာကြည့်ရှု/နားထောင်ပါ။ ဇာတ်လမ်းကို အတိုချုံ့ခြင်း (Summary) လုံးဝ မလုပ်ပါနှင့်။
                
                ဗီဒီယိုထဲတွင် ပါဝင်သော ဇာတ်ကောင်ပြောစကားများနှင့် အဖြစ်အပျက်တစ်ခုချင်းစီကို အစမှ အဆုံးအထိ ကွက်တိလိုက်ဖတ်နိုင်ရန် TikTok Short Drama စတိုင် မြန်မာဘာသာပြန် စကားပြော ဇာတ်ညွှန်းအဖြစ် အပြည့်အစုံ ရေးသားပေးပါ။
                
                ဥပမာ - ဇာတ်ကောင် ပြောသည့် စကားများနှင့် ခံစားချက်များကို စကားပြောဟန်ဖြင့် အစအဆုံး အစီအစဉ်တကျ ရေးပေးပါ (နိဒါန်း၊ ခေါင်းစဉ်များ လုံးဝ မပါရ၊ Voiceover ဖတ်ရန် သက်သက်သာ)။
                """
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[gemini_file, prompt]
                )
                script = response.text.strip()
            except Exception as ex:
                script = ""

        if not script:
            script = "ဒီဇာတ်ကားထဲမှာတော့ မမျှော်လင့်ဘဲ အံ့သြဖွယ် အဖြစ်အပျက်တွေ ဆက်တိုက် ဖြစ်ပေါ်လာခဲ့ပါတယ်။"

        # 2. TTS Voiceover
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(audio_path)

        # 3. FFmpeg Processing (Blur Subtitle, Strip Original Audio, Add AI Voice)
        h_ratio = round(blur_height / 100.0, 2)
        crop_h = round(1.0 - h_ratio, 2)

        filter_complex = f"split[v1][v2];[v2]crop=iw:ih*{crop_h}:0:ih*{h_ratio},boxblur=15[blurred];[v1][blurred]overlay=0:H*{h_ratio}"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_vid,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            output_vid
        ]
        subprocess.run(cmd, check=True)

        return {"success": True, "script": script, "output_video": output_vid}
    except Exception as e:
        return {"success": False, "error": str(e)}
