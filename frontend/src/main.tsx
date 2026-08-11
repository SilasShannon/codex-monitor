import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Boxes, CircleDollarSign, Database, FolderGit2, Gauge, Search, Settings, Wrench } from 'lucide-react'
import './styles.css'

type Page = 'Overview'|'Tokens'|'Cost'
type Overview = {active_sessions:number;sessions:number;total_tokens:number;input_tokens:number;cached_input_tokens:number;cache_write_input_tokens:number;output_tokens:number;cache_rate:number|null}
type Cost = {today:string;['7_days']:string;['30_days']:string;all_time:string;cache_savings:string;unavailable_sessions:number}
type Session = {session_id:string;project_name?:string;model?:string;last_activity?:string;total_tokens?:number}
type Point = {date:string;input_tokens:number;cached_input_tokens:number;output_tokens:number;total_tokens:number;estimated_api_equivalent_cost:string;unpriced_sessions:number}
type Breakdown = {name:string;sessions:number;input_tokens:number;cached_input_tokens:number;output_tokens:number;total_tokens:number;estimated_api_equivalent_cost:string;unpriced_sessions:number}
type Data = {overview:Overview;cost:Cost;sessions:Session[];series:Point[];projects:Breakdown[];models:Breakdown[];costProjects:Breakdown[];costModels:Breakdown[];costSessions:Breakdown[]}
const Charts = React.lazy(()=>import('./charts'))

const nav = [
  ['Overview', Gauge], ['Live', Activity], ['Projects', FolderGit2], ['Sessions', Database],
  ['Tokens', Boxes], ['Cost', CircleDollarSign], ['Models', Boxes], ['Tools', Wrench],
  ['MCP', Boxes], ['Git', FolderGit2], ['Search', Search], ['Settings', Settings],
] as const
const ready = new Set(['Overview','Tokens','Cost'])
const compact = (value?:number) => value==null?'Unavailable':Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(value)
const usd = (value?:string|number) => value==null?'Unavailable':Number(value).toLocaleString('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2})
const api = async <T,>(path:string):Promise<T> => {const response=await fetch(path);if(!response.ok)throw Error(`${response.status}`);return response.json()}

function App(){
  const [page,setPage]=React.useState<Page>('Overview'); const [data,setData]=React.useState<Data|null>(null); const [error,setError]=React.useState('')
  React.useEffect(()=>{Promise.all([
    api<Overview>('/api/overview'),api<Cost>('/api/cost/summary'),api<Session[]>('/api/sessions?limit=8'),
    api<Point[]>('/api/analytics/timeseries?days=30'),api<Breakdown[]>('/api/analytics/breakdown?dimension=project'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=model'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=project&sort=cost'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=model&sort=cost'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=session&sort=cost'),
  ]).then(([overview,cost,sessions,series,projects,models,costProjects,costModels,costSessions])=>setData({overview,cost,sessions,series,projects,models,costProjects,costModels,costSessions})).catch(()=>setError('The local analytics API is unavailable.'))},[])
  return <div className="shell"><aside><div className="brand"><span className="brandmark">C</span><div>Codex Monitor<small>Local observability</small></div></div>
    <nav>{nav.map(([label,Icon])=><button className={page===label?'active':''} key={label} onClick={()=>ready.has(label)&&setPage(label as Page)}><Icon size={17}/><span>{label}</span>{!ready.has(label)&&<em>Soon</em>}</button>)}</nav>
    <div className="local"><span/><div>Local only<small>127.0.0.1</small></div></div></aside>
    <main><header><div><p className="eyebrow">Workspace analytics</p><h1>{page}</h1></div><div className="range">Last 30 days</div></header>
      {error&&<div className="notice">{error}</div>}{!data?<Loading/>:page==='Overview'?<OverviewPage data={data}/>:page==='Tokens'?<TokensPage data={data}/>:<CostPage data={data}/>}</main></div>
}

function OverviewPage({data}:{data:Data}){return <><section className="hero-grid">
  <Metric label="Active sessions" value={String(data.overview.active_sessions)} tone="green" hint={`${data.overview.sessions} indexed`}/>
  <Metric label="Tokens today" value={compact(data.series.at(-1)?.total_tokens)} hint="Inclusive input + output"/>
  <Metric label="API equivalent today" value={usd(data.cost.today)} tone="violet" hint="Estimate · not a charge"/>
  <Metric label="7-day estimate" value={usd(data.cost['7_days'])} hint="API-equivalent value"/>
  <Metric label="30-day estimate" value={usd(data.cost['30_days'])} hint="Verified pricing only"/>
  <Metric label="Cache rate" value={data.overview.cache_rate==null?'Unavailable':`${Math.round(data.overview.cache_rate*100)}%`} tone="cyan" hint="Cached / inclusive input"/>
  <Metric label="Cache savings" value={usd(data.cost.cache_savings)} tone="green" hint="Estimated counterfactual"/>
  </section><section className="split"><ChartPanel title="Token usage over time"><TokenChart data={data.series}/></ChartPanel><Evidence data={data}/></section><SessionTable rows={data.sessions}/><BreakdownTable title="Recent projects" rows={data.projects} metric="tokens"/></>}

function TokensPage({data}:{data:Data}){return <><section className="hero-grid token-cards">
  <Metric label="Inclusive input" value={compact(data.overview.input_tokens)} hint="Fresh + cached + cache writes"/>
  <Metric label="Cached input" value={compact(data.overview.cached_input_tokens)} tone="cyan" hint="Discounted cache reads"/>
  <Metric label="Cache writes" value={compact(data.overview.cache_write_input_tokens)} hint="Explicit cache creation"/>
  <Metric label="Output" value={compact(data.overview.output_tokens)} tone="violet" hint="Includes visible and reasoning output"/>
  </section><ChartPanel title="Fresh, cached, and output tokens"><TokenChart data={data.series}/></ChartPanel><BreakdownTable title="Tokens by project" rows={data.projects} metric="tokens"/></>}

function CostPage({data}:{data:Data}){return <><section className="hero-grid">
  <Metric label="Today" value={usd(data.cost.today)} tone="violet" hint="Estimated API-equivalent"/>
  <Metric label="7 days" value={usd(data.cost['7_days'])} hint="Estimated API-equivalent"/>
  <Metric label="30 days" value={usd(data.cost['30_days'])} hint="Estimated API-equivalent"/>
  <Metric label="Cache savings" value={usd(data.cost.cache_savings)} tone="green" hint="Estimated counterfactual"/>
  </section><section className="split"><ChartPanel title="Estimated cost over time"><CostChart data={data.series}/></ChartPanel><BreakdownTable title="Cost by model" rows={data.costModels} metric="cost"/></section><BreakdownTable title="Cost by project" rows={data.costProjects} metric="cost"/><BreakdownTable title="Highest-cost sessions" rows={data.costSessions} metric="cost"/></>}

function TokenChart({data}:{data:Point[]}){return <React.Suspense fallback={<div className="chart-loading"/>}><Charts kind="tokens" data={data}/></React.Suspense>}
function CostChart({data}:{data:Point[]}){return <React.Suspense fallback={<div className="chart-loading"/>}><Charts kind="cost" data={data}/></React.Suspense>}
function ChartPanel({title,children}:{title:string;children:React.ReactNode}){return <section className="panel chart"><div className="panelhead"><div><p className="eyebrow">30-day window</p><h2>{title}</h2></div></div>{children}</section>}
function Metric({label,value,hint,tone=''}:{label:string;value:string;hint:string;tone?:string}){return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>}
function Evidence({data}:{data:Data}){return <section className="panel posture"><p className="eyebrow">Data posture</p><h2>Evidence, not guesses</h2><div className="ring"><div><b>{data.overview.sessions-data.cost.unavailable_sessions}</b><span>priced sessions</span></div></div><ul><li><i className="ok"/>Exact token snapshots</li><li><i className="ok"/>Official model pricing</li><li><i/>Historical prices pending</li></ul><p className="footnote">Every monetary value is an estimated API-equivalent cost, never an actual subscription charge.</p></section>}
function SessionTable({rows}:{rows:Session[]}){return <section className="panel standalone"><div className="panelhead"><div><p className="eyebrow">Recent activity</p><h2>Sessions</h2></div></div><div className="table"><div className="tr th"><span>Project</span><span>Model</span><span>Tokens</span><span>Last activity</span></div>{rows.map(s=><div className="tr" key={s.session_id}><span><b>{s.project_name||'Unassigned'}</b><small>{s.session_id.slice(0,12)}</small></span><span className="pill">{s.model||'Unknown'}</span><span>{compact(s.total_tokens)}</span><span>{s.last_activity?new Date(s.last_activity).toLocaleString():'Unknown'}</span></div>)}</div></section>}
function BreakdownTable({title,rows,metric}:{title:string;rows:Breakdown[];metric:'tokens'|'cost'}){return <section className="panel standalone"><div className="panelhead"><div><p className="eyebrow">Breakdown</p><h2>{title}</h2></div></div><div className="table"><div className="tr breakdown th"><span>Name</span><span>Sessions</span><span>Cached</span><span>{metric==='cost'?'API equivalent':'Total tokens'}</span></div>{rows.slice(0,12).map(row=><div className="tr breakdown" key={row.name}><span><b>{row.name}</b><small>{row.unpriced_sessions?`${row.unpriced_sessions} unpriced`:''}</small></span><span>{row.sessions}</span><span>{compact(row.cached_input_tokens)}</span><span>{metric==='cost'?usd(row.estimated_api_equivalent_cost):compact(row.total_tokens)}</span></div>)}</div></section>}
function Loading(){return <div className="skeleton-grid">{Array.from({length:7}).map((_,i)=><div className="skeleton" key={i}/>)}</div>}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
