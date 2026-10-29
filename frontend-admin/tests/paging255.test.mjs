import test from 'node:test';
import assert from 'node:assert/strict';
import {hydrateOrders255} from '../src/server227.mjs';
const state=()=>({orders:[{id:5,total:100}],_meta:{revision:2,orderPagination255:{nextBefore:5}}});
test('hydrates all pages before exposing totals',async()=>{
 const calls=[];const result=await hydrateOrders255(state(),async path=>{calls.push(path);return calls.length===1?{revision:2,orders:[{id:4,total:200}],nextBefore:4}:{revision:2,orders:[{id:3,total:300}],nextBefore:null};});
 assert.equal(result.orders.reduce((n,o)=>n+o.total,0),600);assert.equal(calls.length,2);assert.equal(result._meta.orderPagination255.complete,true);
});
test('fails on revision change instead of mixing totals',async()=>{await assert.rejects(()=>hydrateOrders255(state(),async()=>({revision:3,orders:[],nextBefore:null})),/mudou/);});
test('fails on repeated cursor',async()=>{await assert.rejects(()=>hydrateOrders255(state(),async()=>({revision:2,orders:[{id:4}],nextBefore:5})),/Continuação/);});
