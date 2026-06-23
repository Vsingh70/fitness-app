// Nutrition redesign — screens for the side-by-side canvas.
// Exports web + iOS components for 3 directions, entry state, add-meal, trends.

// ---- shared SVG ring ----
function Ring({ size = 132, stroke = 9, value = 0.6, color = "var(--color-accent)", track = "var(--color-surface-sunken)" }) {
  const r = (size - stroke) / 2, c = 2 * Math.PI * r, off = c * (1 - value);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={track} strokeWidth={stroke}/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}/>
    </svg>
  );
}
const ArrowR = ({ s = 16 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>;
const SearchI = ({ s = 18 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
const PlusI = ({ s = 16 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M12 5v14M5 12h14"/></svg>;

// shared meal data
const MEALS = [
  { type: "Breakfast", at: "07:30", kcal: 490, p: 36, items: ["Rolled oats · 80g", "Whey isolate · 30g", "Blueberries · 120g"] },
  { type: "Lunch", at: "12:45", kcal: 760, p: 58, items: ["Chicken thigh · 200g", "Jasmine rice · 180g", "Greens + olive oil"] },
  { type: "Snack", at: "15:10", kcal: 176, p: 17, items: ["Greek yogurt 2% · 200g", "Honey · 15g"] },
];
const RECENT = [
  { nm: "Chicken breast", kc: 165 }, { nm: "Whey vanilla", kc: 117 }, { nm: "Greek yogurt", kc: 130 },
  { nm: "Banana", kc: 105 }, { nm: "Almonds", kc: 164 }, { nm: "Eggs ×2", kc: 156 },
];

// Logged meals — no fixed Breakfast/Lunch/Snack/Dinner. In flexible mode these
// are just "Meal 1, 2, 3…" added freely; with a plan, the plan's meal count drives them.
const LOGGED = [
  { n: "Meal 1", at: "07:30", kcal: 490, p: 36, c: 54, f: 11, items: ["Rolled oats · 80g", "Whey isolate · 30g", "Blueberries · 120g"] },
  { n: "Meal 2", at: "12:45", kcal: 760, p: 58, c: 55, f: 24, items: ["Chicken thigh · 200g", "Jasmine rice · 180g", "Greens + olive oil"] },
  { n: "Meal 3", at: "15:10", kcal: 176, p: 17, c: 21, f: 4, items: ["Greek yogurt 2% · 200g", "Honey · 15g"] },
];

// macro strip data (current / target)
const MACROS = [["Protein", "134", "200"], ["Carbs", "168", "300"], ["Fat", "51", "80"]];

function AddMealBtn({ ios }) {
  const st = ios
    ? { marginTop: 8, width: "100%", padding: "13px", border: "1px dashed var(--ios-label3)", borderRadius: 8, background: "transparent", color: "var(--ios-accent)", fontWeight: 600, fontSize: 13, fontFamily: "var(--ios-sans)", textTransform: "uppercase", letterSpacing: "0.06em", cursor: "pointer" }
    : { marginTop: 14, width: "100%", padding: "14px", border: "1px dashed var(--color-border-strong)", borderRadius: 6, background: "transparent", color: "var(--color-accent)", fontWeight: 600, fontSize: 13, fontFamily: "var(--font-sans)", textTransform: "uppercase", letterSpacing: "0.08em", cursor: "pointer" };
  return <button style={st}>+ Add meal</button>;
}

// ============ WEB CHROME ============
function WebFrame({ title, crumb = "Nutrition", children, action }) {
  const railIcons = ["▦","◴","✦","◷","⚙"];
  return (
    <div className="web-frame">
      <div className="web-rail">
        <div className="mk">g</div>
        <div className="ic">▦</div><div className="ic">◴</div>
        <div className="ic on">✦</div><div className="ic">◷</div>
        <div style={{ marginTop: "auto" }} className="ic">⚙</div>
      </div>
      <div className="web-main">
        <div className="web-topbar">
          <span className="crumb">{crumb}</span>
          <h1>{title}</h1>
          <span className="sp"></span>
          {action}
        </div>
        <div className="nw-wrap">{children}</div>
      </div>
    </div>
  );
}

// ============ DIRECTION A — LOG-FIRST (web) ============
function WebDirA() {
  return (
    <WebFrame title="Today" action={<button className="btn sm">Day · Week</button>}>
      <div className="aw-progress">
        <div><div className="big">1,620</div></div>
        <div className="of">of 2,680 kcal · 1,060 left</div>
        <div className="macros">
          <div className="m"><div className="v">134<span style={{fontSize:12,color:"var(--color-text-tertiary)"}}>g</span></div><div className="l">Protein</div></div>
          <div className="m"><div className="v">168<span style={{fontSize:12,color:"var(--color-text-tertiary)"}}>g</span></div><div className="l">Carbs</div></div>
          <div className="m"><div className="v">51<span style={{fontSize:12,color:"var(--color-text-tertiary)"}}>g</span></div><div className="l">Fat</div></div>
        </div>
      </div>

      <div className="aw-quick">
        <div className="aw-search">
          <SearchI s={20}/>
          <input placeholder="What did you eat?" defaultValue=""/>
          <button className="go"><PlusI/></button>
        </div>
        <div className="aw-recent">
          <div className="row-h"><span className="nw-kicker">Recent &amp; frequent</span><span className="nw-kicker" style={{color:"var(--color-accent)"}}>Scan · Photo</span></div>
          <div className="aw-chips">
            {RECENT.map(r => (
              <div className="aw-chip" key={r.nm}>
                <span className="nm">{r.nm}</span><span className="kc">{r.kc}</span><span className="plus">+</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="aw-meals">
        {LOGGED.map(m => (
          <div className="aw-meal" key={m.n}>
            <div className="when"><div className="t">{m.n}</div><div className="tm">{m.at}</div></div>
            <div className="items">{m.items.map((it,i) => <div className="it" key={i}><span>{it}</span></div>)}</div>
            <div className="tot">{m.kcal}<div className="p">{m.p}g protein</div></div>
          </div>
        ))}
      </div>
      <AddMealBtn/>
    </WebFrame>
  );
}

// ============ DIRECTION B — BUDGET / TIMELINE (web) ============
function WebDirB() {
  return (
    <WebFrame title="Today" action={<button className="btn sm">Adjust target</button>}>
      <div className="bw-hero">
        <div className="cell accent">
          <div className="lab">Calories remaining</div>
          <div className="big">1,060<span className="u">kcal</span></div>
          <div className="sub">1,620 eaten · 2,680 target</div>
          <div className="track"><div className="f" style={{width:"60%"}}></div></div>
        </div>
        <div className="cell">
          <div className="lab">Protein to go</div>
          <div className="big">66<span className="u">g</span></div>
          <div className="sub">134 of 200g · 67%</div>
          <div className="track"><div className="f ink" style={{width:"67%"}}></div></div>
        </div>
      </div>

      <div style={{display:"flex",alignItems:"baseline",justifyContent:"space-between",marginTop:30}}>
        <span className="nw-kicker">Your day</span>
        <span className="nw-kicker" style={{color:"var(--color-accent)"}}>+ Add to timeline</span>
      </div>
      <div className="bw-timeline" style={{marginTop:16}}>
        <div className="bw-node"><div className="dot"></div><div className="tm">07:30 · Breakfast</div><div className="hd"><span className="nm">Oats, whey &amp; berries</span><span className="kc">490</span></div><div className="its">36g protein · 54g carbs</div></div>
        <div className="bw-node"><div className="dot"></div><div className="tm">12:45 · Lunch</div><div className="hd"><span className="nm">Chicken, rice &amp; greens</span><span className="kc">760</span></div><div className="its">58g protein · 55g carbs</div></div>
        <div className="bw-node now"><div className="dot"></div><div className="bw-now-label">Now · 3:42 PM</div><div className="hd" style={{marginTop:2}}><span className="nm">Greek yogurt &amp; honey</span><span className="kc">176</span></div><div className="its">17g protein</div></div>
        <div className="bw-node future"><div className="dot"></div><div className="tm">Planned · Dinner</div><div className="hd"><span className="nm" style={{color:"var(--color-text-tertiary)"}}>~1,060 kcal to hit target</span></div><div className="cta">+ Log dinner <ArrowR s={13}/></div></div>
      </div>
    </WebFrame>
  );
}

// ============ DIRECTION C — EDITORIAL DASHBOARD (web) ============
function WebDirC() {
  return (
    <WebFrame title="Nutrition" crumb="The Daily" action={<button className="btn sm">Day · Week</button>}>
      <div className="cw-masthead">
        <div>
          <div className="date">Tuesday · May 27</div>
          <h2>The Daily Plate</h2>
        </div>
        <div className="edition">Cut block · Vol. 4<br/>−300 kcal / day</div>
      </div>

      <div className="cw-lead">
        <div className="cw-figure">
          <div className="cw-ring">
            <Ring size={132} stroke={8} value={0.6} color="var(--color-accent)"/>
            <div className="ctr"><div className="v">60%</div><div className="l">of target</div></div>
          </div>
          <div className="read">
            <div className="dek"><span className="drop">1,060</span>calories and 66g of protein still to go before the day closes.</div>
            <div className="by">On pace · protein-forward</div>
          </div>
        </div>
        <div className="cw-macros">
          <div className="mrow"><span className="nm">Protein</span><div className="ba"><div className="f" style={{width:"67%"}}></div></div><span className="va">134<span style={{fontSize:11,color:"var(--color-text-tertiary)"}}>/200</span></span></div>
          <div className="mrow"><span className="nm">Carbs</span><div className="ba"><div className="f" style={{width:"56%"}}></div></div><span className="va">168<span style={{fontSize:11,color:"var(--color-text-tertiary)"}}>/300</span></span></div>
          <div className="mrow"><span className="nm">Fat</span><div className="ba"><div className="f" style={{width:"64%"}}></div></div><span className="va">51<span style={{fontSize:11,color:"var(--color-text-tertiary)"}}>/80</span></span></div>
          <div className="mrow"><span className="nm">Fiber</span><div className="ba"><div className="f" style={{width:"63%"}}></div></div><span className="va">22<span style={{fontSize:11,color:"var(--color-text-tertiary)"}}>/35</span></span></div>
        </div>
      </div>

      <div className="cw-meals-h"><span className="t">Logged today</span><span className="nw-kicker" style={{color:"var(--color-accent)"}}>+ Add entry</span></div>
      <div className="cw-cols">
        {MEALS.map(m => (
          <div className="cw-entry" key={m.type}>
            <div className="eh"><span className="nm">{m.type}</span><span className="tm">{m.at}</span><span className="kc">{m.kcal}</span></div>
            <div className="its">{m.items.join(" · ")}</div>
          </div>
        ))}
        <div className="cw-entry empty">
          <div className="eh"><span className="nm">Dinner</span><span className="tm">—</span></div>
          <div className="its"><span className="add">+ Compose dinner</span></div>
        </div>
      </div>
    </WebFrame>
  );
}

// ============ iOS DIRECTIONS ============
function IosWrap({ children }) { return <div className="ni-wrap">{children}</div>; }

function IosDirA() {
  return (
    <IosWrap>
      <div className="ni-head"><div className="ni-kicker">Tuesday · May 27</div><h1 className="ni-title">Today</h1></div>
      <div className="ni-sec">
        <div className="nia-prog">
          <div className="big">1,620</div><div className="of">/ 2,680 · 1,060 left</div>
        </div>
        <div className="nia-macros">
          {MACROS.map(([l,v,t]) => (
            <div className="nia-mac" key={l}>
              <div className="l">{l}</div>
              <div className="v">{v}<span className="t">/{t}g</span></div>
            </div>
          ))}
        </div>
        <div className="nia-search"><SearchI s={18}/><span className="ph">What did you eat?</span><span className="go"><PlusI s={15}/></span></div>
        <div className="nia-recent">
          {RECENT.slice(0,5).map(r => <div className="nia-rchip" key={r.nm}><span className="nm">{r.nm}</span><span className="kc">{r.kc}</span></div>)}
        </div>
        <div style={{marginTop:18}}>
          {LOGGED.map(m => (
            <div className="nia-meal" key={m.n}>
              <div><div className="t">{m.n}</div><div className="tm">{m.at}</div><div className="its">{m.items.join(" · ")}</div></div>
              <div className="kc">{m.kcal}<div className="p">{m.p}g P</div></div>
            </div>
          ))}
          <AddMealBtn ios/>
        </div>
      </div>
    </IosWrap>
  );
}

function IosDirB() {
  return (
    <IosWrap>
      <div className="ni-head"><div className="ni-kicker">Tuesday · May 27</div><h1 className="ni-title">Budget</h1></div>
      <div className="ni-sec">
        <div className="nib-hero">
          <div className="c acc"><div className="l">Calories left</div><div className="big">1,060<span className="u"> kcal</span></div><div className="sub">1,620 / 2,680</div></div>
          <div className="c"><div className="l">Protein to go</div><div className="big">66<span className="u">g</span></div><div className="sub">134 / 200g</div></div>
        </div>
        <div className="nib-tl">
          <div className="nib-node"><div className="dot"></div><div className="tm">07:30 · Breakfast</div><div className="hd"><span className="nm">Oats &amp; whey</span><span className="kc">490</span></div><div className="its">36g protein</div></div>
          <div className="nib-node"><div className="dot"></div><div className="tm">12:45 · Lunch</div><div className="hd"><span className="nm">Chicken &amp; rice</span><span className="kc">760</span></div><div className="its">58g protein</div></div>
          <div className="nib-node now"><div className="dot"></div><div className="tm" style={{color:"var(--ios-accent)"}}>Now · 3:42 PM</div><div className="hd"><span className="nm">Yogurt &amp; honey</span><span className="kc">176</span></div><div className="its">17g protein</div></div>
          <div className="nib-node future"><div className="dot"></div><div className="tm">Planned · Dinner</div><div className="hd"><span className="nm" style={{color:"var(--ios-label3)"}}>~1,060 to target</span></div><div className="cta">+ Log dinner →</div></div>
        </div>
      </div>
    </IosWrap>
  );
}

function IosDirC() {
  return (
    <IosWrap>
      <div className="ni-sec" style={{paddingTop:8}}>
        <div className="nic-mast"><div className="date">Tuesday · May 27</div><h2>The Daily Plate</h2></div>
        <div className="nic-fig">
          <div className="nic-ring"><Ring size={104} stroke={7} value={0.6} color="var(--ios-accent)" track="var(--ios-fill)"/><div className="ctr"><div className="v">60%</div><div className="l">of target</div></div></div>
          <div className="nic-dek"><span className="drop">1,060</span>kcal &amp; 66g protein still to go.</div>
        </div>
        <div className="nic-macros">
          <div className="nic-mrow"><span className="nm">Protein</span><div className="ba"><div className="f" style={{width:"67%"}}></div></div><span className="va">134<span style={{fontSize:10,color:"var(--ios-label3)"}}>/200</span></span></div>
          <div className="nic-mrow"><span className="nm">Carbs</span><div className="ba"><div className="f" style={{width:"56%"}}></div></div><span className="va">168<span style={{fontSize:10,color:"var(--ios-label3)"}}>/300</span></span></div>
          <div className="nic-mrow"><span className="nm">Fat</span><div className="ba"><div className="f" style={{width:"64%"}}></div></div><span className="va">51<span style={{fontSize:10,color:"var(--ios-label3)"}}>/80</span></span></div>
        </div>
        <div className="nic-mh">Logged today</div>
        {MEALS.map(m => (
          <div className="nic-entry" key={m.type}>
            <div className="eh"><span className="nm">{m.type}</span><span className="tm">{m.at}</span><span className="kc">{m.kcal}</span></div>
            <div className="its">{m.items.join(" · ")}</div>
          </div>
        ))}
        <div className="nic-entry empty"><div className="eh"><span className="nm">Dinner</span><span className="tm">—</span></div><div className="its"><span className="add">+ Compose dinner</span></div></div>
      </div>
    </IosWrap>
  );
}

// ============ ENTRY STATE (track vs create plan) ============
function WebEntry() {
  return (
    <WebFrame title="Nutrition">
      <div style={{maxWidth:560,margin:"24px auto 0"}}>
        <div className="nw-kicker" style={{textAlign:"center"}}>Welcome to Nutrition</div>
        <h2 className="nw-serif" style={{fontSize:32,textAlign:"center",margin:"10px 0 6px"}}>How do you want to track?</h2>
        <p style={{textAlign:"center",color:"var(--color-text-secondary)",fontSize:14,margin:"0 auto 28px",maxWidth:420}}>First time here — pick a way to get started. You can switch anytime in settings.</p>
        <div className="entry-choice">
          <div className="entry-card primary">
            <div className="ek">Recommended</div>
            <div className="eh">Flexible tracking</div>
            <div className="ed">Log meals freely as you eat — search, scan a barcode, or snap a photo. Add as many meals a day as you like. No setup.</div>
            <div className="ar">Start tracking <ArrowR s={14}/></div>
          </div>
          <div className="entry-card">
            <div className="ek">Structured</div>
            <div className="eh">Create a meal plan</div>
            <div className="ed">Build a daily template with a set number of meals and macro targets, then log against it each day.</div>
            <div className="ar" style={{color:"var(--color-accent)"}}>Build a plan <ArrowR s={14}/></div>
          </div>
        </div>
      </div>
    </WebFrame>
  );
}
function IosEntry() {
  return (
    <IosWrap>
      <div className="ni-head"><div className="ni-kicker">Welcome to Nutrition</div><h1 className="ni-title">How do you want to track?</h1></div>
      <div className="ni-sec">
        <p style={{color:"var(--ios-label2)",fontSize:14,margin:"4px 0 18px"}}>First time here — pick a way to get started. Switch anytime.</p>
        <div className="ni-entry">
          <div className="ni-ecard primary"><div className="ek">Recommended</div><div className="eh">Flexible tracking</div><div className="ed">Log freely — search, scan, or snap a photo. Add as many meals as you like.</div></div>
          <div className="ni-ecard"><div className="ek">Structured</div><div className="eh">Create a meal plan</div><div className="ed">Set a daily template with target meals and macros.</div></div>
        </div>
      </div>
    </IosWrap>
  );
}

// ============ ADD-MEAL FLOW ============
const FOODS = [
  { nm: "Chicken breast, grilled", meta: "USDA · per 100g", kc: 165 },
  { nm: "Whey isolate, vanilla", meta: "Optimum · per scoop", kc: 117 },
  { nm: "Greek yogurt, 2%", meta: "Fage · per 100g", kc: 65 },
  { nm: "Jasmine rice, cooked", meta: "USDA · per 100g", kc: 130 },
  { nm: "Banana, raw", meta: "USDA · per 100g", kc: 89 },
];
function WebAddMeal() {
  return (
    <WebFrame title="Add to lunch" crumb="Nutrition ›" action={<button className="btn sm secondary">Cancel</button>}>
      <div className="aw-search" style={{maxWidth:560}}>
        <SearchI s={20}/><input placeholder="Search foods, brands, recents…" defaultValue="chicken"/>
      </div>
      <div style={{display:"flex",gap:18,marginTop:18,borderBottom:"1px solid var(--color-border)"}}>
        {["Search","Scan barcode","Photo"].map((t,i)=>(
          <button key={t} style={{background:"none",border:"none",padding:"8px 0",borderBottom:i===0?"1.5px solid var(--color-text)":"1.5px solid transparent",marginBottom:-1,fontSize:12,textTransform:"uppercase",letterSpacing:"0.08em",fontWeight:600,color:i===0?"var(--color-text)":"var(--color-text-secondary)"}}>{t}</button>
        ))}
      </div>
      <div style={{marginTop:8,maxWidth:560}}>
        {FOODS.map(f => (
          <div key={f.nm} style={{display:"grid",gridTemplateColumns:"1fr auto auto",gap:16,alignItems:"center",padding:"14px 0",borderBottom:"1px solid var(--color-border)"}}>
            <div><div style={{fontSize:14,fontWeight:500}}>{f.nm}</div><div style={{fontSize:11,color:"var(--color-text-tertiary)",marginTop:2}}>{f.meta}</div></div>
            <div className="nw-num" style={{fontSize:15}}>{f.kc}<span style={{fontSize:11,color:"var(--color-text-tertiary)",fontFamily:"var(--font-sans)"}}> kcal</span></div>
            <div style={{width:30,height:30,borderRadius:999,border:"1px solid var(--color-text)",display:"grid",placeItems:"center"}}><PlusI s={15}/></div>
          </div>
        ))}
      </div>
    </WebFrame>
  );
}
function IosAddMeal() {
  return (
    <div style={{height:"100%",position:"relative",background:"var(--ios-bg)"}}>
      <div className="ni-head" style={{opacity:0.4}}><div className="ni-kicker">Tuesday · May 27</div><h1 className="ni-title">Today</h1></div>
      <div className="ni-sheet">
        <div className="grab"></div>
        <div className="sh"><h3>Add to lunch</h3><span style={{color:"var(--ios-accent)",fontSize:15,fontWeight:600}}>Cancel</span></div>
        <div className="tabs"><button className="on">Search</button><button>Scan</button><button>Photo</button></div>
        <div className="body">
          <div className="ni-sb"><SearchI s={17}/><span className="ph">Search foods, brands…</span></div>
          <div style={{marginTop:8}}>
            {FOODS.map(f => (
              <div className="ni-fr" key={f.nm}>
                <div><div className="nm">{f.nm}</div><div className="meta">{f.meta}</div></div>
                <div className="kc">{f.kc}<span style={{fontSize:10,color:"var(--ios-label3)",fontFamily:"var(--ios-sans)"}}> kcal</span></div>
                <div className="add"><PlusI s={14}/></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ TRENDS (day/week) ============
const WEEK = [
  { d: "M", v: 92, kc: "2,480" }, { d: "T", v: 78, kc: "2,090", under: true }, { d: "W", v: 100, kc: "2,680" },
  { d: "T", v: 108, kc: "2,900", over: true }, { d: "F", v: 95, kc: "2,540" }, { d: "S", v: 88, kc: "2,360", under: true }, { d: "S", v: 60, kc: "1,620", today: true },
];
function WebTrends() {
  return (
    <WebFrame title="Trends" crumb="Nutrition" action={<button className="btn sm">Export</button>}>
      <div className="tw-toggle"><button>Day</button><button className="on">Week</button><button>Month</button></div>
      <div style={{position:"relative"}}>
        <div className="tw-week">
          <div className="tw-target-line" style={{bottom:"calc(26px + 70%)"}}></div>
          {WEEK.map((w,i)=>(
            <div className="tw-bar" key={i}>
              <div className={"col"+(w.under?" under":w.over?" over":w.today?"":"")} style={{height:`${w.v*0.62}%`,background:w.today?"var(--color-accent)":undefined}}></div>
              <div className="dl">{w.d}</div>
            </div>
          ))}
        </div>
        <div className="nw-kicker" style={{position:"absolute",right:0,top:"calc(30% - 8px)",fontSize:10}}>Target 2,680</div>
      </div>
      <div className="tw-stats">
        <div className="tw-stat"><div className="l">Avg / day</div><div className="v">2,381</div><div className="d">−299 vs target</div></div>
        <div className="tw-stat"><div className="l">Avg protein</div><div className="v">186g</div><div className="d">93% of goal</div></div>
        <div className="tw-stat"><div className="l">Days on target</div><div className="v">5<span style={{fontSize:16,color:"var(--color-text-tertiary)"}}>/7</span></div><div className="d">within ±10%</div></div>
        <div className="tw-stat"><div className="l">Cut adherence</div><div className="v">86<span style={{fontSize:16,color:"var(--color-text-tertiary)"}}>%</span></div><div className="d">on plan</div></div>
      </div>
    </WebFrame>
  );
}
function IosTrends() {
  return (
    <IosWrap>
      <div className="ni-head"><div className="ni-kicker">Last 7 days</div><h1 className="ni-title">Trends</h1></div>
      <div className="ni-sec">
        <div className="nit-toggle"><button>Day</button><button className="on">Week</button><button>Month</button></div>
        <div className="nit-week">
          {WEEK.map((w,i)=>(
            <div className="nit-bar" key={i}>
              <div className={"col"+(w.under?" under":w.over?" over":"")} style={{height:`${w.v*0.62}%`,background:w.today?"var(--ios-accent)":undefined}}></div>
              <div className="dl">{w.d}</div>
            </div>
          ))}
        </div>
        <div className="nit-stats">
          <div className="nit-stat"><div className="l">Avg / day</div><div className="v">2,381</div><div className="d">−299 vs target</div></div>
          <div className="nit-stat"><div className="l">Avg protein</div><div className="v">186g</div><div className="d">93% of goal</div></div>
          <div className="nit-stat"><div className="l">On target</div><div className="v">5/7</div><div className="d">within ±10%</div></div>
          <div className="nit-stat"><div className="l">Adherence</div><div className="v">86%</div><div className="d">on plan</div></div>
        </div>
      </div>
    </IosWrap>
  );
}

Object.assign(window, {
  WebDirA, WebDirB, WebDirC, IosDirA, IosDirB, IosDirC,
  WebEntry, IosEntry, WebAddMeal, IosAddMeal, WebTrends, IosTrends,
});
