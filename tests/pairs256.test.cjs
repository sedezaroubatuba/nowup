const {test}=require('node:test'),assert=require('node:assert/strict');
const {selectPairs256}=require('../static/pairs256.js');
const products=[{id:'1',related:'2,3,2,99,4,5,6'}, {id:'2'}, {id:'3',blocked:true}, {id:'4'}, {id:'5'}, {id:'6'}, {id:'7',recommend:true,price:500,regular:1000},{id:'8',recommend:true,price:1000,regular:500}];
test('related products first; deduplicates, excludes missing and unavailable and limits to three',()=>assert.deepEqual(selectPairs256(products,new Set(['1'])),['2','4','5']));
test('does not recommend products already in cart',()=>assert.deepEqual(selectPairs256(products,new Set(['1','2','4'])),['5','6','7']));
test('promotions only when a cart has items and actual discount exists',()=>{assert.deepEqual(selectPairs256(products,new Set()),[]);assert.deepEqual(selectPairs256(products,new Set(['2'])),['7']);});
