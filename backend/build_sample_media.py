"""Build original, code-drawn demo media. Dev tools: pip install Pillow imageio-ffmpeg."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
OUT=Path(__file__).resolve().parent.parent/'frontend/public/demo-posts'
OUT.mkdir(parents=True,exist_ok=True)
def text(x,y,value,size=18,color='#9fb1ca'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(value)}</text>'
def box(x,y,w,h,color='#18283d'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{color}" stroke="#30445f"/>'
def save(name,title,subtitle,body):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-label="{escape(title)}"><rect width="960" height="540" fill="#0e1726"/><g font-family="Arial,sans-serif">{text(40,42,"KEYSTONE / BUILDER NOTES",12,"#78acff")}{text(40,91,title,30,"#edf4ff")}{text(40,123,subtitle,15)}{body}{text(40,511,"ILLUSTRATIVE SAMPLE / PROJECT PROTOTYPE",11,"#7487a2")}</g></svg>'
    (OUT/name).write_text(svg,encoding='utf-8')
body=box(40,151,568,326)+box(632,151,288,326)
body+='<path d="M70 434H578" stroke="#40536b" stroke-width="2"/><path d="M185 424L185 335L315 233L448 302L485 353" fill="none" stroke="#609cff" stroke-width="25" stroke-linejoin="round"/>'
for i,(x,y) in enumerate([(185,335),(315,233),(448,302),(485,353)]):
    body+=f'<circle cx="{x}" cy="{y}" r="15" fill="#15243a" stroke="#b8ddff" stroke-width="4"/>'+text(x+20,y-17,f'J{i+1}',12,'#b8ddff')
body+='<path d="M474 365L465 390M496 363L506 390" stroke="#b8ddff" stroke-width="7" stroke-linecap="round"/><path d="M468 391H505L500 425H474Z" fill="#efbb54"/><ellipse cx="486" cy="391" rx="18" ry="5" fill="#ffe1a3"/>'+box(142,424,85,10,'#7287a4')
for i,(a,b) in enumerate([('04','Degrees of freedom'),('3D','Printed arm concept'),('NEXT','Wrist feedback loop')]):
    y=208+i*91;body+=text(658,y,a,27,'#78acff')+text(658,y+28,b,15)
save('rover-arm.svg','First pick-up. Next: a steadier wrist.','A four-joint rover arm concept, reaching for a sample cup.',body)
body=box(40,151,410,326)+box(474,151,446,326)
for x,label in [(65,'BEFORE / COLOR ALONE'),(499,'AFTER / CLEAR STATUS')]:
    body+=text(x,187,label,12,'#78acff')+box(x,214,360,194,'#101b2b')+text(x+20,247,'Campus arrivals',21,'#eff5ff')+text(x+20,285,'Campus Loop North',17,'#d7e3f5')+text(x+20,316,'Thompson Library',14)+text(x+20,368,'Next bus',13)+text(x+265,370,'8 min',24,'#f8c86b')
body+='<circle cx="396" cy="281" r="6" fill="#f8c86b"/>'+box(714,266,123,32,'#443521')+text(729,288,'DELAYED',12,'#ffda8c')+text(65,445,'A color change is easy to miss.',14)+text(499,445,'State the delay in plain language.',14)
save('bus-arrivals.svg','A delay you can actually notice.','Arrival interface study / replace a color-only cue with a clear label.',body)
body=box(40,151,340,326)+box(404,151,516,326)+text(65,190,'ROOM FINDER',13,'#78acff')+text(65,236,'A quiet place,',28,'#edf4ff')+text(65,273,'one tap away.',28,'#edf4ff')+text(65,316,'Thompson Library',17)+box(65,341,288,43,'#283f60')+text(85,369,'Free now / 2+ seats',16,'#dfeaff')+text(65,432,'Mobile-first interface prototype',13)+text(65,453,'Illustrative availability only',12)
for i,(room,seats,status) in enumerate([('Room 204','4 seats','Available now'),('Room 310','2 seats','Free for 2 hours'),('Room 412','6 seats','Available now')]):
    y=172+i*94;body+=box(425,y,474,79,'#142236')+text(446,y+29,room,18,'#edf4ff')+text(446,y+54,seats,13)+box(711,y+23,169,30,'#173e34')+text(725,y+43,status,12,'#88e0bb')
save('study-room.svg','Find a room. Get back to studying.','A study-room finder concept for Thompson Library.',body)
body=''
for i,(title,lines) in enumerate([('Question',['What decision will this help?','Define a useful outcome.']),('Dataset',['Check source and missingness.','Start with a simple plot.']),('Model',['Establish a baseline first.','Test against your question.'])]):
    x=40+i*300;body+=box(x,167,280,272)+text(x+23,210,f'0{i+1}',24,'#78acff')+text(x+23,254,title,25,'#edf4ff')
    for j,line in enumerate(lines):body+=text(x+23,300+j*30,line,13)
    if i<2:body+=f'<path d="M{x+285} 300h10m-5-5 5 5-5 5" stroke="#78acff" stroke-width="2" fill="none"/>'
body+=text(40,475,'Understand the problem before reaching for a model.',16,'#c1cfe2')
save('data-project.svg','Start with the question.','A practical reading-list framework for your next data project.',body)
font_path=Path('C:/Windows/Fonts/arial.ttf')
if not font_path.exists():font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def font(n):return ImageFont.truetype(str(font_path),n) if font_path.exists() else ImageFont.load_default(size=n)
W,H,FPS=720,408,24
writer=imageio_ffmpeg.write_frames(str(OUT/'onboarding.mp4'),(W,H),fps=FPS,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=7,macro_block_size=2,output_params=['-movflags','+faststart'])
writer.send(None)
steps=[('Welcome to Keystone','Build something with people who care.','Create your builder profile',['Your name','Your major / interests']),('Make it yours','Pick the skills you bring to the team.','Choose your skills',['Python','Design','React']),('Find your next team','Meet builders with complementary skills.','Explore projects',['Campus transit / Frontend','Rover dashboard / Embedded'])]
for frame in range(FPS*9):
    t=frame/FPS;index=min(int(t//3),2);local=t%3
    image=Image.new('RGB',(W,H),'#0e1726');d=ImageDraw.Draw(image)
    d.text((25,19),'KEYSTONE / ONBOARDING PROTOTYPE',font=font(12),fill='#77aaff')
    d.text((25,365),'ILLUSTRATIVE SAMPLE / INTERFACE MOTION STUDY',font=font(10),fill='#788ba6')
    d.text((25,94),steps[index][0],font=font(24),fill='#edf4ff')
    line='';y=133
    for word in steps[index][1].split()+['']:
        candidate=(line+' '+word).strip()
        if len(candidate)>25 or not word:d.text((25,y),line,font=font(15),fill='#9dafc9');y+=23;line=word
        else:line=candidate
    for j in range(3):d.rounded_rectangle((25+j*37,263,53+j*37,267),radius=2,fill='#65a3ff' if j<=index else '#2b3c55')
    progress=min(1,local/0.75);ease=1-(1-progress)**3;x=330+int(24*(1-ease))
    panel=Image.new('RGB',(350,270),'#0e1726');pd=ImageDraw.Draw(panel)
    pd.rounded_rectangle((0,0,345,265),radius=18,fill='#19283d',outline='#344a67',width=1)
    pd.text((22,22),steps[index][2],font=font(19),fill='#edf4ff')
    for j,label in enumerate(steps[index][3]):
        yy=65+j*44;selected=index==1 and local>1+j*0.4
        pd.rounded_rectangle((22,yy,321,yy+34),radius=8,fill='#24466b' if selected else '#101e31',outline='#65a3ff' if selected else '#30445f')
        pd.text((34,yy+9),label+('   Selected' if selected else ''),font=font(13),fill='#d6e6fb')
    pd.rounded_rectangle((22,215,321,246),radius=8,fill='#477ff1')
    pd.text((121,223),'Get started' if index==0 else 'Continue' if index==1 else 'Start building',font=font(13),fill='white')
    if progress<1:panel=Image.blend(Image.new('RGB',panel.size,'#0e1726'),panel,ease)
    image.paste(panel,(x,70))
    if frame==FPS*4:image.save(OUT/'onboarding-preview.png')
    writer.send(image.tobytes())
writer.close()
print('Built four project illustrations and a nine-second onboarding video.')
