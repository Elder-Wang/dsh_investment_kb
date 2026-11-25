import test from 'node:test';
import assert from 'node:assert/strict';
import {choosePath} from './picker.mjs';

test('native picker uses a constant script and preserves the selected path', async () => {
  for (const kind of ['file','folder']) {
    const got = await choosePath(kind, undefined, {platform:'darwin',execute:async (bin,args) => {
      assert.equal(bin,'/usr/bin/osascript'); assert.equal(args[0],'-e');
      assert.match(args[1],new RegExp('choose '+kind)); return {stdout:'/资料/有 空格\n'};
    }});
    assert.equal(got,'/资料/有 空格');
  }
});
test('cancel does not select a path; unsupported operations fail without invoking a dialog',async()=>{
  assert.equal(await choosePath('file',undefined,{platform:'darwin',execute:async()=>{throw {stderr:'User canceled. (-128)'};}}),null);
  await assert.rejects(choosePath('echo foo'),/文件或文件夹/);
  await assert.rejects(choosePath('file',undefined,{platform:'win32'}),/手动/);
});
