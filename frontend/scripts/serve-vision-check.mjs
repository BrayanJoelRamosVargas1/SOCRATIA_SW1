// Static, click-driven checks: actual MediaPipe models, synthetic images only.
// No physical camera, continuous render loop, Next build or cloud requests.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const fixtures=path.join(process.env.TEMP??'.','socratia-gaze-validation');
const output=path.join(root,'../artifacts/defense-validation/real-vision.json');
const allowed=new Set(['front','eyes_left','eyes_right','eyes_down','head_side','bare']);
const signals=ts.transpileModule(await fs.readFile(path.join(root,'src/features/simulations/practice-signals.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022}}).outputText;
const html=await fs.readFile(path.join(root,'scripts/vision-check.html'));
const server=http.createServer(async(req,res)=>{
  try {
    const url=new URL(req.url,'http://127.0.0.1');
    if(req.method==='POST'&&url.pathname==='/results'){
      let body='';for await(const part of req){body+=part;if(body.length>12000)throw Error('Too large');}
      const value=JSON.parse(body);
      if(value.source!=='synthetic-fixtures'||!Array.isArray(value.cases)||value.cases.length>12)throw Error('Invalid');
      await fs.mkdir(path.dirname(output),{recursive:true});await fs.writeFile(output,JSON.stringify(value,null,2));
      res.end('saved');return;
    }
    let content,type='application/octet-stream';
    if(url.pathname==='/'){content=html;type='text/html; charset=utf-8';}
    else if(url.pathname==='/worker-check'){content=await fs.readFile(path.join(root,'scripts/camera-worker-check.html'));type='text/html; charset=utf-8';}
    else if(url.pathname==='/signals.js'){content=signals;type='text/javascript';}
    else if(url.pathname==='/vision.mjs'){content=await fs.readFile(path.join(root,'node_modules/@mediapipe/tasks-vision/vision_bundle.mjs'));type='text/javascript';}
    else if(url.pathname.startsWith('/vision/')){
      const target=path.resolve(root,'public',url.pathname.slice(1));
      if(!target.startsWith(path.join(root,'public/vision')+path.sep))throw Error('Invalid path');
      content=await fs.readFile(target);type=target.endsWith('.wasm')?'application/wasm':target.endsWith('.js')?'text/javascript':type;
    }else if(/^\/fixtures\/[a-z_]+\.png$/.test(url.pathname)){
      const name=path.basename(url.pathname,'.png');if(!allowed.has(name))throw Error('Invalid fixture');
      content=await fs.readFile(path.join(fixtures,name+'.png'));type='image/png';
    }else throw Error('Not found');
    res.setHeader('Content-Type',type);res.setHeader('Cache-Control','no-store');res.end(content);
  }catch{res.statusCode=404;res.end('Not found');}
});
server.listen(8766,'127.0.0.1',()=>console.log('Click-driven real vision checks: http://127.0.0.1:8766'));
