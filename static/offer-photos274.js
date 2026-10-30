/* Only highlighted cards get a local transparent cutout; uploaded originals remain intact. */
function removeEdgeWhite274(data,width,height){
 const count=width*height,seen=new Uint8Array(count),queue=new Int32Array(count);let tail=0,head=0;
 const white=i=>{const p=i*4;return data[p+3]<12||(Math.min(data[p],data[p+1],data[p+2])>=240&&Math.max(data[p],data[p+1],data[p+2])-Math.min(data[p],data[p+1],data[p+2])<18);};
 const push=i=>{if(!seen[i]&&white(i)){seen[i]=1;queue[tail++]=i;}};
 for(let x=0;x<width;x++){push(x);push((height-1)*width+x);}for(let y=0;y<height;y++){push(y*width);push(y*width+width-1);}
 while(head<tail){const i=queue[head++],x=i%width;data[i*4+3]=0;if(x>0)push(i-1);if(x<width-1)push(i+1);if(i>=width)push(i-width);if(i<count-width)push(i+width);}
 let left=width,top=height,right=-1,bottom=-1;
 for(let i=0;i<count;i++)if(data[i*4+3]>12){const x=i%width,y=Math.floor(i/width);left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}
 return right<left?null:{left,top,width:right-left+1,height:bottom-top+1};
}
if(typeof module!=='undefined')module.exports={removeEdgeWhite274};
if(typeof document!=='undefined')(()=>{
 const cache=new Map();
 function process(img){
  if(!img.matches('.nu256-highlight>img')||!img.complete||!img.naturalWidth)return;
  const src=img.currentSrc||img.src;if(!src||src.startsWith('data:')||src.includes('product-placeholder.svg')||img.dataset.cutout274===src)return;
  img.dataset.cutout274=src;
  if(cache.has(src)){const result=cache.get(src);if(result)img.src=result;return;}
  try{
   const scale=Math.min(1,640/Math.max(img.naturalWidth,img.naturalHeight)),w=Math.max(1,Math.round(img.naturalWidth*scale)),h=Math.max(1,Math.round(img.naturalHeight*scale));
   const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,w,h);const pixels=ctx.getImageData(0,0,w,h);
   const corner=[0,(w-1)*4,(h-1)*w*4,(w*h-1)*4];
   if(corner.filter(p=>Math.min(...pixels.data.slice(p,p+3))>=240||pixels.data[p+3]<12).length<3){cache.set(src,null);return;}
   const bounds=removeEdgeWhite274(pixels.data,w,h);if(!bounds){cache.set(src,null);return;}ctx.putImageData(pixels,0,0);
   const output=document.createElement('canvas');output.width=output.height=480;const out=output.getContext('2d'),ratio=440/Math.max(bounds.width,bounds.height),dw=bounds.width*ratio,dh=bounds.height*ratio;out.drawImage(canvas,bounds.left,bounds.top,bounds.width,bounds.height,(480-dw)/2,(480-dh)/2,dw,dh);
   const result=output.toDataURL('image/png');if(cache.size>=60)cache.delete(cache.keys().next().value);cache.set(src,result);img.src=result;
  }catch(_){cache.set(src,null); /* Non-readable images keep their original source. */}
 }
 document.addEventListener('load',e=>{if(e.target.tagName==='IMG')process(e.target);},true);
 const scan=()=>document.querySelectorAll('.nu256-highlight>img').forEach(process);
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scan);else scan();
})();
