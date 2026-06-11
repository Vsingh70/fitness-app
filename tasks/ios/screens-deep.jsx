// iOS deep screens: Active workout, Per-exercise, Workout summary
// Exports: ScreenActiveIOS, ScreenExerciseIOS, ScreenSummaryIOS

function ScreenActiveIOS() {
  return (
    <div style={{ overflow: 'auto', height: '100%', paddingBottom: 110 }}>
      {/* Custom header (in-workout) */}
      <CompactNav
        leading={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)', fontSize: 17, padding: 0, display: 'inline-flex', alignItems: 'center' }}>
          <IconChevronL size={16} stroke={2.4}/> Pause
        </button>}
        title={<span className="ios-rounded num" style={{ fontWeight: 700, fontSize: 17 }}>14:32</span>}
        trailing={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-red)', fontSize: 17, fontWeight: 600, padding: 0 }}>Finish</button>}
      />

      {/* Title block */}
      <div style={{ padding: '0 20px 12px' }}>
        <div className="ios-caption" style={{ color: 'var(--ios-blue)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em' }}>Push A · Week 4</div>
        <h2 className="ios-rounded" style={{ fontSize: 26, fontWeight: 700, margin: '4px 0 4px', letterSpacing: '-0.02em' }}>Exercise 1 of 5</h2>
        <div className="ios-footnote">5 of 17 sets complete</div>
      </div>

      {/* Exercise pill rail */}
      <div style={{ display: 'flex', gap: 6, overflowX: 'auto', padding: '0 20px 16px' }}>
        {[
          { n: 'Bench Press', a: 1, d: 2, t: 4 },
          { n: 'OHP', d: 0, t: 4 },
          { n: 'Incline DB', d: 0, t: 3 },
          { n: 'Lateral', d: 0, t: 3 },
          { n: 'Pushdown', d: 0, t: 3 },
        ].map((e, i) => (
          <div key={i} style={{
            flexShrink: 0, padding: '6px 12px', borderRadius: 999,
            background: e.a ? 'var(--ios-label)' : 'transparent',
            color: e.a ? 'var(--ios-bg)' : (e.d === e.t ? 'var(--ios-accent)' : 'var(--ios-label2)'),
            border: e.a ? '1px solid var(--ios-label)' : '1px solid var(--ios-sep)',
            fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>{e.n} · {e.d}/{e.t}</div>
        ))}
      </div>

      {/* Active exercise card */}
      <div style={{ padding: '0 20px' }}>
        <div className="ios-card" style={{ padding: '16px 16px 12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="ios-rounded" style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>Barbell Bench Press</div>
              <div className="ios-caption" style={{ marginTop: 2 }}>4 × 6–8 @ RPE 8 · rest 3:00</div>
            </div>
            <button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)' }}>
              <Icon d="M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14M21 19l-4-4M3 19l4-4" size={20}/>
            </button>
          </div>

          {/* Plate math */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 3,
            padding: '10px 0 14px', borderBottom: '0.5px solid var(--ios-sep)',
          }}>
            <span style={{ width: 4, height: 14, background: 'var(--ios-label2)', borderRadius: 1 }}/>
            {[20,20,5].map((p, i) => <span key={'l'+i} style={{
              width: 10 + p/2, height: 8 + p*1.4, background: p === 20 ? 'var(--ios-label)' : 'var(--ios-label2)',
              color: 'var(--ios-bg)', fontFamily: 'var(--ios-serif)', fontWeight: 500, fontSize: 9,
              display: 'grid', placeItems: 'center', borderRadius: 2,
            }}>{p}</span>)}
            <span style={{ width: 32, height: 6, background: 'var(--ios-label2)', borderRadius: 1 }}/>
            <span style={{ width: 32, height: 6, background: 'var(--ios-label2)', borderRadius: 1 }}/>
            {[5,20,20].map((p, i) => <span key={'r'+i} style={{
              width: 10 + p/2, height: 8 + p*1.4, background: p === 20 ? 'var(--ios-label)' : 'var(--ios-label2)',
              color: 'var(--ios-bg)', fontFamily: 'var(--ios-serif)', fontWeight: 500, fontSize: 9,
              display: 'grid', placeItems: 'center', borderRadius: 2,
            }}>{p}</span>)}
            <span style={{ width: 4, height: 14, background: 'var(--ios-label2)', borderRadius: 1 }}/>
            <span className="ios-mono ios-caption-2" style={{ marginLeft: 8 }}>92.5 kg · ea 36.25</span>
          </div>

          {/* Set rows */}
          {[
            { i: 1, w: '92.5', r: '8', rpe: '7.5', done: true },
            { i: 2, w: '92.5', r: '8', rpe: '8', done: true },
            { i: 3, w: '92.5', r: '', rpe: '', current: true, prev: '92.5 × 7' },
            { i: 4, w: '92.5', r: '', rpe: '' },
          ].map((s) => (
            <div key={s.i} style={{
              display: 'grid', gridTemplateColumns: '28px 80px 1fr 1fr 50px 28px',
              gap: 8, alignItems: 'center',
              padding: '8px 0',
              borderRadius: 8, marginTop: 4,
              background: s.done ? 'var(--ios-fill)' : (s.current ? 'var(--ios-accent-soft)' : 'transparent'),
              paddingLeft: s.done || s.current ? 8 : 0,
              paddingRight: s.done || s.current ? 8 : 0,
            }}>
              <span className="ios-rounded num" style={{ fontWeight: 700, fontSize: 15, color: 'var(--ios-label2)', textAlign: 'center' }}>{s.i}</span>
              <span className="ios-caption num" style={{ color: 'var(--ios-label3)' }}>{s.prev || '92.5 × 8'}</span>
              <div style={{
                height: 36, borderRadius: 8,
                background: s.done ? 'transparent' : 'var(--ios-fill)',
                border: s.current ? '1.5px solid var(--ios-accent)' : '1px solid var(--ios-sep)',
                display: 'grid', placeItems: 'center',
                fontFamily: '"SF Pro Rounded"', fontWeight: 600, fontSize: 17, fontVariantNumeric: 'tabular-nums',
                color: s.done ? 'var(--ios-green)' : 'var(--ios-label)',
              }}>{s.w}</div>
              <div style={{
                height: 36, borderRadius: 8,
                background: s.done ? 'transparent' : 'var(--ios-fill)',
                border: s.current ? '1.5px solid var(--ios-accent)' : '1px solid var(--ios-sep)',
                display: 'grid', placeItems: 'center',
                fontFamily: '"SF Pro Rounded"', fontWeight: 600, fontSize: 17, fontVariantNumeric: 'tabular-nums',
                color: s.done ? 'var(--ios-green)' : 'var(--ios-label)',
              }}>{s.r || '–'}</div>
              <span className="ios-rounded num" style={{ fontWeight: 600, fontSize: 13, color: s.done ? 'var(--ios-label2)' : 'var(--ios-label3)', textAlign: 'center' }}>{s.rpe || '–'}</span>
              <div style={{
                width: 26, height: 26, borderRadius: 13,
                background: s.done ? 'var(--ios-green)' : 'transparent',
                border: s.done ? 'none' : '1.5px solid var(--ios-label3)',
                display: 'grid', placeItems: 'center',
                color: 'white',
              }}>
                {s.done && <IconCheckmark size={14}/>}
              </div>
            </div>
          ))}

          <button style={{
            marginTop: 8, width: '100%',
            padding: '10px', border: '1px dashed var(--ios-label3)',
            borderRadius: 10, color: 'var(--ios-label2)',
            background: 'transparent', fontSize: 14, fontFamily: 'inherit',
          }}>+ Add set</button>
        </div>
      </div>

      {/* Sticky rest bar (positioned at bottom above tabbar-style nav) */}
      <div style={{
        position: 'absolute', bottom: 32, left: 16, right: 16,
        background: 'color-mix(in oklab, var(--ios-bg2) 90%, transparent)',
        backdropFilter: 'blur(20px) saturate(140%)',
        WebkitBackdropFilter: 'blur(20px) saturate(140%)',
        borderRadius: 14,
        padding: '10px 14px',
        display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 12, alignItems: 'center',
        boxShadow: '0 6px 20px rgba(0,0,0,0.10)',
        border: '0.5px solid var(--ios-sep)',
      }} className="rest-bar">
        <div style={{ position: 'relative', width: 44, height: 44 }}>
          <ActivityRing size={44} stroke={4} value={0.42} color="var(--ios-accent)"/>
          <div style={{
            position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
            fontFamily: '"SF Pro Rounded"', fontWeight: 700, fontSize: 14, fontVariantNumeric: 'tabular-nums',
          }}>1:43</div>
        </div>
        <div>
          <div className="ios-headline" style={{ fontSize: 14 }}>Resting</div>
          <div className="ios-caption">1:43 of 3:00 · auto-started</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="ios-btn sm gray" style={{ padding: '0 10px' }}>+30s</button>
          <button className="ios-btn sm tonal">Skip</button>
        </div>
      </div>
    </div>
  );
}

function ScreenExerciseIOS() {
  return (
    <div style={{ overflow: 'auto', height: '100%', paddingBottom: 40 }}>
      <CompactNav
        leading={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)', fontSize: 17, padding: 0, display: 'inline-flex', alignItems: 'center' }}>
          <IconChevronL size={16} stroke={2.4}/> Exercises
        </button>}
        title=""
        trailing={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)' }}>
          <Icon d="M12 5v14M5 12h14" size={20} stroke={2.2}/>
        </button>}
      />

      {/* Hero header */}
      <div style={{ padding: '8px 24px 20px', borderBottom: '1px solid var(--ios-sep)' }}>
        <div className="ios-caption" style={{ color: 'var(--ios-blue)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em' }}>Compound · barbell</div>
        <h1 className="ios-rounded" style={{ fontSize: 30, fontWeight: 700, margin: '4px 0 10px', letterSpacing: '-0.025em' }}>Barbell Bench Press</h1>
        <div className="pill-stack">
          <span className="ios-chip tonal">Chest</span>
          <span className="ios-chip">Triceps</span>
          <span className="ios-chip">Front delts</span>
        </div>
      </div>

      {/* PR tiles */}
      <div style={{ padding: '0 20px 18px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <StatTile label="e1RM" value="120.4" unit="kg" delta="+1.9 kg · PR" deltaCls="up"/>
          <StatTile label="Best set" value="95 × 8" delta="May 23"/>
          <StatTile label="All-time" value="100 × 5" delta="Apr 11"/>
          <StatTile label="Volume / wk" value="2,940" unit="kg" delta="↑ 8%" deltaCls="up"/>
        </div>
      </div>

      {/* Recommendation strip */}
      <div style={{ padding: '0 20px 18px' }}>
        <div className="ios-card" style={{ padding: 14, background: 'var(--ios-accent-soft)' }}>
          <div className="ios-headline" style={{ color: 'var(--ios-accent)' }}>Try 97.5 kg next session</div>
          <div className="ios-footnote" style={{ marginTop: 4 }}>
            Double-progression rule fired — every working set hit top of range at RPE ≤ 9.
          </div>
          <button className="ios-btn sm tonal" style={{ marginTop: 10 }}>Apply to today</button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ padding: '0 20px 12px', display: 'flex', justifyContent: 'center' }}>
        <div className="ios-segmented" style={{ width: '100%', maxWidth: 360, display: 'flex' }}>
          <button className="on" style={{ flex: 1 }}>Trends</button>
          <button style={{ flex: 1 }}>Sets</button>
          <button style={{ flex: 1 }}>Variants</button>
          <button style={{ flex: 1 }}>Notes</button>
        </div>
      </div>

      {/* Chart card */}
      <div style={{ padding: '0 20px 18px' }}>
        <div className="ios-card" style={{ padding: 16 }}>
          <div className="ios-caption" style={{ fontWeight: 600 }}>Estimated 1RM · 6 months</div>
          <div className="ios-rounded num" style={{ fontSize: 28, fontWeight: 700, marginTop: 2 }}>
            120.4 <span style={{ fontSize: 14, color: 'var(--ios-label2)', fontWeight: 500 }}>kg</span>
          </div>
          <div className="ios-footnote" style={{ color: 'var(--ios-green)' }}>↑ 14.2 kg vs Dec</div>
          <svg viewBox="0 0 320 140" style={{ width: '100%', display: 'block', marginTop: 12 }} preserveAspectRatio="none">
            <defs>
              <linearGradient id="exg" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor="var(--ios-blue)" stopOpacity="0.30"/>
                <stop offset="1" stopColor="var(--ios-blue)" stopOpacity="0"/>
              </linearGradient>
            </defs>
            {[30,70,110].map(y => <line key={y} x1="0" y1={y} x2="320" y2={y} stroke="var(--ios-sep)" strokeDasharray="2 2"/>)}
            <path d="M 0 115 L 30 110 L 60 104 L 90 98 L 120 92 L 150 84 L 180 75 L 210 64 L 240 50 L 270 38 L 300 25 L 320 16 L 320 140 L 0 140 Z" fill="url(#exg)"/>
            <path d="M 0 115 L 30 110 L 60 104 L 90 98 L 120 92 L 150 84 L 180 75 L 210 64 L 240 50 L 270 38 L 300 25 L 320 16" fill="none" stroke="var(--ios-blue)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="320" cy="16" r="4.5" fill="var(--ios-blue)" stroke="var(--ios-bg2)" strokeWidth="2"/>
            <circle cx="300" cy="25" r="4" fill="var(--ios-gold)" stroke="var(--ios-bg2)" strokeWidth="2"/>
          </svg>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
            <span className="ios-caption-2 num">DEC</span>
            <span className="ios-caption-2 num">JAN</span>
            <span className="ios-caption-2 num">FEB</span>
            <span className="ios-caption-2 num">MAR</span>
            <span className="ios-caption-2 num">APR</span>
            <span className="ios-caption-2 num">MAY</span>
          </div>
        </div>
      </div>

      {/* Volume chart */}
      <div style={{ padding: '0 20px 18px' }}>
        <div className="ios-card" style={{ padding: 16 }}>
          <div className="ios-caption" style={{ fontWeight: 600 }}>Working set volume · last 11 sessions</div>
          <svg viewBox="0 0 320 100" style={{ width: '100%', display: 'block', marginTop: 10 }} preserveAspectRatio="none">
            {[
              { x: 4, h: 28 }, { x: 33, h: 38 }, { x: 62, h: 44 }, { x: 91, h: 55 },
              { x: 120, h: 64 }, { x: 149, h: 70 }, { x: 178, h: 76 }, { x: 207, h: 82 },
              { x: 236, h: 86, pr: false }, { x: 265, h: 92 }, { x: 294, h: 96, pr: true },
            ].map((b, i) => (
              <rect key={i} x={b.x} y={100 - b.h} width="22" height={b.h} rx="3" fill={b.pr ? 'var(--ios-gold)' : 'var(--ios-blue)'} opacity={b.pr ? 1 : 0.7}/>
            ))}
          </svg>
        </div>
      </div>

      <div style={{ padding: '0 20px 32px' }}>
        <button className="ios-btn"><IconPlay size={16}/> Start session with bench</button>
      </div>
    </div>
  );
}

function ScreenSummaryIOS() {
  return (
    <div style={{ overflow: 'auto', height: '100%', paddingBottom: 40 }}>
      <CompactNav
        leading={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)', fontSize: 17, padding: 0 }}>Workouts</button>}
        title="Summary"
        trailing={<button style={{ background: 'transparent', border: 'none', color: 'var(--ios-blue)' }}>
          <IconShare size={20}/>
        </button>}
      />

      {/* PR banner */}
      <div style={{ padding: '0 20px 18px' }}>
        <div style={{ borderTop: '2px solid var(--ios-label)', paddingTop: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--ios-accent)' }}>
            <IconStar size={16}/>
            <span className="ios-kicker" style={{ color: 'var(--ios-accent)' }}>2 personal records</span>
          </div>
          <div className="ios-rounded" style={{ fontSize: 30, marginTop: 8, letterSpacing: '-0.015em' }}>Bench &amp; OHP up</div>
          <div className="ios-footnote" style={{ marginTop: 8 }}>Bench 95 × 8 · e1RM 120.4 kg (+1.9)</div>
        </div>
      </div>

      {/* Stat tiles */}
      <div style={{ padding: '0 20px 18px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <StatTile label="Duration" value="58" unit="min"/>
          <StatTile label="Sets" value="21"/>
          <StatTile label="Tonnage" value="5,125" unit="kg" delta="↑ 240 vs avg" deltaCls="up"/>
          <StatTile label="Avg RPE" value="8.2" delta="On target"/>
        </div>
      </div>

      {/* Volume by muscle (mini) */}
      <div style={{ padding: '0 20px 18px' }}>
        <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
          <span>Volume by muscle</span>
          <span className="more">vs typical</span>
        </div>
        <div className="ios-card" style={{ padding: 16 }}>
          {[
            { nm: 'Chest', sets: 9, target: 7, pct: 100 },
            { nm: 'Front delts', sets: 7, target: 6, pct: 88 },
            { nm: 'Side delts', sets: 3, target: 4, pct: 60, short: true },
            { nm: 'Triceps', sets: 6, target: 6, pct: 75 },
          ].map(r => (
            <div key={r.nm} style={{ display: 'grid', gridTemplateColumns: '90px 1fr auto', gap: 10, alignItems: 'center', padding: '6px 0' }}>
              <span className="ios-subhead">{r.nm}</span>
              <div style={{ position: 'relative', height: 6, background: 'var(--ios-fill)', borderRadius: 999, overflow: 'visible' }}>
                <div style={{ height: '100%', width: r.pct + '%', background: r.short ? 'var(--ios-orange)' : 'var(--ios-blue)', borderRadius: 999 }}/>
                <div style={{ position: 'absolute', top: -2, bottom: -2, width: 2, left: (r.target / r.sets * r.pct) + '%', background: 'var(--ios-label3)' }}/>
              </div>
              <span className="ios-caption num">{r.sets} / {r.target}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sets list (per exercise) */}
      <div style={{ padding: '0 20px 18px' }}>
        <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
          <span>Sets</span>
          <span className="more">5 exercises · 21 sets</span>
        </div>
        <div className="ios-list">
          {[
            { nm: 'Bench Press', sets: '95 × 8 PR · 92.5 × 8 · 92.5 × 7 · 85 × 9' },
            { nm: 'Overhead Press', sets: '57.5 × 9 PR · 55 × 9 · 55 × 8' },
            { nm: 'Incline DB Press', sets: '32 × 12 · 32 × 11 · 32 × 10' },
          ].map(e => (
            <div key={e.nm} className="ios-row" style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'flex-start', padding: '12px 16px' }}>
              <div>
                <div className="ios-headline">{e.nm}</div>
                <div className="ios-caption num" style={{ marginTop: 4 }}>{e.sets}</div>
              </div>
              <IconChevron size={14}/>
            </div>
          ))}
        </div>
      </div>

      {/* Next session recs */}
      <div style={{ padding: '0 20px 32px' }}>
        <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
          <span>Next Push A</span>
          <span className="more">3 recs</span>
        </div>
        <div className="ios-list">
          <Row icon={<IconArrow size={14}/>} iconBg="blue" title="Bench → 97.5 kg" detail={<span className="ios-caption">+ progression</span>} chevron/>
          <Row icon={<Icon d="M12 4v16" size={14}/>} iconBg="green" title="OHP → hold 57.5" detail={<span className="ios-caption">repeat top</span>} chevron/>
          <Row icon={<IconPlus size={14}/>} iconBg="orange" title="Side delts +1 set" detail={<span className="ios-caption">below target</span>} chevron last/>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ScreenActiveIOS, ScreenExerciseIOS, ScreenSummaryIOS });
