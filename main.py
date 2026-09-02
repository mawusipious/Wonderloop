from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re, uuid, threading, subprocess, math, textwrap, json, datetime, os, shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
JOBS: Dict[str, dict] = {}
PROJECTS: Dict[str, dict] = {}
LOCK = threading.Lock()
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
CHAR_FILE = DATA / 'characters.json'
BIBLE_FILE = DATA / 'story_bibles.json'
PROFILE_FILE = DATA / 'profile.json'
PROJECT_FILE = DATA / 'projects.json'
EDITED_PLANS: Dict[str, list] = {}
MAX_ACTIVE_JOBS = int(os.getenv('WONDERLOOP_MAX_ACTIVE_JOBS', '2'))
MAX_PROJECTS = int(os.getenv('WONDERLOOP_MAX_PROJECTS', '100'))

def load_json(path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text())
    except Exception: return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def load_projects():
    return load_json(PROJECT_FILE, {})

def persist_projects():
    save_json(PROJECT_FILE, PROJECTS)

PROJECTS.update(load_projects())


app = FastAPI(title='WonderLoop API', version='1.2.1')
ALLOWED_ORIGINS = [x.strip() for x in os.getenv('WONDERLOOP_ALLOWED_ORIGINS', '*').split(',') if x.strip()] or ['*']
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=['*'], allow_headers=['*'])

BLOCKED_PATTERNS = [r'\bsexual\b', r'\bporn\b', r'\bnud(e|ity)\b', r'\bexplicit sex\b', r'\bkill myself\b', r'\bsuicide\b', r'\bself[- ]?harm\b', r'\bterrorist\b']
def safety_check(text: str):
    lowered = text.lower()
    hits = [pat for pat in BLOCKED_PATTERNS if re.search(pat, lowered)]
    return (not hits, hits)

@app.get('/api/health')
def health():
    active = sum(1 for j in JOBS.values() if j.get('status') in ('queued','rendering'))
    return {'status':'ok','version':'1.2.1','ffmpeg':shutil.which('ffmpeg') is not None,'espeak':shutil.which('espeak') is not None,'active_jobs':active,'max_active_jobs':MAX_ACTIVE_JOBS}

@app.post('/api/safety/check')
def check_safety(payload: dict):
    text = str(payload.get('text',''))[:5000]
    ok, _ = safety_check(text)
    return {'allowed': ok, 'message': 'Prompt accepted.' if ok else 'Prompt needs revision for WonderLoop kids-safe mode.'}

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    length: str = '3 minutes'
    style: str = '3D Cartoon'
    format: str = 'YouTube 16:9'
    visual_mode: str = 'WonderLoop Illustrated'
    character_id: str | None = None
    bible_id: str | None = None
    music: bool = True
    narration: bool = True
    captions: bool = True
    language: str = 'English'
    creator_id: str = 'local-creator'

class Scene(BaseModel):
    number: int
    duration_seconds: int
    visual_prompt: str
    narration: str

class PlanResponse(BaseModel):
    job_id: str
    status: str
    title: str
    hook: str
    scenes: List[Scene]

class Character(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    species: str = 'friendly character'
    personality: str = 'kind, playful and curious'
    appearance: str = 'bright, colorful and child-friendly'
    voice: str = 'cheerful'

class StoryBible(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=120)
    world: str = 'A safe, colorful and imaginative world for children.'
    rules: List[str] = []
    characters: List[str] = []

class CreatorProfile(BaseModel):
    id: str = 'local-creator'
    name: str = 'WonderLoop Creator'
    language: str = 'English'

class ProjectSummary(BaseModel):
    job_id: str
    title: str
    created_at: str
    status: str
    video_url: str | None = None
    language: str = 'English'
    format: str = 'YouTube 16:9'

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    title: str
    video_url: str | None = None
    error: str | None = None


def character_context(character_id=None):
    chars = load_json(CHAR_FILE, [])
    if character_id:
        return [c for c in chars if c.get('id') == character_id]
    return chars

def bible_context(bible_id=None):
    bibles = load_json(BIBLE_FILE, [])
    if bible_id:
        return [b for b in bibles if b.get('id') == bible_id]
    return bibles

def topic_from_prompt(prompt: str) -> str:
    p = prompt.lower()
    if 'fruit' in p: return 'fruits'
    if 'number' in p or 'count' in p: return 'numbers'
    if 'abc' in p or 'alphabet' in p: return 'the alphabet'
    if 'color' in p or 'colour' in p: return 'colours'
    words = re.findall(r"[A-Za-z']+", prompt)
    return ' '.join(words[-5:]) or 'a fun lesson'


def make_plan(req: GenerateRequest):
    topic = topic_from_prompt(req.prompt)
    saved_chars = character_context(req.character_id)
    saved_bibles = bible_context(req.bible_id)
    char_hint = saved_chars[0]['name'] if saved_chars else 'a friendly character'
    bible_hint = saved_bibles[0]['world'] if saved_bibles else 'a safe, colorful world for children'
    title = f"A Fun Song About {topic.title()}"
    hook = f"Come sing and learn as we discover {topic} with {char_hint}!"
    if topic == 'fruits':
        lines = [
            'Wash your fruit and get ready to sing!',
            'Crunch the apple, yum yum yum!',
            'Peel the banana, one by one!',
            'Sweet mango dancing in the sun!',
            'Watermelon slices are so much fun!',
            'Try different fruits as part of a balanced meal.',
            'Clap your hands and sing it again!',
            'Bye-bye from all our fruity friends!'
        ]
        subjects = ['apple','banana','mango','watermelon','grapes','fruit basket','all the fruits','fruit friends']
    else:
        lines = [
            f'We are ready to learn about {topic}!', f'Let us discover {topic} together!',
            'Let us sing it slowly, then sing it fast!', f'Learning {topic} can be fun!',
            'Point, clap and learn with me!', f'Great job learning about {topic}!',
            'Sing it again with your new friends!', 'Bye-bye, friends!'
        ]
        subjects = [topic] * 8
    total = {'1 minute': 60, '3 minutes': 180, '5 minutes': 300}.get(req.length, 180)
    base = total // 8
    scenes=[]
    for i in range(8):
        dur = base if i < 7 else total - base*7
        scenes.append(Scene(number=i+1, duration_seconds=dur,
            visual_prompt=f"{req.visual_mode}, {req.style}, {char_hint}, {bible_hint}, cheerful child-friendly character, colorful setting, friendly {subjects[i]}, safe wholesome playful scene, consistent design, focus on {topic}.",
            narration=lines[i]))
    return title, hook, scenes


def font(size):
    candidates=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for c in candidates:
        if Path(c).exists(): return ImageFont.truetype(c,size)
    return ImageFont.load_default()


def draw_scene(path: Path, scene: Scene, topic: str, size=(1280,720), style='3D Cartoon', character_name='Wonder'):
    img=Image.new('RGB',size,(255,247,220)); d=ImageDraw.Draw(img)
    w,h=size
    palettes = {
        '2D Cartoon': ((183,229,255),(139,214,124)),
        '3D Cartoon': ((166,222,255),(125,205,116)),
        'Storybook': ((238,220,190),(176,205,143)),
    }
    sky,ground=palettes.get(style,palettes['3D Cartoon'])
    d.rectangle((0,0,w,h*0.68), fill=sky); d.rectangle((0,h*0.68,w,h), fill=ground)
    # sun
    d.ellipse((w-170,50,w-60,160), fill=(255,210,70))
    # clouds
    for x,y in [(100,100),(330,150),(700,90)]:
        for dx,dy,r in [(0,15,35),(35,0,45),(75,18,30)]: d.ellipse((x+dx-r,y+dy-r,x+dx+r,y+dy+r), fill='white')
    # simple trees
    for x in [90,w-120]:
        d.rectangle((x-12,h*0.43,x+12,h*0.72), fill=(126,83,47)); d.ellipse((x-75,h*0.30,x+75,h*0.55), fill=(78,177,83))
    # character body/head
    cx,cy=w*0.5,h*0.47
    d.ellipse((cx-115,cy-130,cx+115,cy+100), fill=(255,210,170), outline=(80,80,80), width=4)
    d.rectangle((cx-90,cy+95,cx+90,cy+230), fill=(88,145,230), outline=(70,70,70), width=4)
    d.ellipse((cx-45,cy-55,cx-25,cy-35), fill=(40,40,40)); d.ellipse((cx+25,cy-55,cx+45,cy-35), fill=(40,40,40))
    d.arc((cx-45,cy-20,cx+45,cy+50),0,180,fill=(120,40,40),width=5)
    # topic object
    label=topic.title()
    box=(cx+170,cy-30,cx+430,cy+150)
    d.rounded_rectangle(box, radius=35, fill=(255,255,255), outline=(90,90,90), width=4)
    f=font(42)
    tw=d.textbbox((0,0),label,font=f)[2]
    d.text(((box[0]+box[2]-tw)/2,box[1]+50),label,font=f,fill=(40,70,100))
    # scene caption
    caption=f"Scene {scene.number}: {scene.narration}"
    wrapped='\n'.join(textwrap.wrap(caption,width=55))
    d.rounded_rectangle((35,35,w-35,170), radius=28, fill=(255,255,255), outline=(80,80,80), width=3)
    d.text((60,55), wrapped, font=font(34), fill=(35,45,60), spacing=8)
    name_label=f'{character_name} • {style}'
    d.text((60,h-55), name_label, font=font(22), fill=(45,55,65))
    img.save(path)


def render_job(job_id, req: GenerateRequest):
    try:
        with LOCK:
            JOBS[job_id].update(status='rendering', progress=3, phase='planning scenes')
        title, hook, scenes = make_plan(req)
        if job_id in EDITED_PLANS:
            scenes = [Scene(**x) for x in EDITED_PLANS.pop(job_id)]
        topic = topic_from_prompt(req.prompt)
        work = OUT / job_id
        work.mkdir(exist_ok=True)
        if req.format == 'Shorts 9:16': size=(720,1280)
        elif req.format == 'Square 1:1': size=(1080,1080)
        else: size=(1280,720)
        fps = 12
        selected = character_context(req.character_id)
        cname = selected[0]['name'] if selected else 'WonderLoop Friend'

        # 1) Render every scene as a still image.
        for i, sc in enumerate(scenes, 1):
            draw_scene(work/f'scene_{i}.png', sc, topic, size=size, style=req.style, character_name=cname)
            with LOCK:
                JOBS[job_id]['progress'] = 5 + int(i/len(scenes)*38)
                JOBS[job_id]['phase'] = f'creating scene {i} of {len(scenes)}'

        # 2) Create an SRT subtitle track from the scene narration.
        def ts(sec):
            ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
            return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
        elapsed = 0
        srt = work/'captions.srt'
        with srt.open('w', encoding='utf-8') as sf:
            for i, sc in enumerate(scenes, 1):
                sf.write(f'{i}\n{ts(elapsed)} --> {ts(elapsed+sc.duration_seconds)}\n{sc.narration}\n\n')
                elapsed += sc.duration_seconds

        # 3) Assemble the visual track using FFmpeg concat. Each scene gets a gentle zoom.
        concat = work/'concat.txt'
        with concat.open('w') as f:
            for i, sc in enumerate(scenes, 1):
                p=(work/f'scene_{i}.png').as_posix().replace("'", "'\\''")
                f.write(f"file '{p}'\nduration {sc.duration_seconds}\n")
            f.write(f"file '{(work/'scene_8.png').as_posix()}'\n")
        silent = work/'visuals.mp4'
        vf = f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease,pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
        subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-vf',vf,'-r',str(fps),'-c:v','libx264','-preset','veryfast','-crf','25','-movflags','+faststart',str(silent)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with LOCK:
            JOBS[job_id]['progress']=50; JOBS[job_id]['phase']='assembling video'

        # 4) Narration per scene, then concatenate so timing follows the visual scenes.
        total=sum(sc.duration_seconds for sc in scenes)
        narration_parts=[]
        if req.narration:
            for i,sc in enumerate(scenes,1):
                wav=work/f'narration_{i}.wav'; padded=work/f'narration_{i}_padded.wav'
                voice_map={'English':'en','French':'fr','Spanish':'es','German':'de','Italian':'it','Portuguese':'pt','Hindi':'hi','Arabic':'ar'}
                voice=voice_map.get(req.language,'en')
                subprocess.run(['espeak','-v',voice,'-w',str(wav),'-s','145','-p','55',sc.narration],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                subprocess.run(['ffmpeg','-y','-i',str(wav),'-af',f'apad=pad_dur={sc.duration_seconds}','-t',str(sc.duration_seconds),str(padded)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                narration_parts.append(padded)
            nconcat=work/'narration_concat.txt'
            with nconcat.open('w') as nf:
                for part in narration_parts: nf.write(f"file '{part.as_posix()}'\n")
            narration=work/'narration.wav'
            subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(nconcat),'-c','copy',str(narration)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            narration=work/'silence.wav'
            subprocess.run(['ffmpeg','-y','-f','lavfi','-i',f'anullsrc=r=44100:cl=mono:d={total}','-c:a','pcm_s16le',str(narration)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with LOCK:
            JOBS[job_id]['progress']=70; JOBS[job_id]['phase']='creating voice track'

        # 5) Lightweight local music bed.
        music=work/'music.wav'
        if req.music:
            subprocess.run(['ffmpeg','-y','-f','lavfi','-i',f"sine=frequency=392:sample_rate=44100:duration={total}",'-af','volume=0.045',str(music)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['ffmpeg','-y','-f','lavfi','-i',f'anullsrc=r=44100:cl=mono:d={total}','-c:a','pcm_s16le',str(music)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with LOCK:
            JOBS[job_id]['progress']=82; JOBS[job_id]['phase']='mixing voice and music'

        # 6) Final assembly: captions are burned into the video; voice/music are mixed into AAC.
        final=work/'wonderloop_video.mp4'
        subtitle_path=str(srt).replace('\\','/').replace(':','\\:')
        video_input='[0:v]'
        if req.captions:
            filter_complex=f"[0:v]subtitles='{subtitle_path}':force_style='FontName=DejaVu Sans,FontSize=20,Outline=2,MarginV=35'[v];[1:a][2:a]amix=inputs=2:duration=longest:dropout_transition=2[a]"
        else:
            filter_complex="[0:v]null[v];[1:a][2:a]amix=inputs=2:duration=longest:dropout_transition=2[a]"
        subprocess.run(['ffmpeg','-y','-i',str(silent),'-i',str(narration),'-i',str(music),'-filter_complex',filter_complex,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','25','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(final)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

        # 7) Produce a thumbnail and machine-readable project manifest.
        thumb=work/'thumbnail.png'; Image.open(work/'scene_1.png').save(thumb)
        manifest={'version':'1.2.1','job_id':job_id,'title':title,'hook':hook,'prompt':req.prompt,'length':req.length,'style':req.style,'format':req.format,'language':req.language,'creator_id':req.creator_id,'character_id':req.character_id,'bible_id':req.bible_id,'scenes':[s.model_dump() for s in scenes],'files':{'video':'wonderloop_video.mp4','thumbnail':'thumbnail.png','captions':'captions.srt'}}
        (work/'project.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
        with LOCK:
            JOBS[job_id].update(status='completed',progress=100,title=title,video_url=f'/api/jobs/{job_id}/video',phase='video ready with captions, voice and music')
            PROJECTS[job_id]=dict(PROJECTS.get(job_id, {}), status='completed', title=title, video_url=f'/api/jobs/{job_id}/video', language=req.language, format=req.format)
            persist_projects()
    except Exception as e:
        with LOCK:
            JOBS[job_id].update(status='failed',progress=100,error=str(e),phase='failed')


@app.get('/api/characters')
def list_characters():
    return load_json(CHAR_FILE, [])

@app.post('/api/characters')
def create_character(character: Character):
    chars = load_json(CHAR_FILE, [])
    item = character.model_dump()
    item['id'] = str(uuid.uuid4())
    item['created_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
    chars.append(item)
    save_json(CHAR_FILE, chars)
    return item

@app.delete('/api/characters/{character_id}')
def delete_character(character_id: str):
    chars = load_json(CHAR_FILE, [])
    new = [c for c in chars if c.get('id') != character_id]
    save_json(CHAR_FILE, new)
    return {'deleted': len(chars) != len(new)}

@app.get('/api/story-bibles')
def list_bibles():
    return load_json(BIBLE_FILE, [])

@app.post('/api/story-bibles')
def create_bible(bible: StoryBible):
    bibles = load_json(BIBLE_FILE, [])
    item = bible.model_dump()
    item['id'] = str(uuid.uuid4())
    item['created_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
    bibles.append(item)
    save_json(BIBLE_FILE, bibles)
    return item

@app.delete('/api/story-bibles/{bible_id}')
def delete_bible(bible_id: str):
    bibles = load_json(BIBLE_FILE, [])
    new = [b for b in bibles if b.get('id') != bible_id]
    save_json(BIBLE_FILE, new)
    return {'deleted': len(bibles) != len(new)}

@app.get('/')
def root(): return {'app':'WonderLoop','status':'ok','version':'1.2.1','pipeline':'one-prompt video creation','features':['AI Copilot plan','character library','story bible','illustrated scenes','captions','voice','music','mp4','thumbnail','project manifest','scene editor','kids-safe prompt guard','health diagnostics','production configuration']}

@app.get('/api/projects', response_model=List[ProjectSummary])
def list_projects():
    PROJECTS.update(load_projects())
    return sorted(PROJECTS.values(), key=lambda x:x.get('created_at',''), reverse=True)

@app.get('/api/profile')
def get_profile():
    return load_json(PROFILE_FILE, {'id':'local-creator','name':'WonderLoop Creator','language':'English'})

@app.put('/api/profile')
def update_profile(profile: CreatorProfile):
    data=profile.model_dump()
    save_json(PROFILE_FILE, data)
    return data

@app.put('/api/projects/{job_id}')
def update_project(job_id: str, payload: dict):
    PROJECTS.update(load_projects())
    if job_id not in PROJECTS: return {'error':'Project not found'}
    if isinstance(payload.get('title'), str) and payload['title'].strip(): PROJECTS[job_id]['title']=payload['title'].strip()
    persist_projects()
    manifest=OUT/job_id/'project.json'
    if manifest.exists():
        data=json.loads(manifest.read_text(encoding='utf-8')); data['title']=PROJECTS[job_id]['title']; manifest.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    return PROJECTS[job_id]

@app.delete('/api/projects/{job_id}')
def delete_project(job_id: str):
    PROJECTS.update(load_projects())
    if job_id not in PROJECTS: return {'deleted':False}
    PROJECTS.pop(job_id, None); persist_projects()
    shutil.rmtree(OUT/job_id, ignore_errors=True)
    return {'deleted':True}

@app.get('/api/languages')
def languages():
    return {'languages':['English','French','Spanish','Portuguese','German','Italian','Hindi','Arabic'], 'note':'Voice availability depends on locally installed eSpeak voices.'}

@app.get('/api/formats')
def formats():
    return {'formats':[{'name':'YouTube 16:9','width':1280,'height':720},{'name':'Shorts 9:16','width':720,'height':1280},{'name':'Square 1:1','width':1080,'height':1080}]}

@app.get('/api/projects/{job_id}')
def get_project(job_id: str):
    PROJECTS.update(load_projects())
    if job_id not in PROJECTS: return {'error':'Project not found'}
    return PROJECTS[job_id]

@app.get('/api/jobs/{job_id}/download')
def download_video(job_id: str):
    path=OUT/job_id/'wonderloop_video.mp4'
    if not path.exists(): return {'error':'Video is not ready'}
    return FileResponse(path,media_type='video/mp4',filename='wonderloop_video.mp4',headers={'Content-Disposition':'attachment; filename="wonderloop_video.mp4"'})

@app.post('/api/generate', response_model=JobResponse)
def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    allowed, _ = safety_check(req.prompt)
    if not allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail='Prompt blocked by WonderLoop kids-safe mode. Please rewrite it as age-appropriate content.')
    active = sum(1 for j in JOBS.values() if j.get('status') in ('queued','rendering'))
    if active >= MAX_ACTIVE_JOBS:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail='WonderLoop is busy. Please try again shortly.')
    if len(PROJECTS) >= MAX_PROJECTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail='Project limit reached. Delete an old project to continue.')
    job_id=str(uuid.uuid4())
    title,_,_=make_plan(req)
    JOBS[job_id]={'status':'queued','progress':0,'title':title,'video_url':None,'error':None,'phase':'queued'}
    PROJECTS[job_id]={'job_id':job_id,'title':title,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'queued','video_url':None,'language':req.language,'format':req.format,'creator_id':req.creator_id}
    persist_projects()
    background_tasks.add_task(render_job,job_id,req)
    return JobResponse(job_id=job_id,status='queued',progress=0,title=title)

@app.get('/api/jobs/{job_id}', response_model=JobResponse)
def job(job_id:str):
    if job_id not in JOBS: return JobResponse(job_id=job_id,status='not_found',progress=0,title='')
    return JobResponse(job_id=job_id,**JOBS[job_id])


@app.get('/api/jobs/{job_id}/scenes')
def scenes(job_id: str):
    path=OUT/job_id/'project.json'
    if not path.exists(): return {'error':'Project is not ready'}
    data=json.loads(path.read_text(encoding='utf-8'))
    return {'job_id':job_id,'title':data.get('title',''),'scenes':data.get('scenes',[]),'files':data.get('files',{})}

@app.put('/api/jobs/{job_id}/scenes/{scene_number}')
def edit_scene(job_id: str, scene_number: int, payload: dict):
    path=OUT/job_id/'project.json'
    if not path.exists(): return {'error':'Project is not ready'}
    data=json.loads(path.read_text(encoding='utf-8'))
    scenes=data.get('scenes',[])
    if scene_number < 1 or scene_number > len(scenes): return {'error':'Scene not found'}
    scene=scenes[scene_number-1]
    for key in ('narration','visual_prompt'):
        if key in payload and isinstance(payload[key],str): scene[key]=payload[key]
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    return {'saved':True,'scene':scene}

@app.post('/api/jobs/{job_id}/rebuild')
def rebuild(job_id: str, background_tasks: BackgroundTasks):
    path=OUT/job_id/'project.json'
    if not path.exists(): return {'error':'Project is not ready'}
    data=json.loads(path.read_text(encoding='utf-8'))
    req=GenerateRequest(prompt=data.get('prompt',''),length=data.get('length','1 minute'),style=data.get('style','3D Cartoon'),format=data.get('format','YouTube 16:9'),language=data.get('language','English'),creator_id=data.get('creator_id','local-creator'),visual_mode=data.get('visual_mode','WonderLoop Illustrated'),character_id=data.get('character_id'),bible_id=data.get('bible_id'),music=data.get('music',True),narration=data.get('narration',True),captions=data.get('captions',True))
    # Reuse the edited scene plan by storing it for the renderer.
    JOBS[job_id]={'status':'queued','progress':0,'title':data.get('title','WonderLoop Video'),'video_url':None,'error':None}
    EDITED_PLANS[job_id]=data.get('scenes',[])
    background_tasks.add_task(render_job,job_id,req)
    return {'job_id':job_id,'status':'queued'}

@app.get('/api/jobs/{job_id}/thumbnail')
def thumbnail(job_id:str):
    path=OUT/job_id/'thumbnail.png'
    if not path.exists(): return {'error':'Thumbnail is not ready'}
    return FileResponse(path,media_type='image/png',filename='thumbnail.png')

@app.get('/api/jobs/{job_id}/project')
def project(job_id:str):
    path=OUT/job_id/'project.json'
    if not path.exists(): return {'error':'Project is not ready'}
    return FileResponse(path,media_type='application/json',filename='project.json')

@app.get('/api/jobs/{job_id}/video')
def video(job_id:str):
    path=OUT/job_id/'wonderloop_video.mp4'
    if not path.exists(): return {'error':'Video is not ready'}
    return FileResponse(path,media_type='video/mp4',filename='wonderloop_video.mp4')
