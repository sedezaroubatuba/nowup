export function storeFields(form,previous){
 const out={};for(const key of ['name','owner','phone','document','city','neighborhood','address'])out[key]=String(form[key]??'');
 out.radius=Number(form.radius);out.prep=Number(form.prep);
 const hours=Array.from({length:7},(_,i)=>String(form['day'+i]??'').trim());
 if(!previous||JSON.stringify(hours)!==JSON.stringify(previous.hoursByDay))out.hoursByDay=hours;
 return out;
}
export function contractFields(form,plans){
 const plan=plans.find(p=>p.id===form.plan);if(!plan)throw Error('Escolha um plano válido.');
 return {plan:plan.id,price:plan.price,due:form.due,trialUntil:form.trialUntil||'',method:form.method};
}
