// Programs redesign — screens for the side-by-side canvas.
// Mock: Alex Chen · PPL — Vanilla 6-day · Week 4 of 8 · Push A today.

// ---- icons ----
const ArrowR = ({ s = 16 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>;
const PlayI = ({ s = 16 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor"><path d="M6 4l14 8-14 8z"/></svg>;
const GripI = ({ s = 14 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="6" r="1.4"/><circle cx="15" cy="6" r="1.4"/><circle cx="9" cy="12" r="1.4"/><circle cx="15" cy="12" r="1.4"/><circle cx="9" cy="18" r="1.4"/><circle cx="15" cy="18" r="1.4"/></svg>;
const TrashI = ({ s = 15 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13M10 11v6M14 11v6"/></svg>;
const CheckI = ({ s = 14 }) => <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5 10-12"/></svg>;

// ---- data ----
const WEEK_DAYS = [
  { dow: "Mon", nm: "Legs A", mus: "Quads · hams · glutes", ex: 5, st: "Done", done: true },
  { dow: "Tue", nm: "Push A", mus: "Chest · delts · triceps", ex: 5, st: "Today", today: true },
  { dow: "Wed", nm: "Pull A", mus: "Back · biceps · rear delts", ex: 5, st: "Planned" },
  { dow: "Thu", nm: "Rest", mus: "Recovery", rest: true },
  { dow: "Fri", nm: "Push B", mus: "Incline focus · shoulders", ex: 5, st: "Planned" },
  { dow: "Sat", nm: "Legs B", mus: "Posterior chain", ex: 5, st: "Planned" },
];
const PUSH_A = [
  { nm: "Barbell Bench Press", mus: "Chest", sets: 4, reps: "6–8", rpe: "7–8", rest: "3:00", prog: "+2.5 kg — hit top of range", tag: "Compound" },
  { nm: "Overhead Press", mus: "Front delts", sets: 4, reps: "8–10", rpe: "7–9", rest: "2:30", prog: "Hold 57.5 kg", tag: "Compound" },
  { nm: "Incline DB Press", mus: "Upper chest", sets: 3, reps: "10–12", rpe: "8–9", rest: "2:00", prog: "Add a rep", tag: "" },
  { nm: "Cable Lateral Raise", mus: "Side delts", sets: 3, reps: "12–15", rpe: "8–10", rest: "1:30", prog: "+1 set this week", tag: "" },
  { nm: "Rope Triceps Pushdown", mus: "Triceps", sets: 3, reps: "12–15", rpe: "8–10", rest: "1:15", prog: "Same load", tag: "" },
];
const TEMPLATES = [
  { dl: "Push / Pull / Legs", nm: "PPL — Vanilla 6-day", de: "The default. Two of each session a week, double progression in 6–12 rep ranges.", wk: 8, fr: "6×", users: "4.6k", active: true, cat: "Hypertrophy" },
  { dl: "Upper / Lower", nm: "UL — 4-day", de: "Balanced upper and lower split. Friendly to busier weeks.", wk: 8, fr: "4×", users: "3.2k", cat: "Hypertrophy" },
  { dl: "Wendler", nm: "5/3/1 — Beyond", de: "Powerbuilding template with optional FSL assistance.", wk: 12, fr: "4×", users: "2.8k", cat: "Strength" },
  { dl: "Bodybuilding split", nm: "Arnold Split", de: "Chest+back · shoulders+arms · legs, twice a week. High volume.", wk: 8, fr: "6×", users: "1.5k", cat: "Hypertrophy" },
  { dl: "Full body", nm: "3× Full Body", de: "Minimum-effective-dose template. Great for cuts.", wk: 6, fr: "3×", users: "2.1k", cat: "General" },
  { dl: "Hybrid", nm: "Lift × Run — 5-day", de: "Two lifts, two runs, one cross-train. Endurance focus.", wk: 10, fr: "5×", users: "820", cat: "Endurance" },
];
const TPL_DAYS = [
  { nm: "Legs A", ex: [["Back Squat","4×5–7"],["RDL","3×8–10"],["Leg Press","3×10–12"],["Leg Curl","3×12–15"],["Calf Raise","3×10–12"]] },
  { nm: "Push A", ex: [["Bench Press","4×6–8"],["Overhead Press","4×8–10"],["Incline DB","3×10–12"],["Cable Lateral","3×12–15"],["Pushdown","3×12–15"]] },
  { nm: "Pull A", ex: [["Pull-Up","4×AMRAP"],["Barbell Row","4×6–8"],["Cable Row","3×10–12"],["Face Pull","3×15–20"],["Incline Curl","3×8–10"]] },
  { nm: "Push B", ex: [["Incline Bench","4×6–8"],["DB Shoulder","3×10–12"],["Dips","3×8–10"],["Reverse Pec","3×12–15"],["OH Triceps","3×10–12"]] },
  { nm: "Legs B", ex: [["Front Squat","4×6–8"],["Hip Thrust","3×8–10"],["Bulgarian SS","3×8–10"],["Seated Calf","3×12–15"],["Plank","3×45s"]] },
  { nm: "Pull B", ex: [["Lat Pulldown","4×8–10"],["Chest-Sup Row","3×10–12"],["DB Pullover","3×10–12"],["Rear Delt Fly","3×12–15"],["Hammer Curl","3×10–12"]] },
];

// programs library (multiple programs + active)
const PROGRAMS = [
  { nm: "PPL — Vanilla 6-day", meta: "Week 4 of 8 · hypertrophy · 6×/wk", active: true },
  { nm: "Cut block — UL 4-day", meta: "Last run Feb 12 · completed", active: false },
  { nm: "PR Peak — 5/3/1", meta: "Archived Sep 2025", active: false, archived: true },
];

// ============ WEB CHROME ============
function WebFrame({ title, crumb = "Programs", children, action }) {
  return (
    <div className="web-frame">
      <div className="web-rail">
        <div className="mk">g</div>
        <div className="ic">▦</div><div className="ic">◴</div>
        <div className="ic on">≣</div><div className="ic">✦</div>
        <div style={{ marginTop: "auto" }} className="ic">⚙</div>
      </div>
      <div className="web-main">
        <div className="web-topbar">
          <span className="crumb">{crumb}</span>
          <h1>{title}</h1>
          <span className="sp"></span>
          {action}
        </div>
        <div className="pw-wrap">{children}</div>
      </div>
    </div>
  );
}
const Meso = () => (
  <div className="meso">
    <div className="wk done"></div><div className="wk done"></div><div className="wk done"></div>
    <div className="wk now"></div><div className="wk"></div><div className="wk"></div><div className="wk"></div>
    <div className="wk deload" title="Deload"></div>
  </div>
);

// ============ ONBOARDING ============
function WebOnboard() {
  return (
    <WebFrame title="Programs">
      <div className="ow-wrap">
        <div className="pw-kicker" style={{textAlign:"center"}}>Welcome to Programs</div>
        <h2 className="pw-serif" style={{fontSize:32,textAlign:"center",margin:"10px 0 6px"}}>How do you want to train?</h2>
        <p style={{textAlign:"center",color:"var(--color-text-secondary)",fontSize:14,margin:"0 auto 28px",maxWidth:430}}>First time here — start from a proven template, or build your own from scratch. You can switch anytime.</p>
        <div className="ow-choice">
          <div className="ow-card primary">
            <div className="ek">Recommended</div>
            <div className="eh">Follow a template</div>
            <div className="ed">Pick a proven program — PPL, Upper/Lower, 5/3/1 and more. Copy it, tweak if you like, and start this week.</div>
            <div className="ar">Browse templates <ArrowR s={14}/></div>
          </div>
          <div className="ow-card">
            <div className="ek">Full control</div>
            <div className="eh">Build your own program</div>
            <div className="ed">Compose days, exercises, set/rep schemes and a progression strategy from a blank slate.</div>
            <div className="ar" style={{color:"var(--color-accent)"}}>Start building <ArrowR s={14}/></div>
          </div>
        </div>
      </div>
    </WebFrame>
  );
}
function IosOnboard() {
  return (
    <div className="pi-wrap">
      <div className="pi-head"><div className="pi-kicker">Welcome to Programs</div><h1 className="pi-title">How do you want to train?</h1></div>
      <div className="pi-sec">
        <p style={{color:"var(--ios-label2)",fontSize:14,margin:"4px 0 18px"}}>Start from a proven template, or build your own. Switch anytime.</p>
        <div className="pi-entry">
          <div className="pi-ecard primary"><div className="ek">Recommended</div><div className="eh">Follow a template</div><div className="ed">PPL, Upper/Lower, 5/3/1 and more. Copy, tweak, and start this week.</div></div>
          <div className="pi-ecard"><div className="ek">Full control</div><div className="eh">Build your own</div><div className="ed">Compose days, exercises and progression from scratch.</div></div>
        </div>
      </div>
    </div>
  );
}

// ============ DIRECTION A — TRAINING SPINE (web) ============
function WebDirA() {
  return (
    <WebFrame title="Programs" action={<button className="btn sm secondary">Edit</button>}>
      <div className="aw-mast">
        <div className="row">
          <div>
            <div className="pw-kicker">Active program</div>
            <div className="ti">PPL — Vanilla 6-day</div>
          </div>
          <div className="meta">
            <div className="m"><div className="v">Hypertrophy</div><div className="l">Goal</div></div>
            <div className="m"><div className="v">Double prog.</div><div className="l">Strategy</div></div>
            <div className="m"><div className="v">6×/wk</div><div className="l">Frequency</div></div>
          </div>
        </div>
        <div className="aw-meso-wrap">
          <div className="lab"><span>Mesocycle · Week 4 of 8</span><span>Week 8 deload</span></div>
          <Meso/>
        </div>
      </div>

      <div className="aw-today">
        <div>
          <div className="k">Today · Tuesday</div>
          <div className="d">Push A</div>
          <div className="ex">Bench · Overhead Press · Incline DB · Cable Lateral · Triceps · 5 exercises · ~58 min</div>
        </div>
        <button className="btn lg"><PlayI/> Start</button>
      </div>

      <div className="aw-week">
        <div className="aw-week-h"><span className="t">This week</span><span className="pw-link">Full calendar</span></div>
        {WEEK_DAYS.map(d => (
          <div className={"aw-day " + (d.done?"done":d.today?"today":d.rest?"rest":"")} key={d.dow}>
            <span className="dow">{d.dow}</span>
            <div><div className="nm">{d.nm}</div><div className="mus">{d.mus}</div></div>
            <span className="cnt">{d.ex ? `${d.ex} ex` : ""}</span>
            <span className="st">{d.st || ""}</span>
          </div>
        ))}
      </div>

      <div className="aw-progs">
        <div className="aw-week-h"><span className="t">My programs</span><span className="pw-link">+ New program</span></div>
        {PROGRAMS.map(p => (
          <div className={"aw-prog-row " + (p.active?"active":"")} key={p.nm}>
            <div><div className="nm">{p.nm}</div><div className="meta">{p.meta}</div></div>
            {p.active
              ? <span className="act on">Active</span>
              : <span className="act link">{p.archived ? "Restore" : "Activate"}</span>}
            <button className="del" aria-label={"Delete " + p.nm}><TrashI/></button>
          </div>
        ))}
        <button className="aw-newprog">+ Create a new program</button>
      </div>
    </WebFrame>
  );
}
function IosDirA() {
  return (
    <div className="pi-wrap">
      <div className="pi-head"><div className="pi-kicker">Active program</div><h1 className="pi-title">Programs</h1></div>
      <div className="pi-sec">
        <div className="pia-mast">
          <div className="pw-kicker" style={{color:"var(--ios-label2)",fontSize:10}}>PPL — Vanilla 6-day</div>
          <div className="ti">Week 4 of 8</div>
          <div className="meta">
            <div><div className="v">Hypertrophy</div><div className="l">Goal</div></div>
            <div><div className="v">Double prog.</div><div className="l">Strategy</div></div>
            <div><div className="v">6×/wk</div><div className="l">Freq</div></div>
          </div>
          <div className="pi-meso"><div className="wk done"></div><div className="wk done"></div><div className="wk done"></div><div className="wk now"></div><div className="wk"></div><div className="wk"></div><div className="wk"></div><div className="wk deload"></div></div>
        </div>

        <div className="pia-today">
          <div className="k">Today · Tuesday</div>
          <div className="d">Push A</div>
          <div className="ex">5 exercises · ~58 min · 21 sets</div>
          <div className="btn"><PlayI s={15}/> Start workout</div>
        </div>

        <div className="pia-wh">This week</div>
        {WEEK_DAYS.map(d => (
          <div className={"pia-day " + (d.done?"done":d.today?"today":d.rest?"rest":"")} key={d.dow}>
            <span className="dow">{d.dow}</span>
            <div><div className="nm">{d.nm}</div><div className="mus">{d.mus}</div></div>
            <span className="st">{d.st || ""}</span>
          </div>
        ))}

        <div className="pia-wh" style={{marginTop:22}}>My programs</div>
        {PROGRAMS.map((p, i) => (
          i === 1 ? (
            <div className="pia-prog-swipe" key={p.nm}>
              <div className="del-rev"><TrashI s={16}/> Delete</div>
              <div className="pia-prog shifted">
                <div><div className="nm">{p.nm}</div><div className="meta">{p.meta}</div></div>
                <span className="act">Activate</span>
              </div>
            </div>
          ) : (
            <div className="pia-prog" key={p.nm}>
              <div><div className="nm">{p.nm}</div><div className="meta">{p.meta}</div></div>
              <span className={"act " + (p.active?"on":"")}>{p.active ? "Active" : p.archived ? "Restore" : "Activate"}</span>
            </div>
          )
        ))}
        <button className="pia-newprog">+ Create a new program</button>
        <div className="pia-swipe-hint">Swipe a program left to delete</div>
      </div>
    </div>
  );
}

// ============ DIRECTION B — MESOCYCLE GRID (web) ============
function WebDirB() {
  const plan = ["Legs A","Push A","Pull A","Push B","Legs B","Pull B"];
  const rows = [
    { wk: "W1", done: 6 }, { wk: "W2", done: 6 }, { wk: "W3", done: 6 },
    { wk: "W4", done: 1, now: 1 }, { wk: "W5", done: 0 }, { wk: "W6", done: 0 }, { wk: "W7", done: 0 },
  ];
  return (
    <WebFrame title="Programs" action={<button className="btn sm secondary">Edit</button>}>
      <div className="bw-head">
        <div><div className="pw-kicker">Active · PPL — Vanilla 6-day</div><div className="ti">The mesocycle</div></div>
        <button className="btn sm"><PlayI s={14}/> Today · Push A</button>
      </div>
      <div className="bw-grid">
        <div className="bw-grid-row head">
          <div className="cell">Week</div>
          {plan.map(p => <div className="cell" key={p}>{p}</div>)}
        </div>
        {rows.map((r, ri) => (
          <div className="bw-grid-row" key={r.wk}>
            <div className="cell wlab">{r.wk}</div>
            {plan.map((p, ci) => {
              const isDone = ci < r.done;
              const isNow = r.now && ci === r.done;
              return (
                <div className={"cell " + (isDone?"done":isNow?"now":"")} key={p}>
                  <div className="nm">{p.split(" ")[1] === "A" ? p.replace(" A","ᴬ") : p.replace(" B","ᴮ")}</div>
                  <div className="vol">{isDone? "✓" : isNow? "today" : "—"}</div>
                </div>
              );
            })}
          </div>
        ))}
        <div className="bw-grid-row">
          <div className="cell wlab" style={{color:"var(--color-text-tertiary)"}}>W8</div>
          {plan.map(p => <div className="cell deload-col" key={p}><div className="nm" style={{color:"var(--color-text-tertiary)"}}>deload</div></div>)}
        </div>
      </div>
      <div className="bw-legend">
        <span><span className="sw" style={{background:"var(--color-accent-soft)"}}></span> Completed</span>
        <span><span className="sw" style={{boxShadow:"inset 0 0 0 2px var(--color-accent)"}}></span> Today</span>
        <span><span className="sw" style={{background:"repeating-linear-gradient(45deg,transparent 0 4px,var(--color-surface) 4px 8px)",border:"1px solid var(--color-border)"}}></span> Deload</span>
      </div>
      <div className="bw-stats">
        <div className="bw-stat"><div className="l">Completed</div><div className="v">19<span style={{fontSize:15,color:"var(--color-text-tertiary)"}}>/48</span></div><div className="d">sessions</div></div>
        <div className="bw-stat"><div className="l">Adherence</div><div className="v">100<span style={{fontSize:15,color:"var(--color-text-tertiary)"}}>%</span></div><div className="d">weeks 1–3</div></div>
        <div className="bw-stat"><div className="l">Tonnage</div><div className="v">96k<span style={{fontSize:15,color:"var(--color-text-tertiary)"}}>kg</span></div><div className="d">↑ 6% / wk</div></div>
        <div className="bw-stat"><div className="l">PRs</div><div className="v">7</div><div className="d">this block</div></div>
      </div>
    </WebFrame>
  );
}
function IosDirB() {
  const plan = ["Legs A","Push A","Pull A"];
  const rows = [{ wk:"W1", done:3 },{ wk:"W2", done:3 },{ wk:"W3", done:3 },{ wk:"W4", done:1, now:1 },{ wk:"W5", done:0 }];
  return (
    <div className="pi-wrap">
      <div className="pi-head"><div className="pi-kicker">PPL — Vanilla 6-day</div><h1 className="pi-title" style={{fontSize:26}}>The mesocycle</h1></div>
      <div className="pi-sec">
        <div className="pib-grid">
          <div className="pib-row head"><div className="c">Wk</div>{plan.map(p=><div className="c" key={p}>{p}</div>)}</div>
          {rows.map(r=>(
            <div className="pib-row" key={r.wk}>
              <div className="c wl">{r.wk}</div>
              {plan.map((p,ci)=>{
                const done=ci<r.done, now=r.now&&ci===r.done;
                return <div className={"c "+(done?"done":now?"now":"")} key={p}><div className="nm">{done?"✓":now?"now":"—"}</div></div>;
              })}
            </div>
          ))}
        </div>
        <div style={{fontSize:11,color:"var(--ios-label3)",marginTop:8}}>Showing days 1–3 · scroll for Push B / Legs B / Pull B</div>
        <div className="pib-stats">
          <div className="pib-stat"><div className="l">Completed</div><div className="v">19/48</div></div>
          <div className="pib-stat"><div className="l">Adherence</div><div className="v">100%</div></div>
          <div className="pib-stat"><div className="l">Tonnage</div><div className="v">96k kg</div></div>
          <div className="pib-stat"><div className="l">PRs</div><div className="v">7</div></div>
        </div>
      </div>
    </div>
  );
}

// ============ DIRECTION C — EDITORIAL BRIEF (web) ============
function WebDirC() {
  return (
    <WebFrame title="Programs" crumb="The Brief" action={<button className="btn sm secondary">Edit</button>}>
      <div className="cw-mast">
        <div><div className="date">Week 4 of 8 · Tuesday</div><h2>Push, Pull &amp; Legs</h2></div>
        <div className="ed">Vol. 4 · Accumulation<br/>Deload in 4 weeks</div>
      </div>
      <div className="cw-lead">
        <div>
          <div className="cw-dek"><span className="drop">PPL</span>is in its fourth week — volume is peaking before next week's overreach and the week-8 deload. Today is Push A.</div>
          <div className="cw-by">Double progression · 6×/week · hypertrophy</div>
          <div style={{marginTop:18}}><button className="btn"><PlayI s={14}/> Start Push A</button></div>
        </div>
        <div className="cw-side">
          <div className="cw-srow"><span className="l">Goal</span><span className="v">Hypertrophy</span></div>
          <div className="cw-srow"><span className="l">Progression</span><span className="v">Double</span></div>
          <div className="cw-srow"><span className="l">This week</span><span className="v">1 of 6 done</span></div>
          <div className="cw-srow"><span className="l">Tonnage</span><span className="v">23,180 kg</span></div>
          <div className="cw-srow"><span className="l">PRs · block</span><span className="v">7</span></div>
        </div>
      </div>
      <div className="cw-deck-h"><span className="t">The week ahead</span><span className="pw-link">Full calendar</span></div>
      <div className="cw-cols">
        {WEEK_DAYS.map(d => (
          <div className={"cw-card " + (d.today?"today":"")} key={d.dow}>
            <div className="dl">{d.dow}{d.today?" · today":d.done?" · done":""}</div>
            <div className="nm">{d.nm}</div>
            <div className="ex">{d.mus}</div>
          </div>
        ))}
      </div>
    </WebFrame>
  );
}
function IosDirC() {
  return (
    <div className="pi-wrap">
      <div className="pi-sec" style={{paddingTop:8}}>
        <div className="pic-mast"><div className="date">Week 4 of 8 · Tuesday</div><h2>Push, Pull &amp; Legs</h2></div>
        <div className="pic-dek"><span className="drop">PPL</span>is in its fourth week — volume peaks before the week-8 deload. Today is Push A.</div>
        <div className="pic-side">
          <div className="pic-srow"><span className="l">Goal</span><span className="v">Hypertrophy</span></div>
          <div className="pic-srow"><span className="l">Progression</span><span className="v">Double</span></div>
          <div className="pic-srow"><span className="l">This week</span><span className="v">1 of 6 done</span></div>
          <div className="pic-srow"><span className="l">PRs · block</span><span className="v">7</span></div>
        </div>
        <div className="pic-dh">The week ahead</div>
        {WEEK_DAYS.map(d => (
          <div className={"pic-card " + (d.today?"today":"")} key={d.dow}>
            <div className="dl">{d.dow}{d.today?" · today":d.done?" · done":""}</div>
            <div className="nm">{d.nm}</div>
            <div className="ex">{d.mus}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ BROWSE TEMPLATES ============
function WebTemplates() {
  return (
    <WebFrame title="Templates" crumb="Programs ›" action={<button className="btn sm">Build your own</button>}>
      <div className="tw-filters">
        {["All","Hypertrophy","Strength","Endurance","General"].map((t,i)=>(
          <button key={t} className={i===0?"on":""}>{t}</button>
        ))}
      </div>
      <div className="tw-gallery">
        {TEMPLATES.map(t => (
          <div className={"tw-tpl " + (t.active?"active":"")} key={t.nm}>
            <div className="dl">{t.dl}{t.active?" · active":""}</div>
            <div className="nm">{t.nm}</div>
            <div className="de">{t.de}</div>
            <div className="meta"><span><b>{t.wk}</b> weeks</span><span><b>{t.fr}</b>/week</span><span><b>{t.users}</b> users</span><span>{t.cat}</span></div>
          </div>
        ))}
      </div>
    </WebFrame>
  );
}
function IosTemplates() {
  return (
    <div className="pi-wrap">
      <div className="pi-head"><div className="pi-kicker">Programs ›</div><h1 className="pi-title">Templates</h1></div>
      <div className="pi-sec">
        <div className="pit-filters">{["All","Hypertrophy","Strength","Endurance"].map((t,i)=><button key={t} className={i===0?"on":""}>{t}</button>)}</div>
        {TEMPLATES.slice(0,5).map(t => (
          <div className={"pit-tpl " + (t.active?"active":"")} key={t.nm}>
            <div className="dl">{t.dl}{t.active?" · active":""}</div>
            <div className="nm">{t.nm}</div>
            <div className="de">{t.de}</div>
            <div className="meta"><span><b>{t.wk}</b> wk</span><span><b>{t.fr}</b>/wk</span><span><b>{t.users}</b> users</span></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ TEMPLATE DETAIL ============
function WebDetail() {
  return (
    <WebFrame title="PPL — Vanilla 6-day" crumb="Programs › Templates ›" action={<button className="btn sm">Use this template</button>}>
      <div className="dw-hero">
        <div className="dl">Template · Push / Pull / Legs</div>
        <h2>PPL — Vanilla 6-day</h2>
        <p>Standard PPL split with double-progression in 6–12 rep ranges. Two of each session per week; week 8 deload. For intermediate lifters comfortable with autoregulation.</p>
        <div className="dw-specs">
          <div className="s"><div className="v">8</div><div className="l">Weeks</div></div>
          <div className="s"><div className="v">6×</div><div className="l">Per week</div></div>
          <div className="s"><div className="v">Hypertrophy</div><div className="l">Goal</div></div>
          <div className="s"><div className="v">4.6 ★</div><div className="l">4,621 ran it</div></div>
        </div>
      </div>
      <div className="dw-days">
        {TPL_DAYS.map((d,i) => (
          <div className="dw-day" key={d.nm}>
            <div className="dl">Day {i+1}</div>
            <div className="nm">{d.nm}</div>
            {d.ex.map(([n,s]) => <div className="ex" key={n}><span>{n}</span><span className="sr">{s}</span></div>)}
          </div>
        ))}
      </div>
    </WebFrame>
  );
}
function IosDetail() {
  return (
    <div className="pi-wrap" style={{position:"relative",height:"100%"}}>
      <div className="pi-head" style={{paddingBottom:8}}><div className="pi-kicker">Templates ›</div></div>
      <div className="pi-sec" style={{paddingBottom:90}}>
        <div className="pid-hero">
          <div className="dl">Push / Pull / Legs</div>
          <h2>PPL — Vanilla 6-day</h2>
          <p>Double-progression in 6–12 rep ranges. Two of each session a week; week 8 deload.</p>
          <div className="pid-specs">
            <div><div className="v">8</div><div className="l">Weeks</div></div>
            <div><div className="v">6×</div><div className="l">Per week</div></div>
            <div><div className="v">4.6★</div><div className="l">4.6k ran</div></div>
          </div>
        </div>
        {TPL_DAYS.slice(0,4).map((d,i) => (
          <div className="pid-day" key={d.nm}>
            <div className="dl">Day {i+1}</div>
            <div className="nm">{d.nm}</div>
            {d.ex.slice(0,4).map(([n,s]) => <div className="ex" key={n}><span>{n}</span><span className="sr">{s}</span></div>)}
          </div>
        ))}
      </div>
      <div className="pid-cta">Use this template</div>
    </div>
  );
}

// ============ PER-DAY DETAIL ============
function WebPerDay() {
  return (
    <WebFrame title="Push A" crumb="Programs › PPL ›" action={<button className="btn sm"><PlayI s={14}/> Start workout</button>}>
      <div className="xw-hero">
        <div className="dl">Day 2 · Push · Week 4</div>
        <h2>Push A</h2>
        <div className="meta">5 exercises · 21 working sets · ~58 min · Chest · shoulders · triceps</div>
      </div>
      {PUSH_A.map((e,i) => (
        <div className="xw-ex" key={e.nm}>
          <div className="top">
            <span className="idx">{String(i+1).padStart(2,"0")}</span>
            <span className="nm">{e.nm}</span>
            <span className="tag">{e.tag || e.mus}</span>
          </div>
          <div className="scheme">
            <div className="c"><div className="v">{e.sets}</div><div className="l">Sets</div></div>
            <div className="c"><div className="v">{e.reps}</div><div className="l">Reps</div></div>
            <div className="c"><div className="v">{e.rpe}</div><div className="l">RPE</div></div>
            <div className="c"><div className="v">{e.rest}</div><div className="l">Rest</div></div>
          </div>
          <div className="prog">Progression — <b>{e.prog}</b></div>
        </div>
      ))}
    </WebFrame>
  );
}
function IosPerDay() {
  return (
    <div className="pi-wrap">
      <div className="pi-head" style={{paddingBottom:8}}><div className="pi-kicker">PPL ›</div></div>
      <div className="pi-sec">
        <div className="pix-hero">
          <div className="dl">Day 2 · Push · Week 4</div>
          <h2>Push A</h2>
          <div className="meta">5 exercises · 21 sets · ~58 min</div>
        </div>
        {PUSH_A.map((e,i) => (
          <div className="pix-ex" key={e.nm}>
            <div className="top"><span className="idx">{String(i+1).padStart(2,"0")}</span><span className="nm">{e.nm}</span></div>
            <div className="scheme">
              <div><div className="v">{e.sets}</div><div className="l">Sets</div></div>
              <div><div className="v">{e.reps}</div><div className="l">Reps</div></div>
              <div><div className="v">{e.rpe}</div><div className="l">RPE</div></div>
              <div><div className="v">{e.rest}</div><div className="l">Rest</div></div>
            </div>
            <div className="prog">Progression — <b>{e.prog}</b></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ BUILDER / EDITOR ============
// per-exercise builder config: rep-mode (range|target) + intensity TARGET value.
// The intensity MODE (rpe|rir|off) is a GLOBAL program setting — see INTENSITY_MODE.
const BUILD_EX = [
  { nm: "Barbell Bench Press", mus: "Chest", sets: 4, repMode: "range", reps: "6–8", iv: "8" },
  { nm: "Overhead Press", mus: "Front delts", sets: 4, repMode: "range", reps: "8–10", iv: "8" },
  { nm: "Incline DB Press", mus: "Upper chest", sets: 3, repMode: "target", reps: "12", iv: "9" },
  { nm: "Cable Lateral Raise", mus: "Side delts", sets: 3, repMode: "target", reps: "15", iv: "9" },
  { nm: "Rope Triceps Pushdown", mus: "Triceps", sets: 3, repMode: "range", reps: "12–15", iv: "9" },
];
function MiniSeg({ options, value, ios }) {
  return (
    <div className={ios ? "ios-mini-seg" : "mini-seg"}>
      {options.map(o => <span key={o.v} className={"ms " + (o.v === value ? "on" : "")}>{o.label}</span>)}
    </div>
  );
}
const REP_OPTS = [{ v: "range", label: "Range" }, { v: "target", label: "Target" }];
const INT_OPTS = [{ v: "rpe", label: "RPE" }, { v: "rir", label: "RIR" }, { v: "off", label: "Off" }];
const INTENSITY_MODE = "rpe"; // GLOBAL — program-level intensity tracking (rpe | rir | off)
const intLabel = (m) => m === "rpe" ? "RPE" : m === "rir" ? "RIR" : "Off";

function WebBuilder() {
  return (
    <WebFrame title="New program" crumb="Programs › Build ›" action={<><button className="btn sm secondary" style={{marginRight:8}}>Save draft</button><button className="btn sm">Save &amp; activate</button></>}>
      <div className="ew-grid">
        <div>
          <div className="pw-kicker" style={{marginBottom:10}}>Days</div>
          <div className="ew-days">
            {["Legs A","Push A","Pull A","Push B","Legs B","Pull B"].map((d,i) => (
              <div className={"ew-dtab " + (i===1?"on":"")} key={d}>
                <span className="gr"><GripI/></span><span className="nm">{d}</span><span className="ct">5</span>
              </div>
            ))}
            <div className="ew-dtab add">+ Add day</div>
          </div>
          <div style={{marginTop:20}} className="pw-kicker">Details</div>
          <div style={{marginTop:10,fontSize:13,color:"var(--color-text-secondary)",lineHeight:2}}>
            <div>Goal — <b style={{color:"var(--color-text)",fontFamily:"var(--font-serif)"}}>Hypertrophy</b></div>
            <div>Progression — <b style={{color:"var(--color-text)",fontFamily:"var(--font-serif)"}}>Double</b></div>
            <div>Weeks — <b style={{color:"var(--color-text)",fontFamily:"var(--font-serif)"}}>8</b></div>
          </div>
          <div style={{marginTop:18}} className="pw-kicker">Intensity tracking</div>
          <div style={{marginTop:8}}><MiniSeg options={INT_OPTS} value={INTENSITY_MODE}/></div>
          <div style={{marginTop:6,fontSize:11,color:"var(--color-text-tertiary)",lineHeight:1.5}}>Applies to every exercise in the program.</div>
        </div>
        <div className="ew-canvas">
          <div className="h"><span className="t">Push A</span><span className="pw-link">Reorder · dnd</span></div>
          {BUILD_EX.map(e => (
            <div className="ew-ex" key={e.nm}>
              <div className="ew-ex-top">
                <span className="gr"><GripI/></span>
                <span className="nm">{e.nm}</span>
                <span className="mus">· {e.mus}</span>
                <span className="del"><TrashI s={15}/></span>
              </div>
              <div className="ew-ctl">
                <div className="ew-cg">
                  <span className="lab">Sets</span>
                  <div className="body"><div className="ew-field">{e.sets}</div></div>
                </div>
                <div className="ew-cg">
                  <span className="lab">Reps</span>
                  <div className="body">
                    <MiniSeg options={REP_OPTS} value={e.repMode}/>
                    <div className="ew-field">{e.reps}</div>
                  </div>
                </div>
                {INTENSITY_MODE !== "off" && (
                  <div className="ew-cg">
                    <span className="lab">{intLabel(INTENSITY_MODE)} target</span>
                    <div className="body"><div className="ew-field">{e.iv}</div></div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <button className="ew-add">+ Add exercise to Push A</button>
        </div>
      </div>
    </WebFrame>
  );
}
function IosBuilder() {
  return (
    <div className="pi-wrap">
      <div className="pi-head" style={{paddingBottom:8}}><div className="pi-kicker">Build ›</div><h1 className="pi-title" style={{fontSize:26}}>New program</h1></div>
      <div className="pi-sec">
        <div className="pie-drail">
          {["Legs A","Push A","Pull A","Push B","+ Day"].map((d,i)=><div className={"pie-dtab "+(i===1?"on":"")} key={d}>{d}</div>)}
        </div>
        <div className="pie-global">
          <div><div className="lab">Intensity tracking</div><div className="sub">Whole program</div></div>
          <MiniSeg options={INT_OPTS} value={INTENSITY_MODE} ios/>
        </div>
        <div style={{display:"flex",alignItems:"baseline",justifyContent:"space-between",margin:"16px 0 4px",borderBottom:"1px solid var(--ios-label)",paddingBottom:5}}>
          <span style={{fontFamily:"var(--ios-serif)",fontSize:19}}>Push A</span>
          <span style={{fontSize:10,textTransform:"uppercase",letterSpacing:"0.08em",color:"var(--ios-accent)",fontWeight:600}}>Drag to reorder</span>
        </div>
        {BUILD_EX.map(e => (
          <div className="pie-ex" key={e.nm}>
            <div className="pie-ex-top">
              <span className="gr"><GripI/></span>
              <span className="nm">{e.nm}</span>
              <span className="mus">· {e.mus}</span>
            </div>
            <div className="pie-ctl">
              <div className="pie-cg">
                <span className="lab">Sets</span>
                <div className="body"><div className="pie-field">{e.sets}</div></div>
              </div>
              <div className="pie-cg">
                <span className="lab">Reps</span>
                <div className="body">
                  <MiniSeg options={REP_OPTS} value={e.repMode} ios/>
                  <div className="pie-field">{e.reps}</div>
                </div>
              </div>
              {INTENSITY_MODE !== "off" && (
                <div className="pie-cg">
                  <span className="lab">{intLabel(INTENSITY_MODE)}</span>
                  <div className="body"><div className="pie-field">{e.iv}</div></div>
                </div>
              )}
            </div>
          </div>
        ))}
        <button className="pie-add">+ Add exercise</button>
      </div>
    </div>
  );
}

Object.assign(window, {
  WebOnboard, IosOnboard, WebDirA, IosDirA, WebDirB, IosDirB, WebDirC, IosDirC,
  WebTemplates, IosTemplates, WebDetail, IosDetail, WebPerDay, IosPerDay, WebBuilder, IosBuilder,
});
