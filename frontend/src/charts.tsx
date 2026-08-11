import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Point = {date:string;input_tokens:number;cached_input_tokens:number;output_tokens:number;estimated_api_equivalent_cost:string}
const compact=(value:number)=>Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(value)
const usd=(value:number)=>value.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2})

export default function Charts({kind,data}:{kind:'tokens'|'cost';data:Point[]}){
  if(kind==='cost'){
    const values=data.map(point=>({...point,cost:Number(point.estimated_api_equivalent_cost)}))
    return <ResponsiveContainer width="100%" height={250}><BarChart data={values}><CartesianGrid stroke="#1c232d" vertical={false}/><XAxis dataKey="date" tickFormatter={value=>value.slice(5)} stroke="#566171" fontSize={9}/><YAxis tickFormatter={value=>`$${value}`} stroke="#566171" fontSize={9}/><Tooltip content={<ChartTooltip cost/>}/><Bar dataKey="cost" fill="#a78bfa" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer>
  }
  return <ResponsiveContainer width="100%" height={250}><AreaChart data={data}><defs><linearGradient id="cached" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#67e8f9" stopOpacity={.35}/><stop offset="95%" stopColor="#67e8f9" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#1c232d" vertical={false}/><XAxis dataKey="date" tickFormatter={value=>value.slice(5)} stroke="#566171" fontSize={9}/><YAxis tickFormatter={compact} stroke="#566171" fontSize={9}/><Tooltip content={<ChartTooltip/>}/><Area type="monotone" dataKey="input_tokens" stroke="#8b5cf6" fill="#8b5cf622"/><Area type="monotone" dataKey="cached_input_tokens" stroke="#67e8f9" fill="url(#cached)"/><Area type="monotone" dataKey="output_tokens" stroke="#6ee7b7" fill="#6ee7b711"/></AreaChart></ResponsiveContainer>
}

function ChartTooltip({active,payload,label,cost=false}:any){
  if(!active||!payload?.length)return null
  return <div className="tooltip"><b>{label}</b>{payload.map((item:any)=><span key={item.dataKey}>{item.name}: {cost?usd(item.value):compact(item.value)}</span>)}</div>
}
