const {test}=require('node:test'),assert=require('node:assert/strict');
const {selectPairs256}=require('../static/pairs256.js');
const products=[{id:'1',related:'2,3,2,99,4,5,6'}, {id:'2'}, {id:'3',blocked:true}, {id:'4'}, {id:'5'}, {id:'6'}, {id:'7',recommend:true,price:500,regular:1000},{id:'8',recommend:true,price:1000,regular:1000}];
test('merchant highlights first, followed by unique available related products, at most five',()=>assert.deepEqual(selectPairs256(products,new Set(['1'])),['7','8','2','4','5']));
test('excludes products already in cart',()=>assert.deepEqual(selectPairs256(products,new Set(['1','2','4','7'])),['8','5','6']));
test('standalone highlight does not need a promotion or relationship',()=>assert.deepEqual(selectPairs256(products,new Set(['2'])),['7','8']));
test('empty cart has no suggestions',()=>assert.deepEqual(selectPairs256(products,new Set()),[]));
test('more than five highlights are bounded after excluding unavailable and cart items',()=>{const rows=Array.from({length:12},(_,i)=>({id:String(i),recommend:true,blocked:i===1}));assert.deepEqual(selectPairs256(rows,new Set(['0'])),['2','3','4','5','6']);});
