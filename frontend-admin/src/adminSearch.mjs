const normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
export const shortcuts=[
 {id:'opening',label:'Abertura da motinha',path:'Configurações → Tela de abertura',href:'/admin/super/abertura',superOnly:true,terms:'motinha moto buzina som animação splash início'},
 {id:'banners',label:'Banners da página inicial',path:'Configurações → Banners',section:'settings',terms:'banner propaganda imagem promoção'},
 {id:'dashboard',label:'Visão executiva',path:'Executivo',section:'dashboard',terms:'relatórios vendas indicadores faturamento'},
 {id:'stores',label:'Lojistas e KYC',path:'Lojistas',section:'stores',terms:'lojas cadastro aprovação documentos kanban'},
 {id:'finance',label:'Financeiro SaaS',path:'Financeiro',section:'finance',terms:'mensalidade planos pagamentos cobrança'},
 {id:'orders',label:'Pedidos ao vivo',path:'Pedidos',section:'orders',terms:'compras entrega pedidos'},
 {id:'customers',label:'Clientes finais',path:'Clientes',section:'customers',terms:'compradores usuários'},
 {id:'products',label:'Produtos e moderação',path:'Produtos',section:'products',terms:'catálogo categorias itens'},
 {id:'marketing',label:'Marketing',path:'Marketing',section:'marketing',terms:'campanhas cupons divulgação'},
 {id:'logistics',label:'Logística',path:'Logística',section:'logistics',terms:'frete entregadores taxas regiões'},
 {id:'support',label:'Suporte e denúncias',path:'Suporte',section:'support',terms:'atendimento chamados reclamações'},
 {id:'themes',label:'CMS e temas',path:'CMS e temas',section:'themes',terms:'temas sazonais natal carnaval conteúdo'},
 {id:'settings',label:'Configurações',path:'Configurações gerais',section:'settings',terms:'ajustes portal horário texto home'},
 {id:'staff',label:'Equipe e acessos',path:'Equipe',section:'staff',terms:'funcionários permissões convite'},
 {id:'system',label:'Sistema e integrações',path:'Sistema',section:'system',terms:'backup conexões'},
 {id:'logs',label:'Histórico de ações',path:'Sistema → Auditoria',section:'logs',terms:'auditoria alterações registros'},
 {id:'demos',label:'Perfis fictícios',path:'Perfis fictícios',section:'demos',terms:'demonstração teste lojas exemplo'}
];
export function searchShortcuts(query,can,isSuper){const words=normalize(query).split(/\s+/).filter(Boolean);return shortcuts.filter(item=>(item.superOnly?isSuper:can(item.section))&&words.every(word=>normalize(item.label+' '+item.path+' '+item.terms).includes(word)));}
