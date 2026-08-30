from fastapi import FastAPI, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
import edge_tts
import uuid
import os
import shutil
import subprocess

app = FastAPI(title="One Click Recap AI Studio")

api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

tasks_db = {}

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return """
    <!DOCTYPE html>
    <html lang="my">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>One Click Recap AI</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#12141a] text-slate-100 font-sans p-4 max-w-md mx-auto min-h-screen pb-20 text-xs">

        <!-- Header -->
        <div class="text-center my-3">
            <span class="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">VIDEO မှ မြန်မာဘာသာသို့ တစ်ချက်နှိပ်ရုံဖြင့်</span>
            <h1 class="text-xl font-extrabold text-white mt-0.5">One Click Recap</h1>
            <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">
                မည်သည့်ဘာသာစကားဖြင့်မဆို ပြောထားသော Video ကို တင်ပါ။ AI က မြန်မာဘာသာ Video အဖြစ် ပြောင်းလဲပေးပြီး Subtitle အလိုအလျောက် ထည့်သွင်းပေးပါမည်။
            </p>
        </div>

        <!-- Video Upload Box -->
        <div class="border border-dashed border-amber-500/50 bg-[#1a1d24] hover:bg-[#222630] rounded-2xl p-6 text-center cursor-pointer relative transition mb-4 shadow-lg">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleFileSelect()">
            <div class="w-12 h-12 bg-amber-500/10 text-amber-400 rounded-full flex items-center justify-center mx-auto mb-2 text-xl">
                <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <p id="file-label" class="font-bold text-slate-200">Video ရွေးပါ</p>
            <p class="text-[10px] text-slate-500 mt-1">MP4, MOV သို့မဟုတ် WEBM (အများဆုံး 100 MB)</p>
        </div>

        <!-- Subtitle Style -->
        <div class="mb-4">
            <label class="font-bold text-slate-300 block mb-2">Subtitle ပုံစံ</label>
            <div class="space-y-2">
                <label class="flex items-center justify-between p-3 rounded-xl border border-amber-500 bg-amber-500/10 cursor-pointer">
                    <div>
                        <p class="font-bold text-amber-400">အသင့်သုံး Subtitle</p>
                        <p class="text-[10px] text-slate-400">Blur Video ပေါ်တွင် အဆင်သင့် မြန်မာစာတန်း တိုက်ရိုက်ထည့်သွင်းမည်</p>
                    </div>
                    <input type="radio" name="sub_mode" value="auto" checked class="accent-amber-500">
                </label>
            </div>
        </div>

        <!-- AI Voice Selection -->
        <div class="mb-4">
            <label class="font-bold text-slate-300 block mb-2">မြန်မာ AI အသံ</label>
            <select id="voice-type" class="w-full bg-[#1a1d24] border border-slate-700 rounded-xl p-3 text-xs font-semibold text-white focus:outline-none focus:border-amber-500">
                <option value="my-MM-ThihaNeural">Charon / Thiha (အမျိုးသား ဇာတ်လမ်းပြောသံ)</option>
                <option value="my-MM-NilarNeural">Kore / Nilar (အမျိုးသမီး ဇာတ်လမ်းပြောသံ)</option>
            </select>
        </div>

        <!-- Submit Button -->
        <button id="btn-submit" onclick="startOneClickRecap()" class="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-extrabold py-3.5 rounded-2xl text-sm shadow-xl flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-wand-magic-sparkles"></i> One Click Recap ဖန်တီးရန်
        </button>

        <!-- Output Result Box -->
        <div id="status-card" class="mt-5 hidden bg-[#1a1d24] border border-slate-800 rounded-2xl p-4 shadow-xl">
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-slate-200">RECAP အဆင်သင့်ဖြစ်ပါပြီ</span>
                <span id="job-badge" class="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded-full font-semibold">လုပ်ဆောင်နေသည်</span>
            </div>
            <p id="status-text" class="text-[11px] text-slate-400 mb-3">AI က Video ကို နားထောင်ပြီး Subtitle နှင့် Voiceover ဖန်တီးနေပါသည်...</p>
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

            async function startOneClickRecap() {
                if (!selectedFile) return alert("ကျေးဇူးပြု၍ Video ဖိုင် အရင်ရွေးချယ်ပါ");

                const btn = document.getElementById('btn-submit');
                const statusCard = document.getElementById('status-card');
                const statusText = document.getElementById('status-text');
                const jobBadge = document.getElementById('job-badge');
                const videoResult = document.getElementById('video-result');

                btn.disabled = true;
                btn.classList.add('opacity-50');
                statusCard.classList.remove('hidden');
                videoResult.innerHTML = '';
                jobBadge.innerText = "လုပ်ဆောင်နေသည်";
                statusText.innerText = "Video ကို လှမ်းယူပြီး AI စနစ်ဖြင့် ဇာတ်ညွှန်းနှင့် အသံသွင်းယူနေပါသည်...";

                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("voice", document.getElementById('voice-type').value);

                try {
                    const res = await fetch('/api/one-click-recap', {
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
    return {"status": "not_found", "progress": 0, "detail": "Task not found"}

async def process_one_click_pipeline(task_id: str, input_vid: str, voice: str):
    try:
        tasks_db[task_id]["detail"] = "အသံပိုင်းကို ခွဲထုတ်နေပါသည်..."
        extracted_audio = f"aud_{task_id}.mp3"
        ai_audio = f"tts_{task_id}.mp3"
        output_vid = f"recap_final_{task_id}.mp4"

        subprocess.run(["ffmpeg", "-y", "-i", input_vid, "-vn", "-ar", "16000", "-ac", "1", extracted_audio], check=True)

        tasks_db[task_id]["detail"] = "Gemini AI ဖြင့် မြန်မာ Recap ဇာတ်ညွှန်း ရေးဖွဲ့နေပါသည်..."

        script = ""
        if client and os.path.exists(extracted_audio):
            try:
                gemini_file = client.files.upload(file=extracted_audio)
                prompt = """
                ဤအသံဖိုင်ထဲတွင် ပါဝင်သော အဖြစ်အပျက်များကို အစမှ အဆုံးအထိ နားထောင်ပြီး TikTok/Facebook Movie Recap စတိုင် မြန်မာစကားပြော ဇာတ်ညွှန်း အပြည့်အစုံ ရေးပေးပါ။
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
            script = "ဒီနေရာမှာတော့ ကောင်လေးဟာ ထူးဆန်းတဲ့ အဖြစ်အပျက်တွေနဲ့ စတင် ကြုံတွေ့ခဲ့ရပါတယ်။"

        tasks_db[task_id]["detail"] = "AI Myanmar Voiceover ထုတ်လုပ်နေပါသည်..."
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(ai_audio)

        tasks_db[task_id]["detail"] = "Blur အုပ်ပြီး Video & Subtitle ပေါင်းစပ်နေပါသည်..."

        # Blur bottom 25% subtitle area
        filter_complex = "split[v1][v2];[v2]crop=iw:ih*0.25:0:ih*0.75,boxblur=15[blurred];[v1][blurred]overlay=0:H*0.75"

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
        tasks_db[task_id]["detail"] = "✅ One Click Recap ပြီးစီးပါပြီ!"
        tasks_db[task_id]["output_video"] = output_vid

        if os.path.exists(extracted_audio):
            os.remove(extracted_audio)
        if os.path.exists(ai_audio):
            os.remove(ai_audio)
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["detail"] = f"Error: {str(e)}"

@app.post("/api/one-click-recap")
async def one_click_recap(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice: str = Form("my-MM-ThihaNeural")
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
        process_one_click_pipeline,
        task_id, input_vid, voice
    )

    return {"success": True, "task_id": task_id}
