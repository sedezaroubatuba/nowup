const {test}=require('node:test'),assert=require('node:assert/strict');
const {removeEdgeWhite274}=require('../static/offer-photos274.js');
test('removes border-connected white and preserves enclosed white product details',()=>{
 const data=new Uint8ClampedArray(7*7*4).fill(255);
 for(let y=2;y<=4;y++)for(let x=2;x<=4;x++){const i=(y*7+x)*4;data[i]=data[i+1]=data[i+2]=20;}
 const middle=(3*7+3)*4;data[middle]=data[middle+1]=data[middle+2]=255;
 assert.deepEqual(removeEdgeWhite274(data,7,7),{left:2,top:2,width:3,height:3});
 assert.equal(data[3],0);assert.equal(data[middle+3],255);
});
test('preserves a dark background and handles an empty image',()=>{
 const dark=new Uint8ClampedArray(16);for(let i=3;i<16;i+=4)dark[i]=255;
 assert.deepEqual(removeEdgeWhite274(dark,2,2),{left:0,top:0,width:2,height:2});
 assert.equal(removeEdgeWhite274(new Uint8ClampedArray(16).fill(255),2,2),null);
});
