import React, { useEffect, useState } from "react";
import { Store, Wallet, ShoppingBag, TrendingUp } from "lucide-react";
import { api } from "./server227.mjs";
import { money } from "./model.mjs";
function query(f, extra = {}) {
  return new URLSearchParams(Object.fromEntries(Object.entries({ from: f.start, to: f.end, city: f.city, store: f.store, neighborhood: f.neighborhood, hour_from: f.from, hour_to: f.to, status: f.status, q: f.q, ...extra }).filter(([, v]) => v !== "" && v != null))).toString();
}
function useRead(path, revision, interval = 6e4) {
  const [state, set] = useState({ loading: true, error: "", value: null }), [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    const load = () => {
      if (document.hidden) return;
      api(path).then((value) => {
        if (active) set({ value, error: "", loading: false });
      }).catch((e) => {
        if (active) set((old) => ({ ...old, error: e.message, loading: false }));
      });
    };
    set({ loading: true, error: "", value: null });
    load();
    const timer = setInterval(load, interval);
    document.addEventListener("visibilitychange", load);
    return () => {
      active = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", load);
    };
  }, [path, revision, retry, interval]);
  return { ...state, retry: () => setRetry((n) => n + 1) };
}
function Feedback({ state, Button }) {
  return state.error ? <div className="alert danger" role="alert">{state.error} <Button onClick={state.retry}>Tentar novamente</Button></div> : state.loading ? <p role="status">Carregando dados do filtro…</p> : null;
}
function Pager({ value, page, setPage, Button }) {
  const pages = Math.max(1, Math.ceil((value?.total || 0) / 50));
  return <div className="section-toolbar" aria-label="Paginação"><Button disabled={page === 1} onClick={() => setPage(page - 1)}>Anterior</Button><span aria-live="polite">Página {page} de {pages} · {value?.total || 0} registros</span><Button disabled={page >= pages} onClick={() => setPage(page + 1)}>Próxima</Button></div>;
}
function Executive(p) {
  const { filters: f, data: d, ui: { Panel, Tile, Button } } = p, metrics = useRead("metrics?" + query(f), d._meta.revision), hours = useRead("analytics/hourly?" + query(f), d._meta.revision);
  const m = metrics.value, active = d.stores.filter((s) => !s.demo && s.online), mrr = d.stores.filter((s) => !s.demo && s.subscriptionStatus === "active").reduce((sum, s) => sum + s.price, 0);
  return <><Feedback state={metrics} Button={Button} />{m && <div className="metrics"><Tile label="Vendas concluídas no período" value={money(m.gmv)} icon={Wallet} /><Tile label="Pedidos concluídos" value={m.count} icon={ShoppingBag} /><Tile label="Ticket médio concluído" value={money(m.ticket)} icon={TrendingUp} /><Tile label="Lojas disponíveis agora" value={active.length} icon={Store} /></div>}<div className="two-columns"><Panel title="Mensalidades confirmadas" subtitle="Assinaturas ativas com pagamento registrado. Valores em carteira não são recebimentos."><div className="settings-form"><strong>MRR {money(mrr)}</strong><p>ARR projetado: {money(mrr * 12)}</p><p>Churn e LTV: aguardando histórico de contratos conciliados.</p></div></Panel><Panel title="Vendas por hora" subtitle="Agregação SQL · horário de Brasília"><Feedback state={hours} Button={Button} /><div className="table-scroll"><table><thead><tr><th>Hora</th><th>Concluídos</th><th>Vendas</th></tr></thead><tbody>{hours.value?.items.map((r) => <tr key={r.hour}><td>{String(r.hour).padStart(2, "0")}:00</td><td>{r.count}</td><td>{money(r.gmv)}</td></tr>)}</tbody></table></div>{hours.value && !hours.value.items.length && <p className="ops-empty">Nenhum pedido concluído neste filtro.</p>}</Panel></div></>;
}
function LiveOrders(p) {
  const { data: d, filters: f, ui: { Panel, Button, Badge } } = p;
  const [page, setPage] = useState(1), [revision, setRevision] = useState(0);
  useEffect(() => setPage(1), [JSON.stringify(f)]);
  const state = useRead("orders?" + query(f, { page, limit: 50 }), d._meta.revision + ":" + revision, 15e3);
  async function change(o, status) {
    try {
      await api("change", { revision: d._meta.revision, reason: "Pedido #" + o.id + " alterado pela torre de controle", changes: [{ kind: "orders", id: o.id, value: { status }, before: { status: o.status } }] });
      await p.reload();
      setRevision((n) => n + 1);
    } catch (e) {
      p.setToast(e.message);
    }
  }
  return <Panel title="Pedidos ao vivo e histórico" subtitle="Até 50 pedidos por página. Os totais executivos são calculados no servidor."><Feedback state={state} Button={Button} /><Pager value={state.value} page={page} setPage={setPage} Button={Button} /><div className="table-scroll"><table><thead><tr><th>Pedido</th><th>Loja</th><th>Cliente / bairro da entrega</th><th>Data e hora</th><th>Total</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{state.value?.items.map((o) => <tr key={o.id}><td>#{o.id}</td><td>{o.storeName}</td><td>{o.customerName}<small>{o.neighborhood}</small></td><td>{o.date} {String(o.hour).padStart(2, "0")}:{String(o.minute).padStart(2, "0")}</td><td>{money(o.total)}</td><td><Badge>{o.status}</Badge></td><td><Button variant="secondary" onClick={() => p.setModal({ title: "Pedido #" + o.id, body: <div className="modal-content">{o.items.map((item, i) => <p key={i}>{item.qty}× {item.name} · {money(item.price)}</p>)}<p>Total: {money(o.total)}</p>{!["completed", "cancelled", "rejected"].includes(o.status) && <Button onClick={() => {
    p.setModal(null);
    p.confirm("Cancelar pedido?", "Esta a\xE7\xE3o exige motivo e fica registrada.", () => change(o, "cancelled"));
  }}>Cancelar com auditoria</Button>}</div> })}>Ver pedido</Button></td></tr>)}</tbody></table></div>{state.value && !state.value.items.length && <p className="ops-empty">Nenhum pedido encontrado.</p>}</Panel>;
}
function Customers(p) {
  const { data: d, filters: f, ui: { Panel, Button, Badge } } = p;
  const [page, setPage] = useState(1), [revision, setRevision] = useState(0);
  useEffect(() => setPage(1), [JSON.stringify(f)]);
  const state = useRead("customers?" + query(f, { page, limit: 50 }), d._meta.revision + ":" + revision);
  async function toggle(c) {
    try {
      await api("change", { revision: d._meta.revision, reason: "Situa\xE7\xE3o do cliente #" + c.id + " revisada pelo administrador", changes: [{ kind: "customers", id: c.id, value: { blocked: !!c.is_active }, before: { blocked: !c.is_active } }] });
      await p.reload();
      setRevision((n) => n + 1);
    } catch (e) {
      p.setToast(e.message);
    }
  }
  return <Panel title="Clientes finais" subtitle="Diretório paginado, restrito à permissão de clientes."><Feedback state={state} Button={Button} /><Pager value={state.value} page={page} setPage={setPage} Button={Button} /><div className="table-scroll"><table><thead><tr><th>Nome</th><th>Contato</th><th>Cidade / bairro</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{state.value?.items.map((c) => <tr key={c.id}><td>{c.name}</td><td>{c.email}<small>{c.phone}</small></td><td>{c.city} / {c.neighborhood}</td><td><Badge>{c.is_active ? "Ativo" : "Inativo"}</Badge></td><td><Button onClick={() => p.confirm("Alterar acesso do cliente?", c.name, () => toggle(c))}>{c.is_active ? "Inativar" : "Reativar"}</Button></td></tr>)}</tbody></table></div>{state.value && !state.value.items.length && <p className="ops-empty">Nenhum cliente encontrado.</p>}</Panel>;
}
async function kycRequest(path, options = {}) {
  const r = await fetch(path, { credentials: "same-origin", headers: { "X-Nowup-Admin": "227", ...options.body instanceof FormData ? {} : { "Content-Type": "application/json" } }, ...options });
  const body = await r.json();
  if (!r.ok) throw Error(body.detail || "Falha no KYC");
  return body;
}
function Kyc(p) {
  const { data: d, ui: { Panel, Button } } = p;
  const [store, setStore] = useState(""), [docs, setDocs] = useState([]), [busy, setBusy] = useState(false);
  async function load(id) {
    setStore(id);
    try {
      setDocs(id ? (await kycRequest("/admin/super/api/stores/" + id + "/kyc")).items : []);
    } catch (e) {
      p.setToast(e.message);
    }
  }
  async function review(status) {
    const reason = prompt("Justificativa da revis\xE3o (m\xEDnimo 8 caracteres)");
    if (!reason) return;
    setBusy(true);
    try {
      await kycRequest("/admin/super/api/stores/" + store + "/kyc/review", { method: "POST", body: JSON.stringify({ status, reason }) });
      await load(store);
      await p.reload();
    } catch (e) {
      p.setToast(e.message);
    } finally {
      setBusy(false);
    }
  }
  return <Panel title="Documentos privados e assinatura" subtitle="Validação de dígitos e revisão manual; não substitui verificação externa de identidade."><div className="settings-form"><label className="field"><span>Loja</span><select value={store} onChange={(e) => load(e.target.value)}><option value="">Escolha a loja</option>{d.stores.filter((s) => !s.demo).map((s) => <option key={s.id} value={s.id}>{s.name} · KYC {s.kycStatus} · assinatura {s.subscriptionStatus}</option>)}</select></label>{store && <><form onSubmit={async (e) => {
    e.preventDefault();
    const form = e.currentTarget, body = new FormData(form);
    setBusy(true);
    try {
      await kycRequest("/admin/super/api/stores/" + store + "/kyc", { method: "POST", body });
      form.reset();
      await load(store);
    } catch (e2) {
      p.setToast(e2.message);
    } finally {
      setBusy(false);
    }
  }}><label className="field"><span>Tipo</span><select name="doc_type"><option value="identity">Identidade do responsável</option><option value="business">Documento do negócio</option><option value="address">Endereço</option><option value="facade">Fachada</option><option value="selfie">Selfie</option></select></label><label className="field"><span>Documento privado (PDF, JPG ou PNG · até 5 MB)</span><input name="file" type="file" accept=".pdf,.png,.jpg,.jpeg" required /></label><Button type="submit" loading={busy}>Enviar documento</Button></form>{docs.map((doc) => <p key={doc.id}>{doc.doc_type} · {doc.status} <Button disabled={busy} variant="secondary" onClick={async () => {
    try {
      const result = await kycRequest("/admin/super/api/kyc/" + doc.id + "/url");
      location.assign(result.url);
    } catch (e) {
      p.setToast(e.message);
    }
  }}>Baixar com link de 10 minutos</Button></p>)}<div className="row-actions"><Button disabled={busy||!p.can("finance")} onClick={async()=>{const reason=prompt("Justificativa para criar a assinatura Asaas (mínimo 8 caracteres)");if(!reason)return;setBusy(true);try{await api("billing/"+store+"/provision",{reason});p.setToast("Solicitação registrada para o worker; pagamento ainda não confirmado.")}catch(e){p.setToast(e.message)}finally{setBusy(false)}}}>Preparar cobrança Asaas</Button><Button disabled={busy} onClick={() => review("approved")}>Aprovar KYC</Button><Button disabled={busy} variant="secondary" onClick={() => review("rejected")}>Rejeitar KYC</Button></div></>}</div></Panel>;
}
function Products(p) {
  const { data: d, filters: f, ui: { Panel, Button, Badge } } = p;
  const [page, setPage] = useState(1), [revision, setRevision] = useState(0);
  useEffect(() => setPage(1), [JSON.stringify(f)]);
  const state = useRead("products?" + query(f, { page, limit: 50 }), d._meta.revision + ":" + revision);
  async function toggle(product) {
    try {
      await api("change", { revision: d._meta.revision, reason: "Disponibilidade do produto #" + product.id + " revisada na modera\xE7\xE3o", changes: [{ kind: "products", id: product.id, value: { status: product.available ? "Pausado" : "Aprovado" } }] });
      await p.reload();
      setRevision((n) => n + 1);
    } catch (e) {
      p.setToast(e.message);
    }
  }
  return <Panel title="Produtos e moderação" subtitle="Catálogo atual paginado; filtros de loja, cidade e busca. Datas de venda não limitam o catálogo."><Feedback state={state} Button={Button} /><Pager value={state.value} page={page} setPage={setPage} Button={Button} /><div className="table-scroll"><table><thead><tr><th>Produto</th><th>Loja</th><th>Categoria</th><th>Preço</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{state.value?.items.map((product) => <tr key={product.id}><td>{product.name}</td><td>{product.store_name}</td><td>{product.category}</td><td>{money(product.price_cents)}</td><td><Badge>{product.available ? "Dispon\xEDvel" : "Pausado"}</Badge></td><td><Button onClick={() => p.confirm("Alterar disponibilidade?", product.name, () => toggle(product))}>{product.available ? "Pausar" : "Aprovar"}</Button></td></tr>)}</tbody></table></div>{state.value && !state.value.items.length && <p className="ops-empty">Nenhum produto encontrado.</p>}</Panel>;
}
export {
  Customers,
  Executive,
  Kyc,
  LiveOrders,
  Products
};
