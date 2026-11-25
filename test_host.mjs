import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { apply, createLibraryService } from './index.js';

test('owner selects a fresh library; real CLI evidence and cleanup are fenced',async(t)=>{
 const root = await mkdtemp(join(tmpdir(),'dsh-host-test-'));
 const owned = await realpath(root), parent = await realpath(tmpdir());
 t.after(async()=>{assert.ok(owned.startsWith(join(parent,'dsh-host-test-')) && await realpath(root) === owned); await rm(owned,{recursive:true});});
 const library = join(root,'资料库'), note = join(root,'笔记 a.md');
 let saved, clock = 100;
 const svc = createLibraryService({save: async p=>{saved=p}, now:()=>clock});
 assert.deepEqual(await svc.read({action:'status'}),{library:null,sources:[]});
 await assert.rejects(svc.read({action:'select',path:library}));
 await svc.manage({action:'select',path:library});
 assert.equal(saved,await realpath(library));
 await writeFile(note,'# 测试\n\n光模块 本周需求');
 for (const action of ['preview-file','import-file']) assert.equal((await svc.manage({action,path:note})).status,'new');
 const [hit] = await svc.read({action:'search',query:'光模块'});
 await assert.rejects(svc.manage({action:'refresh-source',source:hit.source,expectedLibrary:'/old'}));
 assert.equal((await svc.manage({action:'refresh-source',source:hit.source,expectedLibrary:saved})).status,'unchanged');
 await assert.rejects(svc.manage({action:'refresh-source',source:join(root,'unknown')}));
 await assert.rejects(svc.read({action:'pick-path',kind:'folder'}));
 assert.equal((await svc.read({action:'read',citation:hit.citation})).text,hit.text);
 assert.equal((await svc.read({action:'document',citation:hit.citation})).passages.length,2);
 assert.equal((await svc.read({action:'planet-status',groupId:'123'})).status,'not_synced');
 await assert.rejects(svc.read({action:'search',query:'x',library:'/tmp/bogus'}));
 const prepare=()=>svc.manage({action:'prepare',operation:'remove-doc',source:hit.source,key:hit.key});
 let grant=await prepare(); clock+=120000;
 await assert.rejects(svc.manage({action:'confirm',ticket:grant.ticket}));
 grant=await prepare(); await assert.rejects(svc.read({action:'confirm',ticket:grant.ticket}));
 assert.equal((await svc.read({action:'read',citation:hit.citation})).text,hit.text);
 await svc.manage({action:'confirm',ticket:grant.ticket});
 await assert.rejects(svc.manage({action:'confirm',ticket:grant.ticket}));
 await assert.rejects(svc.read({action:'read',citation:hit.citation}));
 assert.equal((await svc.manage({action:'import-file',path:note})).status,'ignored');
 const confirmation=await svc.manage({action:'prepare',operation:'clear'});
 await svc.manage({action:'confirm',ticket:confirmation.ticket});
 assert.deepEqual((await svc.read({action:'status'})).sources,[]);
});

test('browser peer restriction and agent registration',async()=>{
 let handle,tool; const ctx={effect:fn=>fn(), connection:{browserPeer:{id:'browser'},rpc:{intercept:(channel,match,cb)=>{
   assert.equal(channel,'/api');assert.equal(match('investment-kb.manage'),true); handle=cb;return ()=>{};
 }}},tools:{register:d=>{tool=d;return ()=>{}}}};
 apply(ctx,{}); const s=new AbortController().signal;
 assert.equal((await handle('',{action:'status'},s,{id:'api',principal:{kind:'owner'}})).ok,false);
 assert.equal((await handle('',{action:'status'},s,{id:'browser',principal:{kind:'owner'}})).ok,true);
 assert.equal(tool.name,'investment_kb_query');
 assert.deepEqual(await tool.execute({action:'status'},{signal:s}),{result:{library:null,sources:[]}});
 await assert.rejects(tool.execute({action:'clear'},{signal:s}));
});
