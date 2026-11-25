const p=require('puppeteer-core'); const OUT=process.argv[2]; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{const b=await p.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const pg=await b.newPage(); await pg.setViewport({width:1600,height:1000,deviceScaleFactor:2});
await pg.goto('http://127.0.0.1:8765/pages/slides.html',{waitUntil:'networkidle0'}); await sleep(1500);
const info=await pg.evaluate(()=>[...document.querySelectorAll('.slide')].map((e,i)=>{e.setAttribute('data-s',i);const r=e.getBoundingClientRect();return [i,e.className,Math.round(r.width),Math.round(r.height),(e.querySelector('h1,h2,blockquote')||{}).textContent?.trim().slice(0,60)]}));
console.log(JSON.stringify(info));
for(const [i] of info){const el=await pg.$(`[data-s="${i}"]`); await el.evaluate(e=>e.scrollIntoView()); await sleep(500); await el.screenshot({path:`${OUT}/slide-example-${String(i+1).padStart(2,'0')}.png`});}
await b.close()})();
