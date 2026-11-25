// Library operations with no DSH dependency, so the same logic is testable
// outside a running Host.
import { isAbsolute } from 'node:path';
import { realpath, stat } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { choosePath } from './picker.mjs';
import { runCore } from './bridge.mjs';

export const cleanOps = ['remove-doc', 'remove-source', 'clear', 'restore-doc'];
const text = (s, max = 8192) => {
  if (typeof s !== 'string' || !s.trim() || s.includes('\0') || s.length > max) throw Error('无效或过长的文本参数');
  return s;
};
const path = s => { if (!isAbsolute(text(s))) throw Error('请选择绝对路径'); return s; };
const number = (n, max) => { if (!Number.isInteger(n) || n < 1 || n > max) throw Error('数字超出范围'); return n; };
const group = s => { if (!/^\d{1,32}$/.test(text(s, 32))) throw Error('请输入数字星球 ID'); return s; };
function exact(a, fields) {
  if (!a || typeof a !== 'object' || Array.isArray(a) || Object.keys(a).some(k => !['action', ...fields].includes(k))) throw Error('未知参数');
}

// A single instance is owned by one mounted plugin entry. Only manage() can change authority.
export function createLibraryService({ library, save, python = 'python3', core = runCore, now = Date.now }) {
  let selected = library || null;
  const tickets = new Map();
  function run(argv, signal, extra = {}) {
    if (!selected) throw Error('请先在投研资料库管理页选择知识库目录');
    return core(selected, argv, { python, signal, ...extra });
  }
  async function read(a, signal) {
    switch (a?.action) {
    case 'status': exact(a, []); return { library: selected, sources: selected ? await run(['sources'], signal) : [] };
    case 'search': {
      exact(a, ['query', 'source', 'limit']);
      const argv = ['search', '--limit', String(number(a.limit ?? 12, 100))];
      if (a.source != null) argv.push('--source=' + text(a.source));
      return run([...argv, '--', text(a.query, 512)], signal);
    }
    case 'read': case 'document': exact(a, ['citation']); return run([a.action, '--', text(a.citation, 256)], signal);
    case 'planet-status': exact(a, ['groupId']); return run([a.action, group(a.groupId)], signal);
    default: throw Error('不是只读查询');
    }
  }
  async function manage(a, signal) {
    if (a && Object.hasOwn(a, 'expectedLibrary')) {
      const { expectedLibrary, ...rest } = a;
      if (expectedLibrary !== selected) throw Error('资料库已切换，请刷新后再操作');
      a = rest;
    }
    switch (a?.action) {
    case 'pick-path': {
      exact(a, ['kind']); if (!['file', 'folder'].includes(a.kind)) throw Error('无效选择器');
      return { path: await choosePath(a.kind, signal) };
    }
    case 'refresh-source': {
      exact(a, ['source']); const src = path(a.source), rootAtStart = selected;
      if (!(await run(['sources'], signal)).includes(src)) throw Error('来源尚未登记');
      const info = await stat(src);
      if (selected !== rootAtStart) throw Error('资料库已切换，请刷新后再操作');
      return run([info.isDirectory() ? 'refresh-folder' : 'import-file', '--', src], signal);
    }
    case 'select': {
      exact(a, ['path']); const chosen = path(a.path);
      await core(chosen, ['init'], { python, signal });
      const canonical = await realpath(chosen);
      await save(canonical); selected = canonical; tickets.clear();
      return { library: canonical, sources: await run(['sources'], signal) };
    }
    case 'preview-file': case 'import-file': case 'preview-folder': case 'refresh-folder':
      exact(a, ['path']); return run([a.action, '--', path(a.path)], signal);
    case 'sync-planet': {
      exact(a, ['groupId', 'token', 'maxPages']);
      return run(['sync-planet', group(a.groupId), '--max-pages', String(number(a.maxPages ?? 1, 20))], signal, { token: text(a.token, 4096) });
    }
    case 'prepare': {
      const op = a.operation;
      if (!selected || !cleanOps.includes(op)) throw Error('无效清理目标');
      const hasKey = op === 'remove-doc' || op === 'restore-doc';
      exact(a, ['operation', ...(op === 'clear' ? [] : ['source']), ...(hasKey ? ['key'] : [])]);
      const target = { library: selected, operation: op };
      const argv = [op, '--confirm', '--'];
      if (op !== 'clear') argv.push(target.source = text(a.source));
      if (hasKey) argv.push(target.key = text(a.key));
      if (op === 'clear') argv.pop();
      for (const [k, v] of tickets) if (v.until <= now()) tickets.delete(k);
      if (tickets.size >= 128) tickets.delete(tickets.keys().next().value);
      const ticket = randomUUID(); tickets.set(ticket, { argv, library: selected, until: now() + 120000 });
      return { ...target, ticket };
    }
    case 'confirm': {
      exact(a, ['ticket']); const key = text(a.ticket, 64), issue = tickets.get(key); tickets.delete(key);
      if (!issue || issue.library !== selected || issue.until <= now()) throw Error('确认已失效，请重新核对目标');
      return run(issue.argv, signal);
    }
    default: return read(a, signal);
    }
  }
  return { read, manage };
}
