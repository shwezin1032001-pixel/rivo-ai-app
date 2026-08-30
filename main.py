from fastapi import FastAPI, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
import edge_tts
import uuid
import os
import shutil
import subprocess

app = FastAPI(title="AI Story Narration Studio")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

tasks_db = {}

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return """
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Story Narration Studio</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#12141a] text-slate-100 font-sans p-4 max-w-md mx-auto min-h-screen pb-24 text-xs">

        <div class="text-center my-3">
            <span class="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">AI Video to Burmese Story</span>
            <h1 class="text-xl font-extrabold text-white mt-0.5">AI ဇာတ်ကြောင်းပြော & စာတန်းထိုး</h1>
        </div>

        <!-- Video Upload Area -->
        <div class="border border-dashed border-amber-500/50 bg-[#1a1d24] hover:bg-[#222630] rounded-2xl p-6 text-center cursor-pointer relative transition mb-4 shadow-lg">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleFileSelect()">
            <div class="w-12 h-12 bg-amber-500/10 text-amber-400 rounded-full flex items-center justify-center mx-auto mb-2 text-xl">
                <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <p id="file-label" class="font-bold text-slate-200">Video ရွေးပါ</p>
            <p class="text-[10px] text-slate-500 mt-1">MP4, MOV သို့မဟုတ် WEBM</p>
        </div>

        <!-- Script Area (Editable) -->
        <div class="mb-4">
            <div class="flex justify-between items-center mb-1.5">
                <label class="font-bold text-slate-300">🎬 ဇာတ်ကြောင်းပြော စာသား</label>
                <button type="button" onclick="generateAiScript()" class="text-amber-400 hover:text-amber-300 text-[10px] font-bold">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> AI ဖြင့် စာသားထုတ်မည်
                </button>
            </div>
            <textarea id="script-input" rows="4" class="w-full bg-[#1a1d24] border border-slate-700 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-amber-500 leading-relaxed" placeholder="ဗီဒီယိုရွေးပြီး 'AI ဖြင့် စာသားထုတ်မည်' ကို နှိပ်ပါ သို့မဟုတ် ကိုယ်တိုင် စာသား ရိုက်ထည့်နိုင်ပါသည်..."></textarea>
        </div>

        <!-- Voice Selection -->
        <div class="mb-4">
            <label class="font-bold text-slate-300 block mb-2">မြန်မာ AI အသံ ရွေးချယ်ရန်</label>
            <select id="voice-type" class="w-full bg-[#1a1d24] border border-slate-700 rounded-xl p-3 text-xs font-semibold text-white focus:outline-none focus:border-amber-500">
                <option value="my-MM-ThihaNeural">Thiha (အမျိုးသား ဇာတ်လမ်းပြောသံ)</option>
                <option value="my-MM-NilarNeural">Nilar (အမျိုးသမီး ဇာတ်လမ်းပြောသံ)</option>
            </select>
        </div>

        <!-- Submit Button -->
        <button id="btn-submit" onclick="startRenderVideo()" class="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-extrabold py-3.5 rounded-2xl text-sm shadow-xl flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-play"></i> ဇာတ်ကြောင်းပြော Video Render ပြုလုပ်မည်
        </button>

        <!-- Status Card -->
        <div id="status-card" class="mt-5 hidden bg-[#1a1d24] border border-slate-800 rounded-2xl p-4 shadow-xl">
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-slate-200">လုပ်ဆောင်ချက် အခြေအနေ</span>
                <span id="job-badge" class="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded-full font-semibold">လုပ်ဆောင်နေသည်</span>
            </div>
            <p id="status-text" class="text-[11px] text-slate-400 mb-3">ဗီဒီယိုနှင့် အသံကို ပေါင်းစပ်နေပါသည်...</p>
            <div id="video-result"></div>
        </div>

        <script>
            let selectedFile = null;
            let currentTaskId = null;
            let pollTimer = null;

            function handleFileSelect() {
                const input = document.getElementById('video-file');
                if (input.files && input.files[0]) {
                    selectedFile = input.files[0];
                    document.getElementById('file-label').innerText = "✅ " + selectedFile.name;
                }
            }

            async function generateAiScript() {
                if (!selectedFile) return alert("ကျေးဇူးပြု၍ Video ဖိုင် အရင်ရွေးချယ်ပါ");
                const scriptInput = document.getElementById('script-input');
                scriptInput.value = "⏳ AI က ဗီဒီယိုကို နားထောင်ပြီး ဇာတ်လမ်းစာသား ရေးဖွဲ့နေပါသည်... စက္ကန့် ၃၀ ခန့် စောင့်ပေးပါ...";

                const formData = new FormData();
                formData.append("file", selectedFile);

                try {
                    const res = await fetch('/api/generate-script', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        scriptInput.value = data.script;
                    } else {
                        scriptInput.value = "";
                        alert("Script Error: " + data.error);
                    }
                } catch(e) {
                    scriptInput.value = "";
                    alert("ချိတ်ဆက်မှု မအောင်မြင်ပါ");
                }
            }

            async function startRenderVideo() {
                if (!selectedFile) return alert("ကျေးဇူးပြု၍ Video ဖိုင် အရင်ရွေးချယ်ပါ");
                const scriptText = document.getElementById('script-input').value.trim();
                if (!scriptText) return alert("ကျေးဇူးပြု၍ ဇာတ်လမ်းစာသား ထည့်သွင်းပေးပါ");

                const btn = document.getElementById('btn-submit');
                const statusCard = document.getElementById('status-card');
                const statusText = document.getElementById('status-text');
                const jobBadge = document.getElementById('job-badge');
                const videoResult = document.getElementById('video-result');

                btn.disabled = true;
                btn.classList.add('opacity-50');
                statusCard.classList.remove('hidden');
                videoResult.innerHTML = '';
                jobBadge.className = "bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded-full font-semibold";
                jobBadge.innerText = "လုပ်ဆောင်နေသည်";
                statusText.innerText = "AI Myanmar အသံသွင်းယူပြီး ဗီဒီယိုနှင့် စာတန်းကို ပေါင်းစပ်နေပါသည်...";

                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("voice", document.getElementById('voice-type').value);
                formData.append("script", scriptText);

                try {
                    const res = await fetch('/api/render-video', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        currentTaskId = data.task_id;
                        trackProgress();
                    } else {
                        alert("Error: " + data.error);
                        btn.disabled = false;
                        btn.classList.remove('opacity-50');
                    }
                } catch(e) {
                    alert("ချိတ်ဆက်မှု မအောင်မြင်ပါ");
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                }
            }

            function trackProgress() {
                if (pollTimer) clearInterval(pollTimer);
                pollTimer = setInterval(async () => {
                    if (!currentTaskId) return;
                    try {
                        const res = await fetch('/api/task-status/' + currentTaskId);
                        const data = await res.json();
                        document.getElementById('status-text').innerText = data.detail;

                        if (data.status === 'completed') {
                            clearInterval(pollTimer);
                            document.getElementById('btn-submit').disabled = false;
                            document.getElementById('btn-submit').classList.remove('opacity-50');
                            document.getElementById('job-badge').className = "bg-emerald-500/20 text-emerald-400 text-[10px] px-2 py-0.5 rounded-full font-semibold";
                            document.getElementById('job-badge').innerText = "ပြီးစီးပါပြီ";
                            document.getElementById('video-result').innerHTML = `
                                <video controls class="w-full rounded-xl border border-slate-700 mt-2 shadow-inner" autoplay>
                                    <source src="/get-file/${data.output_video}" type="video/mp4">
                                </video>
                                <a href="/get-file/${data.output_video}" download class="w-full bg-amber-500 hover:bg-amber-400 text-black font-extrabold py-3 rounded-xl text-center flex items-center justify-center gap-1.5 transition mt-3">
                                    <i class="fa-solid fa-download"></i> တင်ရန်အသင့် MP4 သိမ်းရန်
                                </a>
                            `;
                        } else if (data.status === 'failed') {
                            clearInterval(pollTimer);
                            document.getElementById('btn-submit').disabled = false;
                            document.getElementById('btn-submit').classList.remove('opacity-50');
                            document.getElementById('job-badge').className = "bg-red-500/20 text-red-400 text-[10px] px-2 py-0.5 rounded-full font-semibold";
                            document.getElementById('job-badge').innerText = "မအောင်မြင်ပါ";
                        }
                    } catch(e) {}
                }, 1500);
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
    return {"status": "not_found", "detail": "Task not found"}

@app.post("/api/generate-script")
async def generate_script(file: UploadFile = File(...)):
    session_id = uuid.uuid4().hex[:8]
    input_vid = f"temp_{session_id}.mp4"
    extracted_audio = f"aud_{session_id}.mp3"
    try:
        with open(input_vid, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        subprocess.run(["ffmpeg", "-y", "-i", input_vid, "-vn", "-ar", "16000", "-ac", "1", extracted_audio], check=True)

        script = ""
        if client:
            try:
                audio_file = client.files.upload(file=extracted_audio)
                prompt = """
                ဤအသံဖိုင်ထဲတွင် ပါဝင်သော အဖြစ်အပျက်နှင့် စကားပြောများကို အစမှ အဆုံးအထိ သေချာနားထောင်ပါ။
                TikTok Movie Recap / Story Narration ပုံစံဖြင့် မြန်မာလို အစမှ အဆုံးအထိ စကားပြောဟန်ဖြင့် ဇာတ်ကြောင်း ပြန်ပြောပြသည့် စာသား အပြည့်အစုံ ရေးပေးပါ။
                
                စည်းကမ်းချက်များ -
                - ဗီဒီယိုအရှည်နှင့် အံဝင်ခွင်ကျဖြစ်အောင် စာသားကို ရှည်ရှည်ပြည့်ပြည့်စုံစုံ ရေးပေးပါ။
                - အစ၊ အလယ်၊ အဆုံး ခေါင်းစဉ်များ၊ နိဒါန်း၊ နိဂုံး ရှင်းလင်းချက် လုံးဝ မပါရ။ ဖတ်ပြမည့် စာသား သက်သက်သာ ရေးပေးပါ။
                """
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[audio_file, prompt]
                )
                script = response.text.strip()
            except Exception as ex:
                script = f"Error: {str(ex)}"
        else:
            script = "GEMINI_API_KEY မရှိသေးပါ။ Render Environment တွင် ထည့်သွင်းပေးပါ။"

        if os.path.exists(input_vid): os.remove(input_vid)
        if os.path.exists(extracted_audio): os.remove(extracted_audio)

        return {"success": True, "script": script}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def process_render_pipeline(task_id: str, input_vid: str, voice: str, script: str):
    try:
        ai_audio = f"tts_{task_id}.mp3"
        output_vid = f"story_final_{task_id}.mp4"

        tasks_db[task_id]["detail"] = "AI Myanmar အသံသွင်းနေပါသည်..."
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(ai_audio)

        tasks_db[task_id]["detail"] = "Blur အုပ်ပြီး ဗီဒီယိုနှင့် ပေါင်းစပ်နေပါသည်..."

        filter_complex = "split[v1][v2];[v2]crop=iw:ih*0.22:0:ih*0.78,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.78"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_vid,
            "-i", ai_audio,
            "-filter_complex", filter_complex,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            output_vid
        ]
        subprocess.run(cmd, check=True)

        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["detail"] = "✅ Recap Video ပြီးစီးပါပြီ!"
        tasks_db[task_id]["output_video"] = output_vid

        if os.path.exists(ai_audio): os.remove(ai_audio)
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["detail"] = f"Error: {str(e)}"

@app.post("/api/render-video")
async def render_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice: str = Form("my-MM-ThihaNeural"),
    script: str = Form(...)
):
    task_id = uuid.uuid4().hex[:8]
    input_vid = f"raw_{task_id}.mp4"

    with open(input_vid, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tasks_db[task_id] = {
        "status": "processing",
        "detail": "စတင် လုပ်ဆောင်နေပါသည်...",
        "output_video": ""
    }

    background_tasks.add_task(
        process_render_pipeline,
        task_id, input_vid, voice, script
    )

    return {"success": True, "task_id": task_id}
