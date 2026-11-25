// Run only the bundled Python entry point; callers construct argv from validated actions.
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { isAbsolute } from 'node:path';

const cli = fileURLToPath(new URL('./kb_cli.py', import.meta.url));
const maxOutput = 16 * 1024 * 1024;

export async function runCore(library, argv, { python = 'python3', token, signal } = {}) {
  if (typeof library !== 'string' || !isAbsolute(library)) throw new Error('请选择绝对路径的本地资料库');
  if (!Array.isArray(argv) || !argv.length || !argv.every(v => typeof v === 'string' && !v.includes('\0'))) throw new Error('无效操作参数');
  const env = {};
  for (const k of ['PATH', 'HOME', 'TMPDIR', 'LANG', 'SystemRoot']) if (process.env[k]) env[k] = process.env[k];
  if (argv[0] === 'sync-planet' && token) env.ZSXQ_ACCESS_TOKEN = token;
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-E', '-s', '-B', cli, '--library', library, ...argv], {
      shell: false, env, stdio: ['ignore', 'pipe', 'pipe'], signal,
    });
    const stdout = [], stderr = [];
    let size = 0, stopped;
    const stop = reason => { stopped = reason; child.kill('SIGKILL'); };
    const timer = setTimeout(() => stop('操作超时，请查看状态后重试'), argv[0] === 'sync-planet' ? 300000 : 120000);
    function capture(chunks, b) {
      size += b.length;
      if (size <= maxOutput) chunks.push(b);
      else if (!stopped) stop('结果超过大小限制，请缩小范围');
    }
    child.stdout.on('data', b => capture(stdout, b));
    child.stderr.on('data', b => capture(stderr, b));
    child.on('error', e => {
      clearTimeout(timer);
      reject(new Error(e.code === 'ENOENT' ? '找不到 Python 3，请安装 Python 并配置解释器路径' : '无法启动或操作已取消'));
    });
    child.once('close', code => {
      clearTimeout(timer);
      if (stopped) return reject(new Error(stopped));
      if (code !== 0) {
        let detail;
        try { detail = JSON.parse(Buffer.concat(stderr).toString('utf8')).error; } catch { /* Never echo arbitrary process output. */ }
        return reject(new Error(typeof detail === 'string' ? detail : '知识库操作失败'));
      }
      try { resolve(JSON.parse(Buffer.concat(stdout).toString('utf8'))); }
      catch { reject(new Error('知识库返回了无效结果')); }
    });
  });
}
