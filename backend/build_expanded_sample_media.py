"""Build project-specific sample demo videos. Development tools: Pillow, imageio-ffmpeg."""
from pathlib import Path
import math
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
OUT=Path(__file__).resolve().parent.parent/'frontend/public/demo-posts'
OUT.mkdir(parents=True,exist_ok=True)
FONT=Path('C:/Windows/Fonts/arial.ttf')
if not FONT.exists():FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def font(size):return ImageFont.truetype(str(FONT),size) if FONT.exists() else ImageFont.load_default(size=size)
SPECS=[('solar','SolarScope','Solar generation monitor','#ffce66','OUTPUT','18.4 kW',['Today / 64.2 kWh','Panel strings / 4 online','Feed age / 3 seconds']),('greenhouse','Greenhouse Watch','Seedling sensor dashboard','#76d8ac','SOIL MOISTURE','42%',['Temperature / 23 C','Humidity / 68%','Sensor pods / 6 online']),('circuit','CircuitBench','Board diagnostic console','#81b8ff','TEST RUN','12 / 12',['Power rail / PASS','Clock signal / PASS','Serial loopback / PASS'])]
for slug,title,subtitle,accent,metric,value,checks in SPECS:
    writer=imageio_ffmpeg.write_frames(str(OUT/f'{slug}-demo.mp4'),(720,408),fps=24,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=7,macro_block_size=2,output_params=['-movflags','+faststart'])
    writer.send(None)
    for frame in range(24*8):
        t=frame/24;progress=min(1,t/5.5)
        image=Image.new('RGB',(720,408),'#0e1726');d=ImageDraw.Draw(image)
        d.text((25,17),'KEYSTONE / SAMPLE PROJECT DEMO',font=font(11),fill='#7f96b6')
        d.text((25,47),title,font=font(28),fill='#edf4ff');d.text((25,84),subtitle,font=font(14),fill='#a5b7d0')
        d.rounded_rectangle((25,119,453,350),radius=16,fill='#17263b',outline='#2e435f')
        d.rounded_rectangle((472,119,695,350),radius=16,fill='#17263b',outline='#2e435f')
        d.text((45,138),'SIGNAL / LAST 60 SECONDS' if slug=='circuit' else 'LIVE READINGS',font=font(11),fill='#91a5c2')
        for y in [190,230,270,310]:d.line((45,y,431,y),fill='#2b3a50',width=1)
        pts=[]
        for i in range(int(100*progress)+1):
            x=45+i*3.85
            y=(264-(35 if (i//9)%2 else -15)) if slug=='circuit' else (285-i*.75-24*math.sin(i*.10)) if slug=='solar' else (274-i*.55-12*math.sin(i*.15))
            pts.append((x,y))
        if len(pts)>1:d.line(pts,fill=accent,width=3)
        if pts:
            x,y=pts[-1];d.ellipse((x-4,y-4,x+4,y+4),fill=accent)
        d.text((492,140),metric,font=font(11),fill='#96acc9')
        display=value if progress>=1 else f'{int(progress*12)} / 12' if slug=='circuit' else f'{int(30+progress*12)}%' if slug=='greenhouse' else f'{progress*18.4:.1f} kW'
        d.text((492,168),display,font=font(28),fill=accent)
        for j,check in enumerate(checks):
            color='#c4d2e5' if t>(j+1)*1.2 else '#61728d'
            d.text((492,226+j*30),check,font=font(12),fill=color)
        d.text((25,376),'ILLUSTRATIVE PROTOTYPE / SIMULATED READINGS',font=font(10),fill='#6f85a1')
        if frame==24*6:image.save(OUT/f'{slug}-dashboard.png')
        writer.send(image.tobytes())
    writer.close()
print('Built three eight-second project videos and dashboard stills.')
