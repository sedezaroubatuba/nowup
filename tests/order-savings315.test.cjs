const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const context={window:{}};vm.createContext(context);
for(const p of ['static/combo-prices303.js','static/order-savings315.js'])vm.runInContext(fs.readFileSync(p,'utf8'),context);
const calculate=context.window.NOWUP_SAVINGS315.calculate;
const card=(id,price,regular,combo={})=>({dataset:{id:String(id),price:String(price),regular256:String(regular),...combo}});
const root=cards=>({querySelectorAll:()=>cards});
const line=(id,price,quantity=1,options=[],groups={})=>({productId:id,unitPrice:price,quantity,options,customization:{groups}});
const combo={combo256:'1',custom192:JSON.stringify({combo_items:[{product_id:2,quantity:2}],groups:[]}),comboPrices303:JSON.stringify({'2':1000})};
test('promotions and quantities add up; paid extras do not count',()=>assert.equal(calculate([line(1,900,3,[{price:100}])],root([card(1,800,1000)])),600));
test('combo promotion is counted once against the larger reference',()=>assert.equal(calculate([line(1,1400,2)],root([card(1,1400,1800,combo)])),1200));
test('mix of combo, promotion and full-price products',()=>assert.equal(calculate([line(1,1500),line(2,800,2),line(3,900)],root([card(1,1500,1500,combo),card(2,800,1000),card(3,900,900)])),900));
test('missing, stale and non-discounted products have no saving',()=>assert.equal(calculate([line(1,700),line(2,1000),line(3,1000)],root([card(1,800,1000),card(2,1000,1000)])),0));
test('selected combo options use their actual price',()=>{
 const config={combo_items:[{quantity:2,group_id301:'g'}],groups:[{id:'g',product_ids:[2,3],options:['A','B']}]};
 const c=card(1,1400,1400,{combo256:'1',custom192:JSON.stringify(config),comboPrices303:JSON.stringify({'2':800,'3':1200})});
 assert.equal(calculate([line(1,1400,1,[],{g:['A','B']})],root([c])),600);
 assert.equal(calculate([line(1,1400)],root([c])),0);
});
