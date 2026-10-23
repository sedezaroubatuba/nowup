let busy=false;
const listeners=new Set();
export const mutationBusy=()=>busy;
export const subscribeMutation=listener=>{listeners.add(listener);return()=>listeners.delete(listener)};
function notify(){for(const listener of listeners)listener()}
export async function exclusiveMutation(action){
 if(busy)throw Error('Aguarde a alteração em andamento.');
 busy=true;notify();
 try{return await action()}finally{busy=false;notify()}
}
