const {test}=require('node:test'),assert=require('node:assert/strict');
const {catalogGroups275}=require('../static/storefront187.js');
const card=(id,category,price,regular,combo='0',available='1')=>({dataset:{id,category,price:String(price),regular256:String(regular),combo256:combo,available256:available}});
test('combos only belong to built-in combos; promotions also stay in regular category',()=>{
 const beer=card('1','cervejas',400,500),combo=card('2','cervejas',2000,2000,'1'),builtin=card('3','combos',1000,1500),off=card('4','gelo',0,100);
 const groups=catalogGroups275([beer,combo,builtin,off]);
 assert.deepEqual(groups.regular.map(c=>c.dataset.id),['1','4']);assert.deepEqual(groups.combos.map(c=>c.dataset.id),['2','3']);assert.deepEqual(groups.promotions.map(c=>c.dataset.id),['1','3']);
});
test('unavailable and undiscounted products do not enter promotional showcase',()=>{
 const groups=catalogGroups275([card('1','cervejas',500,500),card('2','cervejas',400,500,'0','0')]);assert.equal(groups.promotions.length,0);assert.equal(groups.regular.length,2);
});
