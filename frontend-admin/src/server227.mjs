import {exclusiveMutation} from './mutation.mjs';
export const EMPTY={version:1,operationsVersion:2,profile:{name:'Carregando',email:'',phone:'',cpf:'',photo:''},plans:[],stores:[],orders:[],customers:[],products:[],categories:[],banners:[],settings:{autoBlock:false,deliveryPerKm:0,minOrder:0,cities:[],activeCities:[],platformHours:'',globalMessage:'',homeTitle:'',homeText:''},sessions:[],logs:[],staff:[],errors:[],integrations:{},reports:[],productCategories:[],payments:[],billingCoupons:[],couriers:[],deliveryRules:[],coupons:[],campaigns:[],referrals:[],themes:[],tickets:[],_meta:{revision:0,actor:{super:false,permissions:[]},unsupported:[],live:true}};
async function request(path,body){const c=new AbortController(),timeout=setTimeout(()=>c.abort(),30000);try{const response=await fetch('/admin/super/api/'+path,{credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Nowup-Admin':'227',...(body?{'X-Nowup-Activity':'1'}:{})},body:body?JSON.stringify(body):undefined,signal:c.signal});let result;try{result=await response.json()}catch{throw Error('Resposta inválida do servidor. Nenhuma alteração foi confirmada.')}if(!response.ok){if(response.status===401)location.assign('/admin/super/equipe/entrar');throw Error(result.detail||'Não foi possível salvar.')}return result}finally{clearTimeout(timeout)}}
function equal(a,b){return JSON.stringify(a)===JSON.stringify(b)}
export function changes(previous,next){const list=[];for(const key of Object.keys(EMPTY)){
 if(key==='logs'||key==='errors'||key.startsWith('_')||equal(previous[key],next[key]))continue;
 if(['version','operationsVersion','integrations','reports'].includes(key))throw Error('Este dado é gerenciado pelo servidor.');
 if(['settings','profile'].includes(key)){const value={},before={};for(const k of Object.keys(next[key]))if(!equal(previous[key]?.[k],next[key][k])){value[k]=next[key][k];before[k]=previous[key]?.[k]}list.push({kind:key,value,before});continue}
 if(['categories','productCategories'].includes(key)){list.push({kind:key,value:{items:next[key]}});continue}
 if(!Array.isArray(next[key]))throw Error('Alteração não suportada.');
 for(const row of next[key]){const old=previous[key].find(r=>r.id===row.id);if(!old){const {id,...value}=row;list.push({kind:key,create:true,value});continue}const value={},before={};for(const k of Object.keys(row))if(k!=='id'&&!equal(old[k],row[k])){value[k]=row[k];before[k]=old[k]}if(Object.keys(value).length)list.push({kind:key,id:row.id,value,before})}
 if(previous[key].some(r=>!next[key].some(n=>n.id===r.id)))throw Error('Exclusão não disponível neste painel. Use pausar ou desativar.');
 }return list}

export function api(path,body){return path==='change'?exclusiveMutation(()=>request(path,body)):request(path,body)}
