import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, Bell, Bot, Check, ChevronDown,
  CircleHelp, Command, Database, Download, LayoutDashboard, LoaderCircle, MessageSquare,
  MoreHorizontal, RefreshCw, Search, Send, ShieldCheck, Sparkles, Target, TrendingUp,
  Wallet, X, Zap
} from 'lucide-react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis
} from 'recharts';

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const money = (n, compact = false) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: compact ? 1 : 0,
  notation: compact ? 'compact' : 'standard'
}).format(Number(n || 0));
const number = n => new Intl.NumberFormat('en-IN').format(Number(n || 0));
const monthLabel = value => {
  if (!value) return '';
  const [y, m] = value.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'short' });
};
const COLORS = ['#72e4c0', '#8c9eff', '#f6bd70', '#e88fc4', '#75c7ed', '#b5a0ff'];
const prompts = [
  { icon: Wallet, label: 'Executive summary', text: 'Give me an executive summary of sales performance.' },
  { icon: Target, label: 'Profit after discounts', text: 'Which products have the highest profit after discounts?' },
  { icon: TrendingUp, label: 'Monthly regional revenue', text: 'Compare monthly revenue across all regions.' },
  { icon: BarChart3, label: 'Top 5 products · pie chart', text: 'Show the top 5 products by revenue as a pie chart.' },
  { icon: Activity, label: 'Unusual sales patterns', text: 'Find unusual patterns in the sales data.' },
];

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [aiStatus, setAiStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [activeNav, setActiveNav] = useState('Overview');
  const [showAllData, setShowAllData] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [dashRes, aiRes] = await Promise.all([fetch(`${API}/dashboard`), fetch(`${API}/ai-status`)]);
      if (!dashRes.ok) throw new Error('Could not load dashboard data. Is the FastAPI backend running?');
      const dash = await dashRes.json();
      setDashboard(dash);
      if (aiRes.ok) setAiStatus(await aiRes.json());
    } catch (e) { setError(e.message || 'Unable to connect to the backend.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const askQuestion = async (text = question) => {
    const q = text.trim(); if (!q || asking) return;
    setQuestion(q); setAsking(true); setAnswer(null);
    try {
      const response = await fetch(`${API}/ask`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, history: chatHistory.slice(-6) })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'The question could not be processed.');
      setAnswer(data);
      setChatHistory(previous => [...previous, { question: q, answer: data.answer }].slice(-8));
    } catch (e) { setAnswer({ error: e.message || 'Unable to get an answer.' }); }
    finally { setAsking(false); }
  };

  const kpis = dashboard?.kpis || {};
  const trend = useMemo(() => (dashboard?.monthly_revenue || []).map(r => ({ ...r, label: monthLabel(r.month) })), [dashboard]);
  const quality = dashboard?.data_quality?.summary || {};
  const excluded = Number(quality.excluded_rows || 0);
  const totalRows = Number(quality.total_rows || 0);
  const validRows = Math.max(0, totalRows - excluded);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Command size={19} strokeWidth={2.4}/></div><div><b>SALES</b><span>INTELLIGENCE</span></div></div>
      <div className="workspace"><div className="workspace-avatar">S</div><div><strong>Sales workspace</strong><small>Business analytics</small></div><ChevronDown size={15}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="nav-list" aria-label="Main navigation">
        <button className={`nav-item ${activeNav === 'AI analyst' ? 'active' : ''}`} onClick={() => {setActiveNav('AI analyst'); document.getElementById('ask-panel')?.scrollIntoView({behavior:'smooth',block:'start'});}}><Bot size={17}/>AI Analyst<span className="nav-pill">AI</span></button>
        <button className={`nav-item ${activeNav === 'Overview' ? 'active' : ''}`} onClick={() => {setActiveNav('Overview'); document.getElementById('overview-panel')?.scrollIntoView({behavior:'smooth',block:'start'});}}><LayoutDashboard size={17}/>Overview</button>
        <button className={`nav-item ${activeNav === 'Data quality' ? 'active' : ''}`} onClick={() => {setActiveNav('Data quality'); document.getElementById('quality-panel')?.scrollIntoView({behavior:'smooth',block:'start'});}}><ShieldCheck size={17}/>Data Quality</button>
      </nav>
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><b>Need a hand?</b><p>Ask the AI analyst to explore your sales data.</p><button onClick={() => {setActiveNav('AI analyst'); document.getElementById('ask-panel')?.scrollIntoView({behavior:'smooth'});}}>Explore assistant <ArrowUpRight size={13}/></button></div><div className="profile"><div className="profile-avatar">BI</div><div><strong>BI Analyst</strong><small>Workspace owner</small></div><MoreHorizontal size={18}/></div></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div className="breadcrumb">Sales workspace <span>/</span> <b>{activeNav}</b></div><div className="top-actions"><div className="live-status"><i/> Live data</div><button className="icon-button" aria-label="Refresh data" onClick={loadDashboard}><RefreshCw size={16}/></button><button className="icon-button" aria-label="Notifications"><Bell size={16}/></button><div className="top-avatar">BI</div></div></header>
      <div className="page-wrap">
        <motion.section className="page-heading" initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.45}}>
          <div><div className="eyebrow"><span className="eyebrow-dot"/> SALES INTELLIGENCE <span className="eyebrow-line"/></div><h1>Sales <em>overview</em></h1><p>Understand performance, explore trends, and make confident decisions with your sales data.</p></div>
          <div className="heading-actions"><div className="date-chip"><Activity size={15}/> Live dataset</div><button className="export-button" onClick={() => window.print()}><Download size={15}/> Export view</button></div>
        </motion.section>

        {error && <div className="error-banner"><Database size={17}/><div><b>Backend connection needed</b><span>{error} Start it with <code>uvicorn backend.main:app --reload</code>.</span></div><button onClick={loadDashboard}><RefreshCw size={14}/> Retry</button></div>}

        <motion.section id="ask-panel" className="ai-section" initial={{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{delay:.42}}>
          <div className="section-intro"><div><span className="section-number">01</span><div><h2>AI Analyst</h2><p>Ask questions about your sales data in plain language.</p></div></div><span className="section-context">NATURAL LANGUAGE ANALYSIS</span></div>
          <div className="ai-panel"><div className="ai-glow"/><div className="ai-topline"><div className="ai-brand"><div className="ai-icon"><Sparkles size={18}/></div><div><div className="panel-kicker">YOUR INTELLIGENCE LAYER</div><h2>Ask your data anything.</h2></div></div><div className="ai-powered"><span className="pulse-dot"/> AI ANALYST <span className="powered-divider"/> {aiStatus?.active_mode || 'Checking AI provider'}</div></div>
          <p className="ai-description">Go beyond dashboards. Ask a question in plain English and get a clear answer backed by your actual sales data.</p>
          <form className="ask-form" onSubmit={e=>{e.preventDefault();askQuestion();}}><Search size={18}/><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="e.g. Which product generated the highest revenue?" maxLength={1000}/><button type="submit" disabled={!question.trim()||asking}>{asking ? <LoaderCircle className="spin" size={17}/> : <><span>Ask AI</span><Send size={15}/></>}</button></form>
          <div className="prompt-row"><span>TRY ASKING</span>{prompts.map((p,i)=><button key={p.text} onClick={()=>askQuestion(p.text)} disabled={asking}><p.icon size={12}/>{p.label}</button>)}</div>
          <AnimatePresence>{answer && <motion.div className={`answer-card ${answer.error?'answer-error':''}`} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} exit={{opacity:0,y:8}}><div className="answer-head"><div className="answer-check">{answer.error?<X size={15}/>:<Check size={15}/>}</div><div><b>{answer.error?'Could not complete analysis':'Analysis complete'}</b><span>{answer.error?'Check the question or AI configuration.':`${answer.interpretation_source || 'AI'} generated SQL · ${answer.execution_source || 'Local SQLite'}`}</span></div><button onClick={()=>setAnswer(null)} aria-label="Close answer"><X size={16}/></button></div><p>{answer.error || answer.answer}</p>{answer.insights?.length>0 && <ul className="insight-list">{answer.insights.map((item,i)=><li key={i}>{item}</li>)}</ul>}{answer.limitations && <div className="answer-limitation">{answer.limitations}</div>}{answer.chart?.type==='number' && answer.rows?.[0] && <div className="scalar-result">{Object.entries(answer.rows[0]).map(([key,value])=><div key={key}><span>{key.replaceAll('_',' ')}</span><b>{typeof value==='number'?new Intl.NumberFormat('en-IN',{maximumFractionDigits:2}).format(value):String(value??'—')}</b></div>)}</div>}{answer.rows?.length>0 && <><div className="result-chart-heading"><b>{answer.chart?.title || 'Query visualization'}</b><span>{number(answer.row_count)} result rows</span></div><DynamicResultChart chart={answer.chart} rows={answer.rows}/><div className="result-table-wrap"><table className="result-table"><thead><tr>{answer.columns.map(col=><th key={col}>{col.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{answer.rows.slice(0,15).map((row,i)=><tr key={i}>{answer.columns.map(col=><td key={col}>{row[col]===null?'—':typeof row[col]==='number'?new Intl.NumberFormat('en-IN',{maximumFractionDigits:2}).format(row[col]):String(row[col])}</td>)}</tr>)}</tbody></table>{answer.row_count>15 && <span className="table-note">Showing first 15 of {number(answer.row_count)} rows.</span>}</div></>}{answer.sql && <details className="sql-details"><summary>View generated SQL</summary><pre>{answer.sql}</pre></details>}</motion.div>}</AnimatePresence>
          </div>
        </motion.section>


        <section id="overview-panel" className="overview-section" aria-label="Sales overview">
          <div className="section-intro"><div><span className="section-number">02</span><div><h2>Business overview</h2><p>Your sales performance at a glance.</p></div></div><span className="section-context">KEY METRICS & TRENDS</span></div>
        <section className="kpi-grid">
          <KpiCard title="Total revenue" value={money(kpis.total_revenue)} note="Across completed transactions" icon={Wallet} accent="mint" delay={0.04} loading={loading}/>
          <KpiCard title="Transactions" value={number(kpis.transaction_count)} note="Valid completed orders" icon={BarChart3} accent="blue" delay={0.1} loading={loading}/>
          <KpiCard title="Avg. order value" value={money(kpis.average_transaction_value)} note="Revenue per transaction" icon={Activity} accent="amber" delay={0.16} loading={loading}/>
          <KpiCard title="Units sold" value={number(kpis.units_sold)} note="Total quantity delivered" icon={Target} accent="violet" delay={0.22} loading={loading}/>
        </section>

        <section className="charts-grid">
          <motion.div className="panel revenue-panel" initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} transition={{delay:.18}}>
            <div className="panel-head"><div><div className="panel-kicker">PERFORMANCE</div><h2>Revenue overview</h2><p>Monthly revenue across your business</p></div><button className="more-button" aria-label="More options"><MoreHorizontal size={19}/></button></div>
            <div className="chart-legend"><span><i className="legend-dot mint-dot"/> Revenue</span><span className="chart-unit">INR · MONTHLY</span></div>
            <div className="area-chart">{loading ? <ChartSkeleton/> : trend.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{top:10,right:8,left:0,bottom:0}}><defs><linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#70dfbd" stopOpacity={.25}/><stop offset="95%" stopColor="#70dfbd" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#26313c" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fill:'#778494',fontSize:11}} dy={10}/><YAxis axisLine={false} tickLine={false} tick={{fill:'#778494',fontSize:10}} tickFormatter={v=>`₹${(v/1000).toFixed(0)}k`} width={48}/><Tooltip content={<ChartTooltip/>}/><Area type="monotone" dataKey="revenue" stroke="#75e2c1" strokeWidth={2.5} fill="url(#revenueFill)" activeDot={{r:5,fill:'#75e2c1',stroke:'#101923',strokeWidth:3}}/></AreaChart></ResponsiveContainer> : <EmptyChart/>}</div>
            <div className="chart-foot"><span><i className="foot-indicator"/> Based on verified completed sales</span><span>{trend.length} months tracked</span></div>
          </motion.div>

          <motion.div className="panel region-panel" initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} transition={{delay:.25}}>
            <div className="panel-head"><div><div className="panel-kicker">GEOGRAPHY</div><h2>Revenue by region</h2><p>Where your sales are coming from</p></div><button className="more-button" aria-label="More options"><MoreHorizontal size={19}/></button></div>
            <div className="region-chart">{loading ? <ChartSkeleton/> : (dashboard?.revenue_by_region || []).length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.revenue_by_region} layout="vertical" margin={{top:3,right:14,left:0,bottom:0}}><CartesianGrid stroke="#26313c" strokeDasharray="3 5" horizontal={false}/><XAxis type="number" axisLine={false} tickLine={false} tick={{fill:'#778494',fontSize:10}} tickFormatter={v=>`₹${v/1000}k`}/><YAxis type="category" dataKey="region" axisLine={false} tickLine={false} tick={{fill:'#c1cad3',fontSize:12}} width={55}/><Tooltip content={<ChartTooltip/>}/><Bar dataKey="revenue" radius={[0,6,6,0]} barSize={17}>{(dashboard?.revenue_by_region || []).map((r,i)=><Cell key={r.region} fill={COLORS[i%COLORS.length]}/>)}</Bar></BarChart></ResponsiveContainer> : <EmptyChart/>}</div>
            <div className="region-foot">{(dashboard?.revenue_by_region || []).slice(0,4).map((r,i)=><div key={r.region}><span><i style={{background:COLORS[i%COLORS.length]}}/>{r.region}</span><b>{money(r.revenue,true)}</b></div>)}</div>
          </motion.div>
        </section>

        <section className="lower-grid">
          <motion.div className="panel product-panel" initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} transition={{delay:.3}}>
            <div className="panel-head"><div><div className="panel-kicker">PRODUCT MIX</div><h2>Top performing products</h2><p>Ranked by generated revenue</p></div><span className="subtle-tag">TOP 6</span></div>
            <div className="product-list">{loading ? <ChartSkeleton/> : (dashboard?.top_products || []).map((p,i)=>{
              const max = Math.max(...(dashboard?.top_products || []).map(x=>Number(x.revenue)),1);
              return <div className="product-row" key={p.product}><div className="product-rank">{String(i+1).padStart(2,'0')}</div><div className="product-info"><div className="product-meta"><b>{p.product}</b><span>{money(p.revenue,true)}</span></div><div className="progress-track"><motion.div className="progress-fill" initial={{width:0}} animate={{width:`${Number(p.revenue)/max*100}%`}} transition={{duration:.8,delay:.35+i*.08}} style={{background:COLORS[i%COLORS.length]}}/></div></div></div>;
            })}</div>
          </motion.div>
          <motion.div className="panel category-panel" initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} transition={{delay:.36}}>
            <div className="panel-head"><div><div className="panel-kicker">CONTRIBUTION</div><h2>Revenue by category</h2><p>Share of total revenue</p></div><button className="more-button" aria-label="More options"><MoreHorizontal size={19}/></button></div>
            <div className="donut-wrap">{loading ? <ChartSkeleton/> : (dashboard?.revenue_by_category || []).length ? <><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={dashboard.revenue_by_category} dataKey="revenue" nameKey="category" innerRadius="67%" outerRadius="88%" paddingAngle={4} stroke="none">{dashboard.revenue_by_category.map((r,i)=><Cell key={r.category} fill={COLORS[i%COLORS.length]}/>)}</Pie><Tooltip content={<ChartTooltip/>}/></PieChart></ResponsiveContainer><div className="donut-center"><b>{money(kpis.total_revenue,true)}</b><span>TOTAL</span></div></> : <EmptyChart/>}</div>
            <div className="category-legend">{(dashboard?.revenue_by_category || []).map((r,i)=><div key={r.category}><span><i style={{background:COLORS[i%COLORS.length]}}/>{r.category}</span><b>{money(r.revenue,true)}</b></div>)}</div>
          </motion.div>
        </section>
        </section>

        <section id="quality-panel" className="quality-section">
          <div className="section-intro"><div><span className="section-number">03</span><div><h2>Data quality</h2><p>Know which records are included in your analysis.</p></div></div><span className="section-context">VALIDATION & TRUST</span></div>
          <div className="quality-strip"><div className="quality-icon"><ShieldCheck size={19}/></div><div className="quality-copy"><b>Data integrity status</b><span>Analytics use validated transactions. Records flagged with data quality issues are excluded from the default analysis.</span><div className="quality-progress"><span style={{width:`${totalRows?Math.round(validRows/totalRows*100):0}%`}}/></div></div><div className="quality-stats"><div><b>{number(validRows)}</b><span>VALID ROWS</span></div><div><b>{number(excluded)}</b><span>EXCLUDED</span></div><div className="quality-rate"><b>{totalRows?`${Math.round(validRows/totalRows*100)}%`:'—'}</b><span>DATA HEALTH</span></div></div></div>
        </section>
        <footer className="footer"><span>© 2026 SALES INTELLIGENCE</span><span><i/> SECURE · DETERMINISTIC · AI-ASSISTED</span></footer>
      </div>
    </main>
  </div>;
}

function DynamicResultChart({chart,rows}) {
  if (!chart || chart.type === 'table' || chart.type === 'number' || !chart.x_key || !chart.y_keys?.length) return null;
  const data = rows.map(row => ({...row, ...Object.fromEntries(chart.y_keys.map(key => [key, Number(row[key] || 0)]))}));
  const colors = ['#75e2c1','#8c9eff','#f6bd70','#e88fc4','#75c7ed'];
  const axis = <><CartesianGrid stroke="#26313c" strokeDasharray="3 5" vertical={false}/><XAxis dataKey={chart.x_key} axisLine={false} tickLine={false} tick={{fill:'#9aa8b5',fontSize:10}}/><YAxis axisLine={false} tickLine={false} tick={{fill:'#82909e',fontSize:10}}/><Tooltip content={<ChartTooltip/>}/></>;
  return <div className="answer-chart"><ResponsiveContainer width="100%" height="100%">
    {chart.type === 'pie' ? <PieChart><Pie data={data} dataKey={chart.y_keys[0]} nameKey={chart.x_key} innerRadius="48%" outerRadius="78%" paddingAngle={3}>{data.map((row,i)=><Cell key={`${row[chart.x_key]}-${i}`} fill={colors[i%colors.length]}/>)}</Pie><Tooltip content={<ChartTooltip/>}/></PieChart> :
    chart.type === 'line' ? <LineChart data={data}>{axis}{chart.y_keys.map((key,i)=><Line key={key} type="monotone" dataKey={key} stroke={colors[i%colors.length]} strokeWidth={2.5} dot={{r:3}}/>)}</LineChart> :
    chart.type === 'area' ? <AreaChart data={data}>{axis}{chart.y_keys.map((key,i)=><Area key={key} type="monotone" dataKey={key} stroke={colors[i%colors.length]} fill={colors[i%colors.length]} fillOpacity={.15}/>)}</AreaChart> :
    <BarChart data={data}>{axis}{chart.y_keys.map((key,i)=><Bar key={key} dataKey={key} fill={colors[i%colors.length]} radius={[5,5,0,0]}/>)}</BarChart>}
  </ResponsiveContainer></div>;
}

function KpiCard({title,value,note,icon:Icon,accent,delay,loading}) {
  return <motion.div className={`kpi-card ${accent}`} initial={{opacity:0,y:14}} animate={{opacity:1,y:0}} transition={{duration:.42,delay}} whileHover={{y:-3,transition:{duration:.18}}}><div className="kpi-top"><span>{title}</span><div className="kpi-icon"><Icon size={17}/></div></div><div className="kpi-value">{loading?<span className="skeleton-line"/>:value}</div><div className="kpi-note"><span className="note-dot"/>{note}</div></motion.div>;
}
function ChartTooltip({active,payload,label}) {
  if (!active || !payload?.length) return null;
  const metric = String(payload[0].dataKey || payload[0].name || '');
  const value = /(revenue|sales|amount|price|discount|profit)/i.test(metric) ? money(payload[0].value) : number(payload[0].value);
  return <div className="chart-tooltip"><span>{label || payload[0].name}</span><b>{value}</b></div>;
}
function ChartSkeleton(){return <div className="chart-skeleton"><span/><span/><span/><span/><span/></div>;}
function EmptyChart(){return <div className="empty-chart">No completed sales data available yet.</div>;}

export default App;
