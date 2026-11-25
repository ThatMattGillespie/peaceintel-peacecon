const p=require('puppeteer-core'); const OUT=process.argv[2];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{const b=await p.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const pg=await b.newPage(); await pg.setViewport({width:1440,height:900,deviceScaleFactor:2});
for(const f of ['home','landing']){
 await pg.goto('http://127.0.0.1:8765/pages/'+f+'.html',{waitUntil:'networkidle0'});
 // walk the page so every reveal fires, then return to the top
 const H=await pg.evaluate(()=>document.body.scrollHeight);
 for(let y=0;y<H;y+=400){await pg.evaluate(y=>scrollTo(0,y),y);await sleep(180)}
 await sleep(2500); await pg.evaluate(()=>scrollTo(0,0)); await sleep(800);
 const n=await pg.evaluate(()=>{const els=[...document.querySelectorAll('body > header, body > section, body > footer, main > header, main > section, main > footer, body > main > *')].filter(e=>e.getBoundingClientRect().height>200&&/band/.test(e.className));
  els.forEach((e,i)=>e.setAttribute('data-shot',i)); return els.length});
 for(let i=0;i<n;i++){
  const el=await pg.$(`[data-shot="${i}"]`);
  await el.evaluate(e=>e.scrollIntoView()); await sleep(1600);
  // the floating top bar belongs to the hero only
  await pg.evaluate(i=>{const nav=document.querySelector('header.fnav, .fnav');if(nav)nav.style.visibility=i==0?'':'hidden'},i);
  const name=`${f}-${String(i+1).padStart(2,'0')}.png`;
  await el.screenshot({path:OUT+'/'+name}); console.log(name);
 }
 await pg.evaluate(()=>{const nav=document.querySelector('header.fnav, .fnav');if(nav)nav.style.visibility=''});
 await pg.setViewport({width:1440,height:900,deviceScaleFactor:1});
 await pg.evaluate(()=>scrollTo(0,0)); await sleep(500);
 await pg.screenshot({path:OUT+'/'+f+'-full-page.jpg',fullPage:true,type:'jpeg',quality:82});
 await pg.setViewport({width:1440,height:900,deviceScaleFactor:2});
}
await b.close()})();
