/* Fail CI when reviewed screens change, so tutorial review is part of the change. */
const fs=require('node:fs'),crypto=require('node:crypto'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const reviewed=[
 'templates/pro_panel.html','templates/tutorials395.html','templates/ingredients320.html',
 'templates/meals322.html','templates/combos301.html','templates/weight370.html',
 'templates/fashion385.html','templates/merchant_product_card.html','templates/promotions285.html',
 'templates/order_revision.html','templates/order_public348.html',
 'static/pro198.js','static/storefront187.js','static/fashion-layout391.js',
 'static/tutorials-data395.js','static/tutorials395.js','static/tutorials395.css',
 'nowup_ingredients320.py','nowup_storeapp257.py','nowup_review127.py'
];
const snapshot=Object.fromEntries(reviewed.map(file=>[file,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')]));
const baseline=path.join(root,'tests/tutorials395-reviewed.json');
if(process.argv.includes('--reviewed')){fs.writeFileSync(baseline,JSON.stringify(snapshot,null,2)+'\n');console.log('Tutorial review baseline updated.');}
else{const old=JSON.parse(fs.readFileSync(baseline,'utf8'));const changed=reviewed.filter(file=>old[file]!==snapshot[file]);if(changed.length){console.error('Review tutorials for these changed screens before publishing:\n'+changed.join('\n')+'\nAfter reviewing content, targets and previews, run node tools/check_tutorials395.cjs --reviewed');process.exitCode=1;}else console.log('Tutorials match the reviewed screens.');}
