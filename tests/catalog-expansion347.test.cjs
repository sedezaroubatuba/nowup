const {test}=require('node:test'),assert=require('node:assert/strict');
const {catalogExpansion347}=require('../static/storefront187.js');
test('desktop expands and collapses without duplicating products or losing card state',()=>{
 const grid={children:[],append(card){card.remove();card.parent=this;this.children.push(card)}};
 function node(){return {hidden:false,attrs:{},parent:null,setAttribute(k,v){this.attrs[k]=v},remove(){if(this.parent){this.parent.children=this.parent.children.filter(x=>x!==this);this.parent=null}},focus(){this.focused=true}}}
 const more=node(),collapseButton=node(),section={scrollIntoView(){this.scrolled=true}};let loaded=0,refreshed=0;
 function load(limit){while(loaded<limit){const card=node();card.id=++loaded;grid.append(card)}}
 load(7);const first=grid.children[0];first.selectedQuantity=3;grid.append(more);
 const controls=catalogExpansion347({grid,more,collapseButton,load,count:12,limit:7,refresh:()=>refreshed++,section});
 controls.expand();assert.equal(grid.children.length,12);assert.equal(collapseButton.hidden,false);assert.equal(collapseButton.attrs['aria-expanded'],'true');assert.equal(more.parent,null);
 controls.collapse();assert.equal(grid.children.filter(x=>x!==more&&!x.hidden).length,7);assert.equal(more.parent,grid);assert(more.focused&&section.scrolled);assert(collapseButton.hidden);
 controls.expand();assert.equal(grid.children.length,12);assert.equal(grid.children.filter(x=>!x.hidden).length,12);assert.equal(grid.children[0],first);assert.equal(first.selectedQuantity,3);assert.equal(loaded,12);assert.equal(refreshed,2);
});
