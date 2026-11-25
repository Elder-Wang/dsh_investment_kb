import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import test from 'node:test';

// Validate the loader/registration contract only. This is not a browser render test.
test('Client factory registers one locale-aware bundle settings seat without starting RPC', async () => {
  let module;
  vm.runInNewContext(await readFile(new URL('./client.js', import.meta.url), 'utf8'), {
    window: { __ModuleLoader__: { load(value) { assert.equal(module, undefined); module = value; } } },
  });
  assert.equal(module.id, '@local/dsh-investment-kb');
  const plugin = module.factory(name => { assert.equal(name, 'react'); return {}; });
  assert.deepEqual(Array.from(plugin.inject), ['slots', 'locale', 'connection']);
  const dictionaries = [], seats = [], disposers = [];
  plugin.apply({
    locale: { register(ns, labels) { dictionaries.push({ns,labels}); return () => dictionaries.pop(); } },
    effect(fn) { disposers.push(fn()); },
    slots: { inject(name, fn) { assert.equal(name, 'plugins.bundle.config'); disposers.push(fn()); },
      register(spec, component) { seats.push({spec,component}); return () => seats.pop(); } },
    connection: {rpc:{call(){ assert.fail('registration must not trigger RPC'); }}},
  });
  assert.equal(seats.length, 1); assert.equal(seats[0].spec.name, 'plugins.bundle.config');
  assert.equal(seats[0].spec.key, module.id); assert.equal(seats[0].spec.locale, dictionaries[0].ns);
  assert.deepEqual(Object.keys(dictionaries[0].labels.zh).sort(), Object.keys(dictionaries[0].labels.en).sort());
  assert.equal(seats[0].component({view:'summary'}), null);
  for (const dispose of disposers.reverse()) dispose();
  assert.equal(seats.length,0); assert.equal(dictionaries.length,0);
});
