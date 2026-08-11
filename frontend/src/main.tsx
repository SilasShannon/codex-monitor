import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Boxes, CircleDollarSign, Database, FolderGit2, Gauge, Search, Settings, Wrench } from 'lucide-react'
import './styles.css'

type Overview = {active_sessions:number;sessions:number;total_tokens:number;cache_rate:number|null;tool_calls:number;mcp_calls:number}
type Cost = {today:string;['7_days']:string;['30_days']:string;all_time:string;cache_savings:string;unavailable_sessions:number}
type Session = {session_id:string;project_name?:string;model?:string;last_activity?:string;total_tokens?:number}

const nav = [
  ['Overview', Gauge], ['Live', Activity], ['Projects', FolderGit2], ['Sessions', Database],
  ['Tokens', Boxes], ['Cost', CircleDollarSign], ['Models', Boxes], ['Tools', Wrench],
  ['MCP', Boxes], ['Git', FolderGit2], ['Search', Search], ['Settings', Settings],
] as const

const compact = (value?: number) => value == null ? 'Unavailable' : Intl.NumberFormat('en', {notation:'compact', maximumFractionDigits:1}).format(value)
const usd = (value?: string) => value == null ? 'Unavailable' : Number(value).toLocaleString('en-US', {style:'currency', currency:'USD', minimumFractionDigits:2, maximumFractionDigits:2})
const api = async <T,>(path:string):Promise<T> => { const response=await fetch(path); if(!response.ok) throw new Error(`${response.status}`); return response.json() }

function App(){
  const [data,setData]=React.useState<{overview:Overview;cost:Cost;sessions:Session[]}|null>(null)
  const [error,setError]=React.useState('')
  React.useEffect(()=>{Promise.all([api<Overview>('/api/overview'),api<Cost>('/api/cost/summary'),api<Session[]>('/api/sessions?limit=8')])
    .then(([overview,cost,sessions])=>setData({overview,cost,sessions})).catch(()=>setError('The local analytics API is unavailable.'))},[])
  return <div className="shell">
    <aside><div className="brand"><span className="brandmark">C</span><div>Codex Monitor<small>Local observability</small></div></div>
      <nav>{nav.map(([label,Icon],i)=><button className={i===0?'active':''} key={label}><Icon size={17}/><span>{label}</span>{i>0&&<em>Soon</em>}</button>)}</nav>
      <div className="local"><span></span><div>Local only<small>127.0.0.1</small></div></div>
    </aside>
    <main><header><div><p className="eyebrow">Workspace analytics</p><h1>Overview</h1></div><div className="range">Last 30 days⌄</div></header>
      {error&&<div className="notice">{error}</div>}
      {!data?<div className="skeleton-grid">{Array.from({length:7}).map((_,i)=><div className="skeleton" key={i}/>)}</div>:<>
        <section className="hero-grid">
          <Metric label="Active sessions" value={String(data.overview.active_sessions)} tone="green" hint={`${data.overview.sessions} indexed`}/>
          <Metric label="Tokens today" value={compact(data.overview.total_tokens)} hint="Processed input + output"/>
          <Metric label="API equivalent today" value={usd(data.cost.today)} tone="violet" hint="Estimate · not a charge"/>
          <Metric label="7-day estimate" value={usd(data.cost['7_days'])} hint="API-equivalent value"/>
          <Metric label="30-day estimate" value={usd(data.cost['30_days'])} hint="Verified pricing only"/>
          <Metric label="Cache rate" value={data.overview.cache_rate==null?'Unavailable':`${Math.round(data.overview.cache_rate*100)}%`} tone="cyan" hint="Cached / inclusive input"/>
          <Metric label="Cache savings" value={usd(data.cost.cache_savings)} tone="green" hint="Estimated counterfactual"/>
        </section>
        <section className="split">
          <div className="panel"><div className="panelhead"><div><p className="eyebrow">Recent activity</p><h2>Sessions</h2></div><span>{data.cost.unavailable_sessions} unpriced</span></div>
            <div className="table"><div className="tr th"><span>Project</span><span>Model</span><span>Tokens</span><span>Last activity</span></div>
              {data.sessions.map(s=><div className="tr" key={s.session_id}><span><b>{s.project_name||'Unassigned'}</b><small>{s.session_id.slice(0,12)}</small></span><span className="pill">{s.model||'Unknown'}</span><span>{compact(s.total_tokens)}</span><span>{s.last_activity?new Date(s.last_activity).toLocaleString():'Unknown'}</span></div>)}
            </div></div>
          <div className="panel posture"><p className="eyebrow">Data posture</p><h2>Evidence, not guesses</h2><div className="ring"><div><b>{data.overview.sessions-data.cost.unavailable_sessions}</b><span>priced sessions</span></div></div>
            <ul><li><i className="ok"/>Exact token snapshots</li><li><i className="ok"/>Official model pricing</li><li><i/>Historical prices pending</li></ul>
            <p className="footnote">Every monetary value is an estimated API-equivalent cost. Subscription charges are not available.</p></div>
        </section>
      </>}
    </main>
  </div>
}

function Metric({label,value,hint,tone=''}:{label:string;value:string;hint:string;tone?:string}){
  return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
