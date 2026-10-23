import test from 'node:test';
import assert from 'node:assert/strict';
import {filterRows,hourMatch,saasStatus,ruleStep} from '../src/operations.mjs';
test('overnight shift excludes 02:00 and assigns dawn to previous day',()=>{
 const f={start:'2026-10-22',end:'2026-10-22',from:'18',to:'2'};
 const rows=[{id:1,date:'2026-10-22',hour:18,minute:0},{id:2,date:'2026-10-23',hour:1,minute:59},{id:3,date:'2026-10-23',hour:2,minute:0},{id:4,date:'2026-10-23',hour:2,minute:59},{id:5,date:'2026-10-22',hour:1,minute:0}];
 assert.deepEqual(filterRows(rows,f).map(x=>x.id),[1,2]);
 assert.equal(hourMatch(17,'18','2',59),false);
});

test('billing status follows confirmed provider state instead of a future due date',()=>{
 const store={demo:false,due:'2026-11-30',price:7900,subscriptionStatus:'pending'};
 assert.equal(saasStatus(store),'Aguardando pagamento');
 assert.equal(saasStatus({...store,subscriptionStatus:'blocked'}),'Bloqueada');
 assert.equal(saasStatus({...store,subscriptionStatus:'active'}),'Ativa');
 assert.equal(ruleStep({...store,due:'2026-10-19',subscriptionStatus:'past_due'},'2026-10-23'),'D+4 · bloqueio automático');
});
