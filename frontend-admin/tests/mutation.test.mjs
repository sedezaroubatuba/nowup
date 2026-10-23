import test from 'node:test';
import assert from 'node:assert/strict';
import {exclusiveMutation,mutationBusy,subscribeMutation} from '../src/mutation.mjs';
test('blocks double saves and releases buttons after success or failure',async()=>{
 const states=[],unsubscribe=subscribeMutation(()=>states.push(mutationBusy()));
 let finish;const first=exclusiveMutation(()=>new Promise(resolve=>finish=resolve));
 assert.equal(mutationBusy(),true);
 await assert.rejects(exclusiveMutation(()=>assert.fail('duplicate ran')),/Aguarde/);
 finish('saved');assert.equal(await first,'saved');assert.equal(mutationBusy(),false);
 await assert.rejects(exclusiveMutation(async()=>{throw Error('offline')}),/offline/);
 assert.equal(mutationBusy(),false);assert.deepEqual(states,[true,false,true,false]);unsubscribe();
});
