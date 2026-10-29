import React,{useState,useRef,useEffect} from 'react';
import {Search,X,ArrowRight} from 'lucide-react';
import {searchShortcuts} from './adminSearch.mjs';
import './adminSearch.css';
export default function AdminSearch({can,isSuper,navigate}){
 const [query,setQuery]=useState(''),[open,setOpen]=useState(false);const ref=useRef(null);
 const results=searchShortcuts(query,can,isSuper);
 useEffect(()=>{const close=e=>{if(!ref.current?.contains(e.target))setOpen(false)};document.addEventListener('pointerdown',close);return()=>document.removeEventListener('pointerdown',close)},[]);
 function go(item){setOpen(false);setQuery('');if(item.href)location.assign(item.href);else navigate(item.section)}
 return <div className="admin-search" ref={ref} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setOpen(false)}} onKeyDown={e=>{if(e.key==='Escape'){setOpen(false);ref.current.querySelector('input').focus()}}}>
 <form role="search" onSubmit={e=>{e.preventDefault();if(results[0])go(results[0])}}><Search size={19} aria-hidden="true"/><input aria-label="Buscar funções no painel ADM" placeholder="Buscar no ADM: motinha, banners, lojistas…" value={query} onFocus={()=>setOpen(true)} onChange={e=>{setQuery(e.target.value);setOpen(true)}} aria-expanded={open} aria-controls="admin-search-results" autoComplete="off"/>{query&&<button type="button" aria-label="Limpar busca" onClick={()=>{setQuery('');ref.current.querySelector('input').focus()}}><X size={18}/></button>}</form>
 {open&&<div className="admin-search-results" id="admin-search-results"><p role="status">{query?results.length+' resultado(s)':'Atalhos do painel'}</p>{results.length?<ul>{results.map(item=><li key={item.id}><button type="button" onClick={()=>go(item)}><span><strong>{item.label}</strong><small>{item.path}</small></span><ArrowRight size={17}/></button></li>)}</ul>:<p>Nenhuma função encontrada. Tente outro termo.</p>}</div>}
 </div>
}
