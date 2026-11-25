"""Offline release check: pack the actual bundle, then use it outside the checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
RUNTIME = {'index.js', 'client.js', 'kb_service.mjs', 'bridge.mjs', 'picker.mjs', 'kb_cli.py',
           'kb_store.py', 'kb_formats.py', 'kb_folders.py', 'kb_planet.py', 'icon.svg',
           'locale/en.json', 'locale/zh.json', 'cordis.patch.yml', 'package.json', 'README.md'}


@unittest.skipUnless(shutil.which('npm') and shutil.which('node'), 'distribution check requires npm and node')
class DistributionTest(unittest.TestCase):
    def test_pack_and_exercise_outside_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            tmp = Path(temp)
            env = dict(os.environ, HOME=temp, npm_config_cache=str(tmp/'cache'), npm_config_offline='true')
            report = subprocess.run(['npm', 'pack', '--json', '--ignore-scripts', '--pack-destination', temp],
                                    cwd=ROOT, env=env, check=True, text=True, capture_output=True)
            packed = json.loads(report.stdout)
            pkg = packed[0] if isinstance(packed, list) else packed['@local/dsh-investment-kb']
            self.assertEqual({f['path'] for f in pkg['files']}, RUNTIME)
            release = tmp/'release'
            with tarfile.open(tmp/pkg['filename']) as archive:
                for item in archive.getmembers():
                    self.assertTrue(item.isfile())
                    self.assertIn(item.name, {'package/' + f for f in RUNTIME})
                    dest = release/item.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(archive.extractfile(item).read())
            bundle = release/'package'
            manifest = json.loads((bundle/'package.json').read_text())
            self.assertTrue((bundle/manifest['dsh']['bundle']['patch']).is_file())
            self.assertEqual(ET.parse(bundle/'icon.svg').getroot().tag, '{http://www.w3.org/2000/svg}svg')
            for language in ('en','zh'):
                self.assertTrue(json.loads((bundle/'locale'/f'{language}.json').read_text())['meta']['title'])
            # New database, brand new HOME/cache, no reference to a development
            # interpreter environment. System Python, Node and DSH are not reinstalled.
            note = tmp/'研究.md'
            note.write_text('光模块记录', encoding='utf-8')
            js = """import {runCore} from './bridge.mjs';
import assert from 'node:assert/strict';
import {createLibraryService} from './kb_service.mjs';
const [lib,note,python]=process.argv.slice(1);
const run=(...args)=>runCore(lib,args,{python});
await run('init');await run('import-file',note);
const svc=createLibraryService({library:lib,python}); const [hit]=await svc.read({action:'search',query:'光模块'});
assert.equal((await svc.read({action:'read',citation:hit.citation})).text,'光模块记录');"""
            subprocess.run([shutil.which('node'),'--input-type=module','-e',js,str(tmp/'new library'),str(note),sys.executable],
                           cwd=bundle, env={'PATH':os.defpath,'HOME':temp}, check=True, timeout=20)
            for jsfile in ('client.js', 'index.js'):
                subprocess.run([shutil.which('node'),'--check',str(bundle/jsfile)],check=True)


if __name__ == '__main__':
    unittest.main()
