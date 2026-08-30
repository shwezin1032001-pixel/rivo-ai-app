from fastapi import FastAPI, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from google import genai
import edge_tts
import uuid
import os
import shutil
import subprocess

app = FastAPI(title="AI Story Narration Studio")

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
        <title>AI Story Narration Studio</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-[#12141a] text-slate-100 font-sans p-4 max-w-md mx-auto min-h-screen pb-20 text-xs">

        <div class="text-center my-3">
            <span class="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">AI Video to Burmese Story</span>
            <h1 class="text-xl font-extrabold text-white mt-0.5">AI ဇာတ်ကြောင်းပြော & စာတန်းထိုး Studio</h1>
            <p class="text-[11px] text-slate-400 mt-1 leading-relaxed">
                Video တင်လိုက်သည်နှင့် AI က ဇာတ်လမ်းတစ်ပုဒ်လုံးကို အစအဆုံး မြန်မာအသံဖြင့် ဖတ်ပြပြီး စာတန်းထိုးပါ ထည့်ပေးပါမည်။
            </p>
        </div>

        <div class="border border-dashed border-amber-500/50 bg-[#1a1d24] hover:bg-[#222630] rounded-2xl p-6 text-center cursor-pointer relative transition mb-4 shadow-lg">
            <input type="file" id="video-file" accept="video/*" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" onchange="handleFileSelect()">
            <div class="w-12 h-12 bg-amber-500/10 text-amber-400 rounded-full flex items-center justify-center mx-auto mb-2 text-xl">
                <i class="fa-solid fa-cloud-arrow-up"></i>
            </div>
            <p id="file-label" class="font-bold text-slate-200">Video ရွေးပါ</p>
            <p class="text-[10px] text-slate-500 mt-1">MP4, MOV သို့မဟုတ် WEBM</p>
        </div>

        <div class="mb-4">
            <label class="font-bold text-slate-300 block mb-2">မြန်မာ AI အသံ ရွေးချယ်ရန်</label>
            <select id="voice-type" class="w-full bg-[#1a1d24] border border-slate-700 rounded-xl p-3 text-xs font-semibold text-white focus:outline-none focus:border-amber-500">
                <option value="my-MM-ThihaNeural">Thiha (အမျိုးသား ဇာတ်လမ်းပြောသံ)</option>
                <option value="my-MM-NilarNeural">Nilar (အမျိုးသမီး ဇာတ်လမ်းပြောသံ)</option>
            </select>
        </div>

        <button id="btn-submit" onclick="startStoryProcess()" class="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-extrabold py-3.5 rounded-2xl text-sm shadow-xl flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-wand-magic-sparkles"></i> ဇာတ်ကြောင်းပြော & စာတန်းထိုး ပြုလုပ်မည်
        </button>

        <div id="status-card" class="mt-5 hidden bg-[#1a1d24] border border-slate-800 rounded-2xl p-4 shadow-xl">
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold text-slate-200">လုပ်ဆောင်ချက် အခြေအနေ</span>
                <span id="job-badge" class="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded-full font-semibold">လုပ်ဆောင်နေသည်</span>
            </div>
            <p id="status-text" class="text-[11px] text-slate-400 mb-3">ဗီဒီယိုကို ကြည့်ရှုပြီး ဇာတ်လမ်း အပြည့်အစုံ ရေးဖွဲ့နေပါသည်...</p>
            <div id="script-preview" class="text-[11px] text-left bg-black/40 p-3 rounded-xl max-h-36 overflow-y-auto mb-3 hidden border border-slate-800 leading-relaxed text-gray-300"></div>
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

            async function startStoryProcess() {
                if (!selectedFile) return alert("ကျေးဇူးပြု၍ Video ဖိုင် အရင်ရွေးချယ်ပါ");

                const btn = document.getElementById('btn-submit');
                const statusCard = document.getElementById('status-card');
                const statusText = document.getElementById('status-text');
                const jobBadge = document.getElementById('job-badge');
                const scriptPreview = document.getElementById('script-preview');
                const videoResult = document.getElementById('video-result');

                btn.disabled = true;
                btn.classList.add('opacity-50');
                statusCard.classList.remove('hidden');
                scriptPreview.classList.add('hidden');
                videoResult.innerHTML = '';
                jobBadge.innerText = "လုပ်ဆောင်နေသည်";
                statusText.innerText = "ဗီဒီယိုကို နားထောင်ပြီး ဇာတ်လမ်းအစအဆုံး ရေးဖွဲ့နေပါသည်...";

                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("voice", document.getElementById('voice-type').value);

                try {
                    const res = await fetch('/api/create-story-narration', {
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

                        if (data.script && document.getElementById('script-preview').classList.contains('hidden')) {
                            document.getElementById('script-preview').classList.remove('hidden');
                            document.getElementById('script-preview').innerHTML = "<b>🎬 AI ဇာတ်လမ်း စာသား:</b><br>" + data.script.replace(/\\n/g, '<br>');
                        }

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

async def process_story_pipeline(task_id: str, input_vid: str, voice: str):
    try:
        tasks_db[task_id]["detail"] = "အသံပိုင်းကို ခွဲထုတ်နေပါသည်..."
        extracted_audio = f"aud_{task_id}.mp3"
        ai_audio = f"tts_{task_id}.mp3"
        output_vid = f"story_final_{task_id}.mp4"

        subprocess.run(["ffmpeg", "-y", "-i", input_vid, "-vn", "-ar", "16000", "-ac", "1", extracted_audio], check=True)

        tasks_db[task_id]["detail"] = "Gemini AI ဖြင့် ဇာတ်ကြောင်းပြော စာသား အစအဆုံး ရေးဖွဲ့နေပါသည်..."

        prompt = """
        ဤအသံဖိုင်ထဲတွင် ပါဝင်သော အဖြစ်အပျက်နှင့် စကားပြောများကို အစမှ အဆုံးအထိ သေချာနားထောင်ပါ။
        ထို့နောက် TikTok Story/Movie Recap ပုံစံဖြင့် မြန်မာလို အစမှ အဆုံးအထိ စကားပြောဟန်ဖြင့် ဇာတ်ကြောင်း ပြန်ပြောပြသည့် စာသား (Story Narration) အပြည့်အစုံ ရေးပေးပါ။
        
        ဥပမာပုံစံ -
        "ငါ့ကို အပြစ်မတင်ပါနဲ့ မင်းမရှိမှပဲ ငါ သူဌေးအိမ်ကို အိမ်ထောင်ပြုဝင်နိုင်မှာ ကောင်းကောင်းမွန်မွန် နေနိုင်မှာ။ အလိုလို ရောက်လာတဲ့ အသားတုံးပဲ... ငါ မင်းကို ခဏတော့ ကယ်နိုင်ပေမဲ့ တစ်သက်လုံးတော့ မစောင့်ရှောက်နိုင်ဘူး..."
        
        စည်းကမ်းချက်များ -
        - ဗီဒီယိုအရှည်နှင့် အံဝင်ခွင်ကျဖြစ်အောင် စာသားကို ရှည်ရှည်ပြည့်ပြည့်စုံစုံ ရေးပေးပါ။
        - အစ၊ အလယ်၊ အဆုံး ခေါင်းစဉ်များ၊ နိဒါန်း၊ နိဂုံး ရှင်းလင်းချက် လုံးဝ မပါရ။ ဖတ်ပြမည့် စာသား သက်သက်သာ ရေးပေးပါ။
        """

        script = ""
        if client and os.path.exists(extracted_audio):
            try:
                gemini_file = client.files.upload(file=extracted_audio)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[gemini_file, prompt]
                )
                script = response.text.strip()
            except Exception:
                script = ""

        if not script:
            script = "ဒီနေရာမှာတော့ ထူးဆန်းတဲ့ အဖြစ်အပျက်တွေ စတင်ခဲ့ပြီး မမျှော်လင့်ဘဲ အခြေအနေတွေ ပြောင်းလဲသွားခဲ့ပါတယ်။"

        tasks_db[task_id]["script"] = script
        tasks_db[task_id]["detail"] = "AI Myanmar Voiceover ထုတ်လုပ်နေပါသည်..."
        
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(ai_audio)

        tasks_db[task_id]["detail"] = "Blur အုပ်ပြီး ဗီဒီယိုနှင့် အသံကို ပေါင်းစပ်နေပါသည်..."

        # Subtitle blur filter (bottom 22%)
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
        tasks_db[task_id]["detail"] = "✅ ဇာတ်ကြောင်းပြော Recap ပြီးစီးပါပြီ!"
        tasks_db[task_id]["output_video"] = output_vid

        if os.path.exists(extracted_audio):
            os.remove(extracted_audio)
        if os.path.exists(ai_audio):
            os.remove(ai_audio)
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["detail"] = f"Error: {str(e)}"

@app.post("/api/create-story-narration")
async def create_story_narration(
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
        "output_video": "",
        "script": ""
    }

    background_tasks.add_task(
        process_story_pipeline,
        task_id, input_vid, voice
    )

    return {"success": True, "task_id": task_id}
