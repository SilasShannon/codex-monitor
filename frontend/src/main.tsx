import React from 'react'
import ReactDOM from 'react-dom/client'
import { Activity, Boxes, CircleDollarSign, Database, FolderGit2, Gauge, Search, Settings, Wrench } from 'lucide-react'
import './styles.css'

type Page = 'Overview'|'Live'|'Sessions'|'Tokens'|'Cost'|'Tools'|'MCP'
type Overview = {active_sessions:number;sessions:number;total_tokens:number;input_tokens:number;cached_input_tokens:number;cache_write_input_tokens:number;output_tokens:number;cache_rate:number|null}
type Cost = {today:string;['7_days']:string;['30_days']:string;all_time:string;cache_savings:string;unavailable_sessions:number}
type Session = {session_id:string;project_name?:string;model?:string;last_activity?:string;total_tokens?:number}
type Point = {date:string;input_tokens:number;cached_input_tokens:number;output_tokens:number;total_tokens:number;estimated_api_equivalent_cost:string;unpriced_sessions:number}
type Breakdown = {name:string;sessions:number;input_tokens:number;cached_input_tokens:number;output_tokens:number;total_tokens:number;estimated_api_equivalent_cost:string;unpriced_sessions:number}
type Briefing = {session_id:string;project:string;path?:string;model?:string;active:boolean;last_activity?:string;request?:string;plain_language_status:string;latest_visible_update?:string;observations:string[];commands:{command:string;success:boolean|null}[];tests:{command:string;success:boolean|null}[];files:{path:string;action:string}[];concepts:{name:string;explanation:string}[];evidence_note:string}
type ActivityRow = {name:string;server?:string;kind:string;calls:number;successes:number;failures:number;unknown_outcomes:number;average_duration_ms:number|null;sessions:number;projects:number;last_activity?:string}
type ActivityData = {scope:'tools'|'mcp';summary:{calls:number;successes:number;failures:number;unknown_outcomes:number;average_duration_ms:number|null;sessions:number;projects:number};rows:ActivityRow[];evidence_note:string}
type Data = {overview:Overview;cost:Cost;sessions:Session[];briefings:Briefing[];tools:ActivityData;mcp:ActivityData;series:Point[];projects:Breakdown[];models:Breakdown[];costProjects:Breakdown[];costModels:Breakdown[];costSessions:Breakdown[]}
const Charts = React.lazy(()=>import('./charts'))

const nav = [
  ['Overview', Gauge], ['Live', Activity], ['Projects', FolderGit2], ['Sessions', Database],
  ['Tokens', Boxes], ['Cost', CircleDollarSign], ['Models', Boxes], ['Tools', Wrench],
  ['MCP', Boxes], ['Git', FolderGit2], ['Search', Search], ['Settings', Settings],
] as const
const ready = new Set(['Overview','Live','Sessions','Tokens','Cost','Tools','MCP'])
const compact = (value?:number) => value==null?'Unavailable':Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(value)
const usd = (value?:string|number) => value==null?'Unavailable':Number(value).toLocaleString('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2})
const api = async <T,>(path:string):Promise<T> => {const response=await fetch(path);if(!response.ok)throw Error(`${response.status}`);return response.json()}

function App(){
  const [page,setPage]=React.useState<Page>('Overview'); const [data,setData]=React.useState<Data|null>(null); const [error,setError]=React.useState('')
  React.useEffect(()=>{const loadAll=()=>Promise.all([
    api<Overview>('/api/overview'),api<Cost>('/api/cost/summary'),api<Session[]>('/api/sessions?limit=8'),
    api<Briefing[]>('/api/live/briefings'),api<ActivityData>('/api/tools'),api<ActivityData>('/api/mcp'),
    api<Point[]>('/api/analytics/timeseries?days=30'),api<Breakdown[]>('/api/analytics/breakdown?dimension=project'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=model'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=project&sort=cost'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=model&sort=cost'),
    api<Breakdown[]>('/api/analytics/breakdown?dimension=session&sort=cost'),
  ]).then(([overview,cost,sessions,briefings,tools,mcp,series,projects,models,costProjects,costModels,costSessions])=>{setData({overview,cost,sessions,briefings,tools,mcp,series,projects,models,costProjects,costModels,costSessions});setError('')}).catch(()=>setError('The local analytics API is unavailable.'))
    const loadLive=()=>Promise.all([api<Overview>('/api/overview'),api<Cost>('/api/cost/summary'),api<Session[]>('/api/sessions?limit=8'),api<Briefing[]>('/api/live/briefings'),api<ActivityData>('/api/tools'),api<ActivityData>('/api/mcp')]).then(([overview,cost,sessions,briefings,tools,mcp])=>{setData(current=>current?{...current,overview,cost,sessions,briefings,tools,mcp}:current);setError('')}).catch(()=>setError('The local analytics API is unavailable.'))
    loadAll();const liveTimer=window.setInterval(loadLive,5000);const analyticsTimer=window.setInterval(loadAll,60000);return()=>{window.clearInterval(liveTimer);window.clearInterval(analyticsTimer)}},[])
  return <div className="shell"><aside><div className="brand"><span className="brandmark">C</span><div>Codex Monitor<small>Local observability</small></div></div>
    <nav>{nav.map(([label,Icon])=><button className={page===label?'active':''} key={label} onClick={()=>ready.has(label)&&setPage(label as Page)}><Icon size={17}/><span>{label}</span>{!ready.has(label)&&<em>Soon</em>}</button>)}</nav>
    <div className="local"><span/><div>Local only<small>127.0.0.1</small></div></div></aside>
    <main><header><div><p className="eyebrow">Workspace analytics</p><h1>{page}</h1></div><div className="range">Last 30 days</div></header>
      {error&&<div className="notice">{error}</div>}{!data?<Loading/>:page==='Overview'?<OverviewPage data={data}/>:page==='Live'?<LivePage data={data}/>:page==='Sessions'?<SessionsPage data={data}/>:page==='Tokens'?<TokensPage data={data}/>:page==='Cost'?<CostPage data={data}/>:page==='Tools'?<ActivityPage data={data.tools}/>:<ActivityPage data={data.mcp}/>}</main></div>
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

function LivePage({data}:{data:Data}){return <>{data.briefings.length===0?<section className="panel empty"><Activity size={24}/><h2>No reliably active sessions</h2><p>Start Codex activity or configure local OTel. This view refreshes every five seconds.</p></section>:<section className="briefing-grid">{data.briefings.map(briefing=><BriefingCard briefing={briefing} key={briefing.session_id}/>)}</section>}</>}
function SessionsPage({data}:{data:Data}){return <><SessionTable rows={data.sessions}/>{data.briefings.length>0&&<><div className="section-title"><p className="eyebrow">Human-readable progress</p><h2>Active session briefings</h2></div><section className="briefing-grid">{data.briefings.map(briefing=><BriefingCard briefing={briefing} key={briefing.session_id}/>)}</section></>}</>}
function BriefingCard({briefing}:{briefing:Briefing}){return <article className="panel briefing"><div className="briefing-head"><div><p className="eyebrow">{briefing.active?'Active now':'Recent session'}</p><h2>{briefing.project}</h2><small>{briefing.model||'Model unknown'} · {briefing.session_id.slice(0,12)}</small></div><span className="live-dot">Live</span></div><p className="status-copy">{briefing.plain_language_status}</p>{briefing.latest_visible_update&&<div className="update"><b>Latest visible update</b><p>{briefing.latest_visible_update}</p></div>}<BriefSection title="What the monitor observed" items={briefing.observations}/>{briefing.files.length>0&&<BriefSection title="Files being worked on" items={briefing.files.slice(0,6).map(file=>`${file.action}: ${file.path}`)}/>} {briefing.tests.length>0&&<BriefSection title="Tests and verification" items={briefing.tests.slice(0,5).map(test=>`${test.success===true?'Passed':test.success===false?'Failed':'Ran'}: ${test.command}`)}/>} {briefing.concepts.length>0&&<div className="concepts"><b>Concepts to understand</b>{briefing.concepts.map(concept=><div key={concept.name}><strong>{concept.name}</strong><p>{concept.explanation}</p></div>)}</div>}<p className="evidence">{briefing.evidence_note}</p></article>}
function BriefSection({title,items}:{title:string;items:string[]}){return <div className="brief-section"><b>{title}</b><ul>{items.map((item,index)=><li key={`${item}-${index}`}>{item}</li>)}</ul></div>}

function ActivityPage({data}:{data:ActivityData}){const label=data.scope==='mcp'?'MCP':'tool';return <><section className="hero-grid activity-cards">
  <Metric label={`${label} calls`} value={compact(data.summary.calls)} tone="violet" hint={`${data.summary.sessions} sessions`}/>
  <Metric label="Successful" value={compact(data.summary.successes)} tone="green" hint="Explicit successful outcomes"/>
  <Metric label="Failed" value={compact(data.summary.failures)} hint="Explicit failed outcomes"/>
  <Metric label="Unknown outcomes" value={compact(data.summary.unknown_outcomes)} tone="cyan" hint="Not exposed by Codex"/>
  </section><ActivityTable data={data}/><p className="activity-evidence">{data.evidence_note}</p></>}
function ActivityTable({data}:{data:ActivityData}){return <section className="panel standalone"><div className="panelhead"><div><p className="eyebrow">Observed local activity</p><h2>{data.scope==='mcp'?'MCP servers and tools':'Codex tools'}</h2></div></div>{data.rows.length===0?<div className="table-empty">No {data.scope==='mcp'?'MCP':'tool'} calls have been observed yet.</div>:<div className="table"><div className="tr activity-row th"><span>{data.scope==='mcp'?'Server / tool':'Tool'}</span><span>Calls</span><span>Outcomes</span><span>Avg duration</span><span>Sessions</span></div>{data.rows.map(row=><div className="tr activity-row" key={`${row.server||''}-${row.name}`}><span><b>{row.server?`${row.server} / ${row.name}`:row.name.replaceAll('_',' ')}</b><small>{row.kind}</small></span><span>{compact(row.calls)}</span><span><i className="outcome success">{row.successes} ok</i><i className="outcome failure">{row.failures} failed</i><small>{row.unknown_outcomes} unknown</small></span><span>{row.average_duration_ms==null?'Unknown':`${Math.round(row.average_duration_ms)} ms`}</span><span>{row.sessions}<small>{row.projects} projects</small></span></div>)}</div>}</section>}

function TokenChart({data}:{data:Point[]}){return <React.Suspense fallback={<div className="chart-loading"/>}><Charts kind="tokens" data={data}/></React.Suspense>}
function CostChart({data}:{data:Point[]}){return <React.Suspense fallback={<div className="chart-loading"/>}><Charts kind="cost" data={data}/></React.Suspense>}
function ChartPanel({title,children}:{title:string;children:React.ReactNode}){return <section className="panel chart"><div className="panelhead"><div><p className="eyebrow">30-day window</p><h2>{title}</h2></div></div>{children}</section>}
function Metric({label,value,hint,tone=''}:{label:string;value:string;hint:string;tone?:string}){return <article className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>}
function Evidence({data}:{data:Data}){return <section className="panel posture"><p className="eyebrow">Data posture</p><h2>Evidence, not guesses</h2><div className="ring"><div><b>{data.overview.sessions-data.cost.unavailable_sessions}</b><span>priced sessions</span></div></div><ul><li><i className="ok"/>Exact token snapshots</li><li><i className="ok"/>Official model pricing</li><li><i/>Historical prices pending</li></ul><p className="footnote">Every monetary value is an estimated API-equivalent cost, never an actual subscription charge.</p></section>}
function SessionTable({rows}:{rows:Session[]}){return <section className="panel standalone"><div className="panelhead"><div><p className="eyebrow">Recent activity</p><h2>Sessions</h2></div></div><div className="table"><div className="tr th"><span>Project</span><span>Model</span><span>Tokens</span><span>Last activity</span></div>{rows.map(s=><div className="tr" key={s.session_id}><span><b>{s.project_name||'Unassigned'}</b><small>{s.session_id.slice(0,12)}</small></span><span className="pill">{s.model||'Unknown'}</span><span>{compact(s.total_tokens)}</span><span>{s.last_activity?new Date(s.last_activity).toLocaleString():'Unknown'}</span></div>)}</div></section>}
function BreakdownTable({title,rows,metric}:{title:string;rows:Breakdown[];metric:'tokens'|'cost'}){return <section className="panel standalone"><div className="panelhead"><div><p className="eyebrow">Breakdown</p><h2>{title}</h2></div></div><div className="table"><div className="tr breakdown th"><span>Name</span><span>Sessions</span><span>Cached</span><span>{metric==='cost'?'API equivalent':'Total tokens'}</span></div>{rows.slice(0,12).map(row=><div className="tr breakdown" key={row.name}><span><b>{row.name}</b><small>{row.unpriced_sessions?`${row.unpriced_sessions} unpriced`:''}</small></span><span>{row.sessions}</span><span>{compact(row.cached_input_tokens)}</span><span>{metric==='cost'?usd(row.estimated_api_equivalent_cost):compact(row.total_tokens)}</span></div>)}</div></section>}
function Loading(){return <div className="skeleton-grid">{Array.from({length:7}).map((_,i)=><div className="skeleton" key={i}/>)}</div>}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
