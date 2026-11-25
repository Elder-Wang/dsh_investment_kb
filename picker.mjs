import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { isAbsolute } from 'node:path';

const run = promisify(execFile);
const scripts = Object.freeze({
  file: 'POSIX path of (choose file with prompt "选择要导入的研究资料")',
  folder: 'POSIX path of (choose folder with prompt "选择文件夹")',
});

// The script is constant. No filesystem path or other browser input is interpolated.
export async function choosePath(kind, signal, {platform = process.platform, execute = run} = {}) {
  if (!Object.hasOwn(scripts, kind)) throw new Error('请选择文件或文件夹');
  if (platform !== 'darwin') throw new Error('此平台请手动输入绝对路径');
  try {
    const {stdout} = await execute('/usr/bin/osascript', ['-e', scripts[kind]], {signal, timeout: 120000, maxBuffer: 32768});
    const path = stdout.replace(/\r?\n$/, '');
    if (!isAbsolute(path)) throw new Error('未得到本机绝对路径');
    return path;
  } catch (e) {
    if (/\(-128\)/.test(e.stderr || '')) return null; // userCancelledErr
    throw new Error('未能完成系统选择，可手动输入绝对路径');
  }
}
