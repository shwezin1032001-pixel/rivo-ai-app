from fastapi import FastAPI, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
import edge_tts
import uuid
import os
import shutil
import subprocess
import json
import asyncio

app = FastAPI(title="RecapKit MM Cloud Studio")

api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

# In-memory storage for Cloud Background Tasks
tasks_db = {}

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return """
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RecapKit MM - Pro AI Video Editor</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#0f172a] text-slate-100 font-sans p-3 max-w-lg mx-auto min-h-screen pb-24 text-xs">

        <div class="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
            <div class="flex items-center gap-2">
                <div class="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white shadow-lg">R</div>
                <div>
                    <h1 class="text-sm font-bold tracking-wide">RecapKit MM <span class="text-[10px] text-blue-400 font-mono">v1.8</span></h1>
                    <p class="text-[9px] text-slate-400">All-in-one AI Myanmar Movie Recap Studio</p>
                </div>
            </div>
            <span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1">
                <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span> Cloud Active
            </span>
        </div>

        <div class="grid grid-cols-2 gap-2 bg-slate-900/80 p-1 rounded-xl border border-slate-800 mb-4">
            <button class="bg-blue-600 text-white font-bold py-2 rounded-lg text-center flex items-center justify-center gap-1 shadow">
                <i class="fa-solid fa-bolt"></i> Cloud Background
            </button>
            <button class="text-slate-400 hover:text-white py-2 text-center flex items-center justify-center gap-1">
                <i class="fa-solid fa-mobile-screen"></i> Local Processing
            </button>
        </div>

        <div class="bg-slate-900 border-2 border-dashed border-blue-500/40 hover:border-blue-400 rounded-2xl p-5 text-center relative mb-4">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleFileSelect()">
            <div class="w-10 h-10 bg-blue-500/10 text-blue-400 rounded-full flex items-center justify-center mx-auto mb-2 text-lg">
                <i class="fa-solid fa-video"></i>
            </div>
            <p id="file-label" class="font-bold text-slate-200">Video ဖိုင် တင်ရန် နှိပ်ပါ</p>
            <p class="text-[10px] text-slate-500 mt-0.5">MP4, MOV, WEBM</p>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-3.5 mb-3">
            <h3 class="font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                <i class="fa-solid fa-compass text-blue-400"></i> Step 1: Perspective (ဇာတ်လမ်းပြောဟန်)
            </h3>
            <div class="grid grid-cols-3 gap-1.5 mb-2">
                <button type="button" onclick="setPerspective('direct', this)" class="persp-btn bg-blue-600 text-white py-1.5 rounded-lg font-semibold border border-blue-500">Direct</button>
                <button type="button" onclick="setPerspective('first', this)" class="persp-btn bg-slate-800 text-slate-300 py-1.5 rounded-lg border border-slate-700">First Person (I)</button>
                <button type="button" onclick="setPerspective('third', this)" class="persp-btn bg-slate-800 text-slate-300 py-1.5 rounded-lg border border-slate-700">Third Person</button>
            </div>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-3.5 mb-3">
            <h3 class="font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                <i class="fa-solid fa-microphone text-blue-400"></i> Step 2: Voice & Narration Speed
            </h3>
            <div class="grid grid-cols-2 gap-2 mb-3">
                <label class="bg-slate-800 p-2.5 rounded-xl border border-slate-700 flex items-center gap-2 cursor-pointer has-[:checked]:border-blue-500 has-[:checked]:bg-blue-950/40">
                    <input type="radio" name="voice" value="my-MM-ThihaNeural" checked class="accent-blue-500">
                    <div>
                        <p class="font-bold text-slate-200">THIHA</p>
                        <p class="text-[9px] text-slate-400">Microsoft Myanmar Male</p>
                    </div>
                </label>
                <label class="bg-slate-800 p-2.5 rounded-xl border border-slate-700 flex items-center gap-2 cursor-pointer has-[:checked]:border-blue-500 has-[:checked]:bg-blue-950/40">
                    <input type="radio" name="voice" value="my-MM-NilarNeural" class="accent-blue-500">
                    <div>
                        <p class="font-bold text-slate-200">NILAR</p>
                        <p class="text-[9px] text-slate-400">Microsoft Myanmar Female</p>
                    </div>
                </label>
            </div>
            <div>
                <div class="flex justify-between text-[11px] mb-1 text-slate-400">
                    <span>Narration Speed (အသံမြန်နှုန်း)</span>
                    <span id="speed-val" class="text-blue-400 font-bold">1.10x</span>
                </div>
                <input type="range" id="speed-range" min="0.8" max="1.3" step="0.05" value="1.10" oninput="document.getElementById('speed-val').innerText = this.value + 'x'" class="w-full accent-blue-500">
            </div>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-3.5 mb-4 space-y-2.5">
            <h3 class="font-bold text-slate-300 flex items-center gap-1.5">
                <i class="fa-solid fa-shield-halved text-blue-400"></i> Step 3: Subtitle & Copyright Bypass
            </h3>
            <label class="flex justify-between items-center bg-slate-800/60 p-2 rounded-xl border border-slate-700/50">
                <span>Remove Original Audio & Dub AI</span>
                <input type="checkbox" id="remove-audio" checked class="w-4 h-4 accent-blue-500 rounded">
            </label>
            <label class="flex justify-between items-center bg-slate-800/60 p-2 rounded-xl border border-slate-700/50">
                <span>Cover Original Subtitles (Blur Box)</span>
                <input type="checkbox" id="cover-sub" checked class="w-4 h-4 accent-blue-500 rounded">
            </label>
            <label class="flex justify-between items-center bg-slate-800/60 p-2 rounded-xl border border-slate-700/50">
                <span>Horizontal Flip (မူပိုင်ခွင့်ကျော်ရန်)</span>
                <input type="checkbox" id="flip-video" checked class="w-4 h-4 accent-blue-500 rounded">
            </label>
        </div>

        <button id="btn-start" onclick="startCloudJob()" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-lg flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-bolt"></i> Start Cloud Background Job
        </button>

        <div id="history-box" class="mt-5 bg-slate-900 border border-slate-800 rounded-2xl p-4 hidden">
            <h3 class="font-bold text-slate-200 mb-3 flex items-center justify-between">
                <span><i class="fa-solid fa-clock-rotate-left text-blue-400"></i> Output History</span>
                <button onclick="checkTaskStatus()" class="text-[10px] text-blue-400 hover:underline"><i class="fa-solid fa-arrows-rotate"></i> Refresh</button>
            </h3>
            <div id="job-card" class="bg-slate-800/80 border border-slate-700 rounded-xl p-3">
                <div class="flex justify-between items-center mb-1">
                    <span id="job-filename" class="font-mono text-[10px] text-slate-300 truncate w-36">processing...</span>
                    <span id="job-status-badge" class="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[9px] px-2 py-0.5 rounded-full">Processing</span>
                </div>
                <div class="w-full bg-slate-700 rounded-full h-1.5 my-2">
                    <div id="job-progress-bar" class="bg-blue-500 h-1.5 rounded-full transition-all duration-300" style="width: 15%"></div>
                </div>
                <p id="job-detail" class="text-[10px] text-slate-400">AI Script ရေးဖွဲ့နေပါသည်...</p>
                <div id="download-container" class="mt-3 hidden"></div>
            </div>
        </div>

        <script>
            let selectedFile = null;
            let currentPersp = 'direct';
            let activeTaskId = null;

            function handleFileSelect() {
                const input = document.getElementById('video-file');
                if (input.files && input.files[0]) {
                    selectedFile = input.files[0];
                    document.getElementById('file-label').innerText = "✅ " + selectedFile.name;
                }
            }

            function setPerspective(type, btn) {
                currentPersp = type;
                document.querySelectorAll('.persp-btn').forEach(b => {
                    b.className = "persp-btn bg-slate-800 text-slate-300 py-1.5 rounded-lg border border-slate-700";
                });
                btn.className = "persp-btn bg-blue-600 text-white py-1.5 rounded-lg font-semibold border border-blue-500";
            }

            async function startCloudJob() {
                if (!selectedFile) return alert("ဗီဒီယိုဖိုင် အရင်ရွေးချယ်ပေးပါ");

                const btn = document.getElementById('btn-start');
                const historyBox = document.getElementById('history-box');
                const jobFilename = document.getElementById('job-filename');

                btn.disabled = true;
                btn.classList.add('opacity-50');
                historyBox.classList.remove('hidden');
                jobFilename.innerText = selectedFile.name;

                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("perspective", currentPersp);
                formData.append("voice", document.querySelector('input[name="voice"]:checked').value);
                formData.append("speed", document.getElementById('speed-range').value);
                formData.append("flip", document.getElementById('flip-video').checked);
                formData.append("blur", document.getElementById('cover-sub').checked);

                try {
                    const res = await fetch('/api/start-cloud-job', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        activeTaskId = data.task_id;
                        trackProgress();
                    } else {
                        alert("Error: " + data.error);
                    }
                } catch(e) {
                    alert("ချိတ်ဆက်မှု မအောင်မြင်ပါ");
                } finally {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                }
            }

            function trackProgress() {
                const interval = setInterval(async () => {
                    if (!activeTaskId) return clearInterval(interval);
                    const res = await fetch(`/api/task-status/${activeTaskId}`);
                    const data = await res.json();
                    
                    document.getElementById('job-progress-bar').style.width = data.progress + "%";
                    document.getElementById('job-detail').innerText = data.detail;

                    if (data.status === 'completed') {
                        clearInterval(interval);
                        document.getElementById('job-status-badge').className = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[9px] px-2 py-0.5 rounded-full";
                        document.getElementById('job-status-badge').innerText = "Completed";
                        document.getElementById('download-container').classList.remove('hidden');
                        document.getElementById('download-container').innerHTML = `
                            <a href="/get-file/${data.output_video}" download class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded-xl text-center flex items-center justify-center gap-1.5 transition">
                                <i class="fa-solid fa-download"></i> Download Completed Recap Video
                            </a>
                        `;
                    } else if (data.status === 'failed') {
                        clearInterval(interval);
                        document.getElementById('job-status-badge').className = "bg-red-500/20 text-red-400 border border-red-500/30 text-[9px] px-2 py-0.5 rounded-full";
                        document.getElementById('job-status-badge').innerText = "Failed";
                    }
                }, 2000);
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

@app.get("/api/task-status/{task_id}")
def task_status(task_id: str):
    if task_id in tasks_db:
        return tasks_db[task_id]
    return {"status": "not_found", "progress": 0, "detail": "Task not found"}

async def process_recap_pipeline(task_id: str, input_vid: str, perspective: str, voice: str, speed: float, flip: bool, blur: bool):
    try:
        tasks_db[task_id]["progress"] = 20
        tasks_db[task_id]["detail"] = "1/4 အသံဖိုင် သီးသန့်ခွဲထုတ်နေပါသည်..."
        
        extracted_audio = f"aud_{task_id}.mp3"
        ai_audio = f"tts_{task_id}.mp3"
        output_vid = f"recapkit_{task_id}.mp4"

        subprocess.run(["ffmpeg", "-y", "-i", input_vid, "-vn", "-ar", "16000", "-ac", "1", extracted_audio], check=True)

        tasks_db[task_id]["progress"] = 45
        tasks_db[task_id]["detail"] = "2/4 Gemini AI ဖြင့် ဇာတ်ညွှန်း အပြည့်အစုံ ရေးဖွဲ့နေပါသည်..."

        script = ""
        if client and os.path.exists(extracted_audio):
            try:
                gemini_file = client.files.upload(file=extracted_audio)
                prompt = f"""
                ဤအသံဖိုင်ထဲတွင် ပါဝင်သော စကားပြောများနှင့် အဖြစ်အပျက်များကို အစမှ အဆုံးအထိ နားထောင်ပြီး RecapKit MM စတိုင် ({perspective} perspective) ဖြင့် မြန်မာစကားပြော ဇာတ်ညွှန်း အပြည့်အစုံ ရေးပေးပါ။
                ဇာတ်လမ်းကို အတိုချုံ့ခြင်း လုံးဝ မလုပ်ပါနှင့်။ အသံဖတ်ရန် သက်သက်သာ ရေးပေးပါ။
                """
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[gemini_file, prompt]
                )
                script = response.text.strip()
            except Exception:
                script = ""

        if not script:
            script = "ဒီနေရာမှာတော့ ကမ္ဘာပေါ်မှာ သိပ္ပံပညာနဲ့ ရှင်းပြလို့မရတဲ့ ထူးဆန်းတဲ့ အရာတွေ ဆက်တိုက် ဖြစ်ပေါ်လာခဲ့ပါတယ်။"

        tasks_db[task_id]["progress"] = 70
        tasks_db[task_id]["detail"] = "3/4 AI Myanmar Voiceover ထုတ်လုပ်နေပါသည်..."

        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(ai_audio)

        tasks_db[task_id]["progress"] = 85
        tasks_db[task_id]["detail"] = "4/4 FFmpeg Video & Audio Rendering ပြုလုပ်နေပါသည်..."

        filters = []
        if flip:
            filters.append("hflip")
        if blur:
            filters.append("split[v1][v2];[v2]crop=iw:ih*0.22:0:ih*0.78,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.78")

        vf_str = ",".join(filters) if filters else "null"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_vid,
            "-i", ai_audio,
            "-vf", vf_str,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            output_vid
        ]
        subprocess.run(cmd, check=True)

        tasks_db[task_id]["progress"] = 100
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["detail"] = "✅ One-Click Recap ပြီးစီးပါပြီ!"
        tasks_db[task_id]["output_video"] = output_vid

        if os.path.exists(extracted_audio):
            os.remove(extracted_audio)
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["detail"] = f"Error: {str(e)}"

@app.post("/api/start-cloud-job")
async def start_cloud_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    perspective: str = Form("direct"),
    voice: str = Form("my-MM-ThihaNeural"),
    speed: float = Form(1.10),
    flip: bool = Form(True),
    blur: bool = Form(True)
):
    task_id = uuid.uuid4().hex[:8]
    input_vid = f"raw_{task_id}.mp4"

    with open(input_vid, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tasks_db[task_id] = {
        "status": "processing",
        "progress": 5,
        "detail": "Cloud Job စတင်နေပါသည်...",
        "output_video": ""
    }

    background_tasks.add_task(
        process_recap_pipeline,
        task_id, input_vid, perspective, voice, speed, flip, blur
    )

    return {"success": True, "task_id": task_id}
