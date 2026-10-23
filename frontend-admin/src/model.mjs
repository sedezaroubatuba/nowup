export const VERSION=1;
export const money=v=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format((Number(v)||0)/100);
export const day=(d=new Date())=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
export function shift(date,n){const d=new Date(date+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
export function daysBetween(a,b){return Math.round((new Date(b+'T12:00:00Z')-new Date(a+'T12:00:00Z'))/86400000);}
export const today=()=>day();
export const MODULES=[['dashboard','Faturamento'],['stores','Aprovar lojistas'],['finance','Financeiro'],['banners','Banners'],['marketing','Marketing'],['reports','Denúncias'],['themes','Temas'],['staff','Funcionários']];
export function billingStatus(s,now=today()){
 if(s.demo)return 'Fictício';if(s.cancelledAt)return 'Cancelado';
 if(s.trialUntil&&s.trialUntil>=now)return 'Teste Grátis';
 if(!s.due)return 'Sem vencimento';
 const delay=daysBetween(s.due,now);return delay>=3?'Inadimplente':delay>0?'Atrasado':'Em dia';
}
export function effectiveBlocked(s,settings,now=today()){
 return !s.demo&&!!settings.autoBlock&&billingStatus(s,now)==='Inadimplente';
}
export function activeTheme(themes,now=new Date()){
 return themes.filter(t=>t.enabled&&t.start&&t.end&&new Date(t.start)<=now&&new Date(t.end)>now).sort((a,b)=>(b.priority||0)-(a.priority||0)||b.id-a.id)[0]||null;
}
export function safeUrl(raw){try{const u=new URL(raw,location.origin);return ['https:','http:'].includes(u.protocol)?u.href:'';}catch{return '';}}
export function isDueSoon(s,now=today()){return !s.demo&&!s.cancelledAt&&s.due>=now&&daysBetween(now,s.due)<=7;}
export function financial(stores,now=today()){
 const real=stores.filter(s=>!s.demo);const subscribed=real.filter(s=>!s.cancelledAt&&!s.trialUntil&&s.approval==='approved');
 const month=now.slice(0,7);const cancelled=real.filter(s=>s.cancelledAt?.startsWith(month)&&s.subscribedAt<month+'-01');
 const initial=real.filter(s=>s.subscribedAt<month+'-01'&&(!s.cancelledAt||s.cancelledAt>=month+'-01'));
 return {mrr:subscribed.reduce((a,s)=>a+s.price,0),churn:initial.length?cancelled.length/initial.length*100:0,due:real.filter(s=>isDueSoon(s,now)).length,overdue:real.filter(s=>['Inadimplente','Atrasado'].includes(billingStatus(s,now))).length,initial:initial.length,cancelled:cancelled.length};
}
export function sales(orders,stores,filter){
 const byId=new Map(stores.filter(s=>!s.demo&&(!filter.city||s.city===filter.city)).map(s=>[s.id,s]));
 const selected=orders.filter(o=>byId.has(o.store)&&o.date>=filter.start&&o.date<=filter.end);
 const done=selected.filter(o=>o.status==='completed');const revenue=done.reduce((a,o)=>a+o.total,0);
 const hours=Array.from({length:24},(_,hour)=>({hour,count:0,total:0}));const ranking=new Map(),products=new Map();
 for(const o of done){hours[o.hour].total+=o.total;hours[o.hour].count++;const r=ranking.get(o.store)||{id:o.store,name:byId.get(o.store).name,total:0,count:0};r.total+=o.total;r.count++;ranking.set(o.store,r);for(const i of o.items){const key=o.store+':'+i.name,p=products.get(key)||{name:i.name,store:byId.get(o.store).name,qty:0,total:0};p.qty+=i.qty;p.total+=i.qty*i.price;products.set(key,p);}}
 return {selected,done,revenue,ticket:done.length?Math.round(revenue/done.length):0,average:Math.round(revenue/(daysBetween(filter.start,filter.end)+1)),cancelled:selected.filter(o=>o.status==='cancelled').length,hours,ranking:[...ranking.values()].sort((a,b)=>b.total-a.total),products:[...products.values()].sort((a,b)=>b.qty-a.qty)};
}
export function idleStores(stores,orders,days,city='',now=today()){
 const since=shift(now,-days+1);
 return stores.filter(s=>!s.demo&&!s.cancelledAt&&s.approval==='approved'&&(!city||s.city===city)&&!orders.some(o=>o.store===s.id&&o.status==='completed'&&o.date>=since&&o.date<=now));
}
export function seed(){const now=today();const plans=[{id:'start',name:'Start',price:7900,features:'Presença no marketplace e cardápio'},{id:'pro',name:'Pro',price:14900,features:'Cardápio, pedidos e relatórios'},{id:'premium',name:'Premium',price:24900,features:'Recursos Pro e destaque comercial'}];
 const names=['Adega Sede Zero','Hamburgueria da Praia','Padaria Bom Dia','Mercado Costa Verde','Farmácia Central','Pet Shop Amigo','Cantina Caiçara','Açaí da Vila','Pizzaria Bella'];
 const cities=['Ubatuba','Ubatuba','Ubatuba','Caraguatatuba','Ubatuba','São Sebastião','Ubatuba','Caraguatatuba','Ubatuba'];
 const stores=names.map((name,i)=>({id:i+1,name,city:cities[i],neighborhood:['Estufa II','Itaguá','Centro'][i%3],category:['Adegas','Restaurantes','Padarias','Mercados','Farmácias','Pet shops','Restaurantes','Restaurantes','Restaurantes'][i],approval:i===5?'pending':i===8?'rejected':'approved',online:i%3!==0,paused:false,plan:plans[i%3].id,price:plans[i%3].price,due:shift(now,[5,-1,12,-5,2,7,8,15,10][i]),trialUntil:i===6?shift(now,8):'',cancelledAt:i===7?shift(now,-3):'',subscribedAt:shift(now,-60),phone:'',email:'',document:'',address:'Endereço de demonstração',radius:5,hours:'Segunda a domingo, 09h às 23h',method:i%2?'Pix':'Cartão',paymentUrl:'',featured:i<2,demo:false,menu:[{name:'Produto de exemplo',price:2500}]}));
 for(let i=0;i<3;i++)stores.push({id:100+i,name:['Hamburgueria Exemplo','Padaria Exemplo','Pet Shop Exemplo'][i],city:'Ubatuba',neighborhood:'Centro',category:['Restaurantes','Padarias','Pet shops'][i],approval:'approved',online:false,paused:false,plan:'start',price:0,due:'',trialUntil:'',cancelledAt:'',subscribedAt:now,phone:'',email:'',document:'',address:'',radius:3,hours:'',method:'Pix',paymentUrl:'',featured:false,demo:true,menu:[]});
 const orders=[];let id=1;for(let days=0;days<45;days++)for(let s=1;s<=7;s++){if(s===6||s===4||s===7&&days<15)continue;for(let j=0;j<(s%3)+1;j++){const qty=1+(days+j+s)%3,price=[1500,2500,3200][j%3];orders.push({id:id++,store:s,date:shift(now,-days),hour:[11,12,13,18,19,20,21][(s+j+days)%7],status:(days+s+j)%13===0?'cancelled':'completed',total:qty*price+500,delivery:500,coupon:(days+j)%5===0?'BEMVINDO10':'',items:[{name:['Combo da casa','Produto mais pedido','Especial do dia'][j%3],qty,price}]});}}
 return {version:VERSION,profile:{name:'Samuel',email:'',phone:'',cpf:'',photo:''},plans,stores,orders,payments:[{id:1,store:1,date:shift(now,-25),amount:7900,method:'Pix',reference:'Registro ilustrativo'}],settings:{autoBlock:false,deliveryPerKm:200,minOrder:2000},categories:['Restaurantes','Padarias','Mercados','Farmácias','Pet shops','Adegas'],banners:[],coupons:[{id:1,code:'BEMVINDO10',type:'percent',value:10,scope:'global',store:'',minimum:2000,limit:100,start:shift(now,-20),end:shift(now,20),enabled:true}],campaigns:[],themes:[{id:1,name:'Natal',primary:'#166534',accent:'#dc2626',logo:'',icons:'Estrelas',banner:'',start:now.slice(0,4)+'-12-01T00:00:00-03:00',end:now.slice(0,4)+'-12-26T00:00:00-03:00',enabled:true,priority:1}],staff:[{id:1,name:'Equipe de demonstração',email:'equipe@example.com',role:'Operação',enabled:true,permissions:['stores','reports']}],reports:[{id:1,store:2,reason:'Informações do horário divergentes',status:'Aberta',date:shift(now,-1),note:''}],logs:[{id:1,date:new Date().toISOString(),actor:'Super ADM',action:'Prévia iniciada com dados ilustrativos'}]};
}
