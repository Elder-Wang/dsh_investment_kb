// Browser half of the installed DSH bundle. No separate application or session command.
window.__ModuleLoader__.load({
  id: '@local/dsh-investment-kb',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const slot = 'plugins.bundle.config';
    const ns = 'investmentKb';
    const copy = {
      title: ['投研资料库', 'Research library'], library: ['当前资料库', 'Current library'], none: ['未选择', 'None selected'],
      choose: ['选择并打开／新建资料库', 'Open or create library'], path: ['Host 上的绝对路径', 'Absolute path on the Host'],
      browse: ['浏览…', 'Browse…'], libraryHelp: ['选择已有资料库或独立空目录。原始笔记目录不是资料库。', 'Choose an existing library or an empty directory, not your notes folder.'],
      imports: ['导入本地资料', 'Import local material'], file: ['单文件', 'File'], folder: ['文件夹', 'Folder'],
      preview: ['预览', 'Preview'], import: ['确认导入', 'Confirm import'], cancel: ['取消', 'Cancel'],
      importHelp: ['支持 Markdown、TXT、DOCX 和 HTML。先核对预览，再按确认时的文件内容入库。', 'Preview Markdown, TXT, DOCX or HTML. Confirmation imports the files as they exist at that time.'],
      sources: ['已登记来源', 'Registered sources'], refresh: ['刷新', 'Refresh'], reload: ['重新读取状态', 'Reload status'],
      removeSource: ['移除来源', 'Remove source'], clear: ['清空当前库', 'Clear this library'],
      search: ['检索', 'Search'], query: ['关键词', 'Keywords'], all: ['全部来源', 'All sources'], filter: ['检索范围', 'Search scope'],
      noHits: ['未找到匹配段落。请尝试其他关键词或检查来源覆盖范围。', 'No matching passages. Try other keywords or check source coverage.'],
      open: ['查看归档原文', 'View archived text'], evidence: ['回读对话引用', 'Read a conversation citation'],
      removeDoc: ['删除此资料', 'Delete document'], restore: ['允许下次重新导入', 'Allow reimport on next refresh'],
      permanent: ['此操作涉及以下资料库和目标。清理会删除归档及历史引用，不会修改原文件，也不会撤回聊天记录。', 'Review the exact library and target below. Removal deletes archived versions and invalidates their citations, not original files or chat history.'],
      restoreHelp: ['解除忽略后，下次刷新才能重新导入。旧引用不会复活。', 'Future refreshes may import this item again. Old citations will not be restored.'],
      confirm: ['确认执行', 'Confirm action'], source: ['来源', 'Source'], key: ['来源内标识', 'Document key'], pages: ['查看更多', 'Show more'],
      planet: ['知识星球', 'Knowledge Planet'], group: ['数字星球 ID', 'Numeric group ID'], coverage: ['查看覆盖范围', 'Check coverage'],
      token: ['本次访问凭据', 'Access token for this run'], sync: ['手动同步一页', 'Sync one page'],
      secretHelp: ['仅同步自己有权访问的星球。凭据只用于本次操作，不保存，不进入聊天。', 'Only sync groups you are authorized to access. The token is used once and is not stored or sent to chat.'],
      terminal: ['当前页面不适合传输凭据。请在 Host 的本机终端执行 sync-planet，并在提示时输入 token。', 'Use sync-planet in a local Host terminal and enter the token at its prompt.'],
      busy: ['处理中…', 'Working…'], ready: ['操作已完成', 'Completed'], openLib: ['先选择资料库以启用下方操作。', 'Choose a library to enable the actions below.'],
      selectSource: ['选择来源', 'Select source'], hidden: ['按标识管理资料', 'Manage by document key'], ignoreHelp: ['输入资料标识（文件夹为相对路径，星球为帖子 ID）。也可解除此前删除资料的忽略记录。', 'Use a relative folder path or a topic ID. You can also allow a deleted document to be imported again.'],
      status: ['操作结果', 'Result'], entries: ['条目数', 'Entries'], doc: ['归档版本', 'Archived version'], operation: ['操作', 'Operation'],
      sourceEmpty: ['尚未登记来源。', 'No registered sources yet.'], new: ['新增', 'New'], changed: ['已变更', 'Changed'], unchanged: ['未变', 'Unchanged'], ignored: ['已忽略', 'Ignored'], unsupported: ['不支持', 'Unsupported'], error: ['失败', 'Failed'],
      matched: ['本条引用命中的段落', 'Cited passage'], partial: ['扫描完成，有条目失败；请查看下方原因。', 'Scan finished with errors; see the reasons below.'], skipped: ['扫描完成，有条目未导入。', 'Scan finished with skipped entries.'], fallbackReason: ['未提供原因', 'No reason provided'],
      origin: ['原帖', 'Original post'], rangeNote: ['起止日期只表示已见帖子，不代表期间全部采全。', 'Dates describe observed posts, not guaranteed continuous coverage.'],
    };
    const labels = { zh: {}, en: {} };
    for (const [key, [zh, en]] of Object.entries(copy)) { labels.zh[key] = zh; labels.en[key] = en; }
    const css = `.ikb-panel{display:grid;gap:16px;color:inherit;font:inherit;min-width:0;overflow-wrap:anywhere}.ikb-panel section{display:grid;gap:8px}.ikb-panel h3,.ikb-panel p{margin:0}.ikb-panel h3{font-size:1em}.ikb-panel button,.ikb-panel input,.ikb-panel select{color:inherit;font:inherit;background:transparent;border:1px solid var(--dsw-alias-border-l2);border-radius:6px;padding:4px 9px;min-width:0}.ikb-panel option{color:var(--dsw-alias-label-primary);background:var(--dsw-alias-bg-base)}.ikb-panel button:not(:disabled){cursor:pointer}.ikb-panel button:disabled{opacity:.5}.ikb-panel fieldset{border:0;padding:0;margin:0;display:grid;gap:16px;min-width:0}.ikb-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.ikb-panel label{display:grid;gap:4px;flex:1;min-width:min(12em,100%)}.ikb-panel article{border-inline-start:2px solid currentColor;padding-inline-start:10px;display:grid;gap:4px}.ikb-panel pre{white-space:pre-wrap;margin:0;font:inherit;max-height:20em;overflow:auto}.ikb-panel summary{cursor:pointer}.ikb-panel .ikb-confirm{border:1px solid var(--dsw-alias-border-l2);border-radius:8px;padding:12px}`;
    return { inject: ['slots','locale','connection'], apply(ctx) {
      ctx.effect(() => ctx.locale.register(ns, labels));
      async function call(action, args={}, signal) {
        const r = await ctx.connection.rpc.call('/api', 'investmentKb/manage', { args: { payload: { action, ...args } } }, signal);
        if (!r.ok) throw new Error(r.error.message || r.error.code);
        return r.value;
      }
      function Panel({t}) {
        const [s, set] = React.useState({ library:null,sources:[],libPath:'',path:'',kind:'file',query:'',filter:'',citation:'',group:'',restoreSource:'',restoreKey:'',hits:null,doc:null,preview:null,review:null,result:null,error:'',busy:false,limit:30 });
        const update = values => set(old=>({...old,...values}));
        const reviewRef = React.useRef(null);
        React.useEffect(()=>{ if(s.review) reviewRef.current?.focus(); },[s.review]);
        const lock = React.useRef(false), alive = React.useRef(false), secret = React.useRef(null), controller = React.useRef(null);
        function snapshot(v) { update({ library:v.library || null,sources:v.sources || [],libPath:v.library || '' }); }
        async function run(fn) {
          if (lock.current) return;
          lock.current=true; const abort = new AbortController(); controller.current=abort;
          update({busy:true,error:'',result:null});
          try { await fn((action,args)=>call(action,['pick-path','select','status','confirm'].includes(action)?args:{...args,expectedLibrary:s.library},abort.signal)); }
          catch (e) { if (alive.current && !abort.signal.aborted) update({error:String(e?.message || e)}); }
          finally { if (controller.current === abort) { lock.current=false; if(alive.current) update({busy:false}); } }
        }
        React.useEffect(()=>{
          alive.current=true; void run(async rpc=>snapshot(await rpc('status')));
          return ()=>{alive.current=false;controller.current?.abort();controller.current=null;lock.current=false;};
        },[]);
        const btn=(key, onClick, disabled=false)=>h('button',{type:'button',onClick,disabled:s.busy || disabled},t(key));
        const field=(key,prop,extra={})=>h('label',null,t(key),h('input',{value:s[prop],onChange:e=>update({[prop]:e.target.value,...(['path','kind'].includes(prop)?{preview:null}:{})}),...extra}));
        const row=(...children)=>h('div',{className:'ikb-row'},...children);
        const section=(name,...children)=>h('section',null,h('h3',null,t(name)),...children);
        const opText=status=>Object.hasOwn(copy,status)?t(status):status;
        const summary=data=>h('pre',null,JSON.stringify(data,null,2));
        const doc=cid=>run(async rpc=>{update({doc:null,citation:cid});const version=await rpc('document',{citation:cid});update({doc:{...version,anchor:cid},limit:30});});
        const prepare=(operation,source,key)=>run(async rpc=>update({review:await rpc('prepare',{operation,...(source?{source}:{}),...(key?{key}:{})})}));
        const refresh=source=>run(async rpc=>{update({result:await rpc('refresh-source',{source}),preview:null,hits:null,doc:null});snapshot(await rpc('status'));});
        const pick=(kind,prop)=>run(async rpc=>{const v=await rpc('pick-path',{kind});if(v.path)update({[prop]:v.path,preview:null});});
        const options=(blank,active)=>[h('option',{key:'',value:''},t(blank)),...s.sources.map(x=>h('option',{key:x,value:x},x))];
        const sourceField=(name,prop,blank)=>h('label',null,t(name),h('select',{value:s[prop],onChange:e=>update({[prop]:e.target.value})},options(blank)));
        const resetViews={hits:null,doc:null,preview:null,review:null,filter:'',restoreKey:'',restoreSource:'',citation:''};
        const canSendSecret=window.isSecureContext === true;
        const preview=s.preview;
        const entries=preview?.entries || (preview ? [preview] : []);
        const report=s.result;
        const anchor=s.doc?.passages.find(p=>p.citation===s.doc.anchor);
        const counts=items=>items.reduce((acc,e)=>{acc[e.status]=(acc[e.status]||0)+1;return acc;},Object.create(null));
        const countLine=c=>['new','changed','unchanged','ignored','unsupported','error'].map(k=>`${t(k)}: ${c[k]||0}`).join(' · ');
        const totals=report?.entries?counts(report.entries):null;
        const failures=report?.entries?.filter(e=>e.status==='error'||e.status==='unsupported') || [];
        const operationLabels={'remove-doc':'removeDoc','remove-source':'removeSource','restore-doc':'restore',clear:'clear'};
        return h('div',{className:'ikb-panel','aria-busy':s.busy}, h('style',null,css),
          h('fieldset',{disabled:s.busy || !!s.review},
            section('library',h('p',null,s.library || t('none')),h('p',null,t('libraryHelp')),
              row(field('path','libPath'),btn('browse',()=>pick('folder','libPath')),btn('choose',()=>run(async rpc=>{
                await rpc('select',{path:s.libPath});update({...resetViews,path:'',result:null});snapshot(await rpc('status'));
              }),!s.libPath.trim()),btn('reload',()=>run(async rpc=>{update(resetViews);snapshot(await rpc('status'));})))),
            !s.library ? h('p',null,t('openLib')) : h(React.Fragment,null,
              section('imports',h('p',null,t('importHelp')),
                row(h('select',{'aria-label':t('imports'),value:s.kind,onChange:e=>update({kind:e.target.value,preview:null})},...['file','folder'].map(x=>h('option',{key:x,value:x},t(x)))),field('path','path'),btn('browse',()=>pick(s.kind,'path')),btn('preview',()=>run(async rpc=>update({preview:await rpc('preview-'+s.kind,{path:s.path}),limit:30})),!s.path.trim())),
                preview && h('article',null,h('strong',null,t('preview')+' · '+s.path),h('span',null,t('entries')+': '+entries.length),h('p',null,countLine(counts(entries))),entries.slice(0,s.limit).map((e,i)=>h('div',{key:i},`${opText(e.status)} · ${e.key || s.path}${e.reason?' · '+e.reason:''}`)),entries.length>s.limit && btn('pages',()=>update({limit:s.limit+50})),row(btn('import',()=>run(async rpc=>{const v=await rpc(s.kind==='folder'?'refresh-folder':'import-file',{path:s.path});update({result:v,preview:null,hits:null});snapshot(await rpc('status'));})),btn('cancel',()=>update({preview:null}))))),
              section('sources',s.sources.length===0 && h('p',null,t('sourceEmpty')),s.sources.map(source=>h('article',{key:source},h('span',null,source),row(source.startsWith('zsxq:')?btn('coverage',()=>run(async rpc=>update({group:source.slice(5),result:await rpc('planet-status',{groupId:source.slice(5)})}))):btn('refresh',()=>refresh(source)),btn('removeSource',()=>prepare('remove-source',source))))),btn('clear',()=>prepare('clear'))),
              section('search',row(field('query','query'),sourceField('filter','filter','all'),btn('search',()=>run(async rpc=>update({doc:null,hits:await rpc('search',{query:s.query,limit:30,...(s.filter?{source:s.filter}:{})})})),!s.query.trim())),s.hits?.length===0&&h('p',null,t('noHits')),
                s.hits?.map(hit=>h('article',{key:hit.citation},h('strong',null,hit.key+' · '+hit.locator),h('span',null,hit.source),h('pre',null,hit.text),h('code',null,hit.citation),row(btn('open',()=>doc(hit.citation)),btn('removeDoc',()=>prepare('remove-doc',hit.source,hit.key)))))),
              section('evidence',row(field('evidence','citation',{placeholder:'kb:…'}),btn('open',()=>doc(s.citation.trim()),!s.citation.trim())),s.doc&&h('article',null,h('strong',null,`${s.doc.key} · ${t('doc')} ${s.doc.version}`),h('div',null,s.doc.source),h('div',null,[s.doc.metadata?.author,s.doc.metadata?.published].filter(Boolean).join(' · ')),/^https:\/\/wx\.zsxq\.com\/topic_detail\/\d+$/.test(s.doc.metadata?.url || '')&&h('a',{href:s.doc.metadata.url,target:'_blank',rel:'noreferrer'},t('origin')),anchor&&h('section',{'aria-label':t('matched')},h('strong',null,t('matched')+' · '+anchor.locator),h('code',null,anchor.citation),h('pre',null,anchor.text)),s.doc.passages.slice(0,s.limit).map(p=>h('div',{key:p.citation},h('small',null,p.locator),h('pre',null,p.text))),s.doc.passages.length>s.limit&&btn('pages',()=>update({limit:s.limit+50})),btn('removeDoc',()=>prepare('remove-doc',s.doc.source,s.doc.key)))),
              section('planet',field('group','group',{inputMode:'numeric'}),row(btn('coverage',()=>run(async rpc=>update({result:await rpc('planet-status',{groupId:s.group})})),!/^\d+$/.test(s.group))),h('p',null,t('rangeNote')),
                canSendSecret?h(React.Fragment,null,h('p',null,t('secretHelp')),row(h('label',null,t('token'),h('input',{ref:secret,type:'password',autoComplete:'off',spellCheck:false})),btn('sync',()=>run(async rpc=>{const token=secret.current.value;secret.current.value='';if(!token)throw new Error(t('token'));update({result:await rpc('sync-planet',{groupId:s.group,token,maxPages:1})});snapshot(await rpc('status'));}),!/^\d+$/.test(s.group)))):h('p',null,t('terminal'))),
              h('details',null,h('summary',null,t('hidden')),h('p',null,t('ignoreHelp')),row(sourceField('source','restoreSource','selectSource'),field('key','restoreKey'),btn('removeDoc',()=>prepare('remove-doc',s.restoreSource,s.restoreKey),!s.restoreSource||!s.restoreKey),btn('restore',()=>prepare('restore-doc',s.restoreSource,s.restoreKey),!s.restoreSource||!s.restoreKey)))
            )),
          s.review&&h('section',{className:'ikb-confirm',ref:reviewRef,tabIndex:-1,'aria-label':t('confirm'),role:'group',onKeyDown:e=>{if(e.key==='Escape')update({review:null});}},h('strong',null,t(s.review.operation==='restore-doc'?'restoreHelp':'permanent')),h('p',null,t('library')+': '+s.review.library),h('p',null,[t('operation')+': '+t(operationLabels[s.review.operation]),s.review.source,s.review.key].filter(Boolean).join(' · ')),row(btn('cancel',()=>update({review:null})),btn(operationLabels[s.review.operation],()=>run(async rpc=>{const ticket=s.review.ticket;update({review:null});const value=await rpc('confirm',{ticket});update({...resetViews,result:value});snapshot(await rpc('status'));})))),
          h('div',{role:'status','aria-live':'polite'},s.busy?t('busy'):totals?.error?t('partial'):totals?.unsupported||totals?.ignored?t('skipped'):report?t('ready'):''),s.error&&h('p',{role:'alert'},s.error),
          report&&h('details',{open:true},h('summary',null,t('status')),totals?h(React.Fragment,null,h('p',null,report.source),h('p',null,countLine(totals)),failures.slice(0,s.limit).map(e=>h('p',{key:e.key},`${opText(e.status)} · ${e.key} — ${e.reason || t('fallbackReason')}`)),failures.length>s.limit&&btn('pages',()=>update({limit:s.limit+50}))):summary(report))
        );
      }
      ctx.slots.inject(slot,()=>ctx.slots.register({name:slot,key:'@local/dsh-investment-kb',locale:ns},({view,t})=>view==='page'?h(Panel,{t}):null));
    }};
  },
});
