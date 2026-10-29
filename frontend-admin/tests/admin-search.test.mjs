import test from 'node:test';
import assert from 'node:assert/strict';
import {searchShortcuts} from '../src/adminSearch.mjs';
test('finds opening by common names and strips accents',()=>{for(const q of ['motinha','BUZINA','animacao','abertura'])assert.equal(searchShortcuts(q,()=>true,true)[0].href,'/admin/super/abertura');assert.equal(searchShortcuts('logistica',()=>true,true)[0].section,'logistics')});
test('respects staff permissions and hides super admin opening',()=>{const items=searchShortcuts('',s=>s==='support',false);assert.deepEqual(items.map(x=>x.section),['support']);assert.equal(searchShortcuts('buzina',()=>true,false).length,0)});
test('matches all query words and handles no results',()=>{assert.equal(searchShortcuts('banners inicial',()=>true,true)[0].id,'banners');assert.equal(searchShortcuts('inexistente',()=>true,true).length,0)});
