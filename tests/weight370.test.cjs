const test=require('node:test'),assert=require('node:assert/strict');
const {weightTotal370}=require('../static/weight370.js');
test('kilograms plus grams have one fixed total rounded once',()=>{
 assert.deepEqual(weightTotal370(7500,1,200),{grams:1200,cents:9000});
 assert.deepEqual(weightTotal370(6599,1,200),{grams:1200,cents:7919});
 assert.deepEqual(weightTotal370(7500,0,200),{grams:200,cents:1500});
});
test('all predefined weights match exact integer half-up arithmetic',()=>{
 for(const rate of [1,5,6599,7500,10000000])for(let kg=0;kg<=99;kg++)for(let g=0;g<=900;g+=100){if(!kg&&!g)continue;const grams=kg*1000+g;assert.equal(weightTotal370(rate,kg,g).cents,Number((BigInt(rate)*BigInt(grams)+500n)/1000n));}
});
test('zero, fractional and forged selections are rejected',()=>{
 for(const [kg,g] of [[0,0],[-1,100],[1,150],[100,0],[1,1000],[1,100.1],[true,200],['1',200]])assert.throws(()=>weightTotal370(7500,kg,g));
});
