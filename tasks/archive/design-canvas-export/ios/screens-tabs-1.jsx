// iOS tab screens: Today, Workouts, Nutrition
// Exports: ScreenTodayIOS, ScreenWorkoutsIOS, ScreenNutritionIOS

// ===== Today =====
function ScreenTodayIOS() {
  const stats = [
    { id: 'r', label: 'Readiness', value: '78', sub: 'High · push it', icon: <IconHeart size={16}/>, color: 'var(--ios-green)', ringValue: 0.78 },
    { id: 's', label: 'Sleep', value: '7h 24m', sub: '↑ 22 min', icon: <IconMoon size={16}/>, color: 'var(--ios-indigo)' },
    { id: 'h', label: 'Resting HR', value: '56', unit: 'bpm', sub: '↓ 2', icon: <IconHeart size={16}/>, color: 'var(--ios-red)' },
    { id: 'v', label: 'HRV', value: '64', unit: 'ms', sub: '↑ 8 ms', icon: <IconBolt2 size={16}/>, color: 'var(--ios-pink)' },
    { id: 'st', label: 'Steps', value: '4,287', sub: '43% of goal', icon: <IconFoot size={16}/>, color: 'var(--ios-blue)', ringValue: 0.43 },
    { id: 'a', label: 'Active min', value: '32 / 60', sub: '↑ 8', icon: <IconTimer size={16}/>, color: 'var(--ios-green)' },
    { id: 'k', label: 'Calories', value: '2,140', unit: 'kcal', sub: '1,720 BMR', icon: <IconFlame size={16}/>, color: 'var(--ios-orange)' },
    { id: 'sp', label: 'SpO₂', value: '97', unit: '%', sub: 'Normal', icon: <IconDrop size={16}/>, color: 'var(--ios-mint)' },
  ];
  return (
    <>
      <div style={{ padding: '8px 0 100px', overflow: 'auto', height: '100%' }}>
        <LargeTitle title="Today" subtitle="Tuesday, 27 May" trailing={
          <div style={{
            width: 38, height: 38, borderRadius: 19,
            border: '1px solid var(--ios-label)',
            color: 'var(--ios-label)', display: 'grid', placeItems: 'center',
            fontFamily: 'var(--ios-serif)', fontWeight: 500, fontSize: 14,
          }}>AC</div>
        }/>

        {/* Fitbit carousel */}
        <div style={{ padding: '0 20px 6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="ios-footnote" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--ios-green)', boxShadow: '0 0 0 3px rgba(52,199,89,0.18)' }}/>
            Fitbit · synced 2m ago
          </span>
          <span className="ios-caption">Hold to reorder</span>
        </div>
        <div style={{ display: 'flex', gap: 10, overflowX: 'auto', padding: '0 20px 16px', scrollSnapType: 'x mandatory' }}>
          {stats.map(s => (
            <div key={s.id} style={{ flex: '0 0 142px', scrollSnapAlign: 'start' }}>
              <div className="stat-tile" style={{ padding: 14, border: '1px solid var(--ios-sep)', borderRadius: 3 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--ios-label2)', display: 'inline-flex' }}>{s.icon}</span>
                  {s.ringValue !== undefined ? (
                    <ActivityRing size={28} stroke={3} value={s.ringValue} color="var(--ios-accent)"/>
                  ) : null}
                </div>
                <div className="lab" style={{ marginTop: 8, fontSize: 12 }}>{s.label}</div>
                <div className="v" style={{ fontSize: 22, marginTop: 2 }}>
                  {s.value}{s.unit && <span className="u">{s.unit}</span>}
                </div>
                <div className="ios-caption-2" style={{ color: (s.sub.includes('↓') || s.sub.includes('↑')) ? 'var(--ios-accent)' : 'var(--ios-label2)' }}>{s.sub}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Nutrition strip */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-card" style={{ padding: '16px', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'center' }}>
            <div className="ios-ring" style={{ width: 76, height: 76 }}>
              <ActivityRing size={76} stroke={6} value={0.6} color="var(--ios-accent)"/>
              <div className="num">
                <span className="ios-rounded" style={{ fontSize: 18, fontWeight: 700 }}>1,620</span>
                <span className="ios-caption-2">/ 2,680</span>
              </div>
            </div>
            <div>
              <div className="ios-caption" style={{ textTransform: 'uppercase', letterSpacing: '.05em', fontWeight: 600 }}>Nutrition · today</div>
              <div className="ios-headline" style={{ marginTop: 2 }}>1,060 kcal remaining</div>
              <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                <span style={{ fontSize: 12 }}><b className="num">134</b> <span className="label2">P</span></span>
                <span style={{ fontSize: 12 }}><b className="num">168</b> <span className="label2">C</span></span>
                <span style={{ fontSize: 12 }}><b className="num">51</b> <span className="label2">F</span></span>
              </div>
            </div>
          </div>
        </div>

        {/* Scheduled workout */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div style={{ borderTop: '2px solid var(--ios-label)', paddingTop: 14 }}>
            <div className="ios-kicker">Today — Push A · Week 4</div>
            <div className="ios-rounded" style={{ fontSize: 34, lineHeight: 1.04, marginTop: 8 }}>Bench, press &amp; pump</div>
            <div className="ios-footnote" style={{ marginTop: 10, display: 'flex', gap: 16 }}>
              <span><span className="num" style={{ color: 'var(--ios-label)', fontWeight: 600 }}>5</span> exercises</span>
              <span><span className="num" style={{ color: 'var(--ios-label)', fontWeight: 600 }}>~58</span> min</span>
              <span><span className="num" style={{ color: 'var(--ios-label)', fontWeight: 600 }}>21</span> sets</span>
            </div>
            <button className="ios-btn" style={{ marginTop: 16, width: '100%' }}>
              <IconPlay size={15}/> Start workout
            </button>
          </div>
        </div>

        {/* Recommendation */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>Recommendations</span>
            <span className="more">See all</span>
          </div>
          <div className="ios-card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{
                width: 26, color: 'var(--ios-accent)',
                display: 'grid', placeItems: 'start center', flexShrink: 0, paddingTop: 2,
              }}><IconArrow size={20}/></div>
              <div style={{ flex: 1 }}>
                <div className="ios-caption" style={{ textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 600, color: 'var(--ios-accent)' }}>Add weight</div>
                <div className="ios-headline" style={{ marginTop: 2 }}>Try 95 kg on bench</div>
                <div className="ios-footnote" style={{ marginTop: 4, lineHeight: 1.4 }}>
                  8 / 8 / 7 reps @ RPE 7.5–9 last session. Top of range.
                </div>
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  {[1,2,3].map(i => <span key={i} style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--ios-accent)' }}/>)}
                  <span className="ios-caption-2" style={{ marginLeft: 4 }}>High confidence</span>
                </div>
              </div>
              <button className="ios-btn sm tonal" style={{ flexShrink: 0 }}>Apply</button>
            </div>
          </div>
        </div>

        <div style={{ padding: '0 20px 32px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>This week</span>
            <span className="more">Insights</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <StatTile label="Sessions" value="5/6" delta="↑ on pace" deltaCls="up"/>
            <StatTile label="Sets" value="96" delta="↑ 11" deltaCls="up"/>
            <StatTile label="Tonnage" value="23k" unit="kg" delta="↑ 6%" deltaCls="up"/>
          </div>
        </div>
      </div>
      <TabBar active="today"/>
    </>
  );
}

// ===== Workouts =====
function ScreenWorkoutsIOS() {
  const days = [
    { dow: 'M', d: 26, tag: 'Legs', done: true },
    { dow: 'T', d: 27, tag: 'Push', today: true },
    { dow: 'W', d: 28, tag: 'Pull' },
    { dow: 'T', d: 29, tag: 'Rest', rest: true },
    { dow: 'F', d: 30, tag: 'Push' },
    { dow: 'S', d: 31, tag: 'Legs' },
    { dow: 'S', d: 1, tag: 'Rest', rest: true },
  ];
  const recent = [
    { date: 'Mon 26', day: 'Legs A', dur: '1:08', sets: 22, vol: '6,480 kg', prs: 1 },
    { date: 'Sat 24', day: 'Pull A', dur: '0:55', sets: 19, vol: '4,220 kg' },
    { date: 'Fri 23', day: 'Push A', dur: '0:58', sets: 21, vol: '5,125 kg', prs: 2 },
    { date: 'Wed 21', day: 'Legs B', dur: '1:12', sets: 24, vol: '6,740 kg' },
    { date: 'Tue 20', day: 'Pull B', dur: '0:54', sets: 20, vol: '4,380 kg', prs: 1 },
  ];
  return (
    <>
      <div style={{ padding: '8px 0 100px', overflow: 'auto', height: '100%' }}>
        <LargeTitle title="Workouts" trailing={
          <button style={{
            width: 38, height: 38, borderRadius: 19,
            background: 'transparent', color: 'var(--ios-label)',
            border: '1px solid var(--ios-label)', display: 'grid', placeItems: 'center',
          }}><IconPlus size={18} stroke={1.6}/></button>
        }/>

        {/* Week strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, padding: '0 16px 18px' }}>
          {days.map(d => (
            <div key={d.dow + d.d} style={{
              padding: '8px 0 10px', borderRadius: 2, textAlign: 'center',
              background: d.today ? 'var(--ios-label)' : 'transparent',
              color: d.today ? 'var(--ios-bg)' : (d.done ? 'var(--ios-accent)' : (d.rest ? 'var(--ios-label3)' : 'var(--ios-label)')),
              border: d.today ? 'none' : '1px solid var(--ios-sep)',
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, opacity: 0.7, textTransform: 'uppercase' }}>{d.dow}</div>
              <div className="ios-rounded" style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>{d.d}</div>
              <div style={{ fontSize: 9, marginTop: 4, opacity: 0.85, fontWeight: 600 }}>{d.tag}</div>
            </div>
          ))}
        </div>

        {/* Today scheduled */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>Today · scheduled</span>
            <span className="more">Reschedule</span>
          </div>
          <div className="ios-card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="ios-caption" style={{ textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 600, color: 'var(--ios-accent)' }}>Push A · Week 4</div>
                <div className="ios-rounded" style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>Push A</div>
                <div className="ios-footnote" style={{ marginTop: 4 }}>5 exercises · ~58 min · 21 sets</div>
              </div>
            </div>
            <button className="ios-btn" style={{ marginTop: 14 }}><IconPlay size={16}/> Start workout</button>
          </div>
        </div>

        {/* Completed */}
        <div className="ios-section" style={{ padding: '0 20px 32px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>This week</span>
            <span className="more">Calendar</span>
          </div>
          <div className="ios-list">
            {recent.map((r, i) => (
              <div key={i} className={"ios-row " + (i === 0 ? "" : "")} style={{ gridTemplateColumns: 'auto 1fr auto auto' }}>
                <div style={{
                  width: 30, display: 'grid', placeItems: 'center',
                  color: 'var(--ios-label)',
                }}>
                  <IconDumbbell size={20}/>
                </div>
                <div>
                  <div className="ios-headline">{r.day}</div>
                  <div className="ios-caption">{r.date} · {r.sets} sets · {r.dur} · {r.vol}</div>
                </div>
                {r.prs && <span className="ios-chip tonal orange"><IconStar size={10}/> {r.prs} PR</span>}
                <IconChevron size={14}/>
              </div>
            ))}
          </div>
        </div>
      </div>
      <TabBar active="workouts"/>
    </>
  );
}

// ===== Nutrition =====
function ScreenNutritionIOS() {
  const meals = [
    { type: 'Breakfast', at: '07:30', items: 3, kcal: 490, p: 36 },
    { type: 'Lunch', at: '12:45', items: 3, kcal: 760, p: 58 },
    { type: 'Snack', at: '15:10', items: 2, kcal: 176, p: 17 },
    { type: 'Dinner', at: '—', items: 0, kcal: 0, p: 0 },
  ];
  return (
    <>
      <div style={{ padding: '8px 0 100px', overflow: 'auto', height: '100%' }}>
        <LargeTitle title="Nutrition" trailing={
          <button style={{
            width: 38, height: 38, borderRadius: 19,
            background: 'transparent', color: 'var(--ios-label)',
            border: '1px solid var(--ios-label)', display: 'grid', placeItems: 'center',
          }}><IconPlus size={18} stroke={1.6}/></button>
        }/>

        {/* Hero ring */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-card" style={{ padding: 18, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div className="ios-ring" style={{ width: 124, height: 124 }}>
              <TripleRing size={124} stroke={10} rings={[
                { value: 0.6, color: 'var(--ios-orange)' },
                { value: 0.67, color: 'var(--ios-blue)' },
                { value: 0.56, color: 'var(--ios-green)' },
              ]}/>
              <div className="num">
                <div className="ios-rounded" style={{ fontSize: 26, fontWeight: 700, lineHeight: 1 }}>1,620</div>
                <div className="ios-caption-2" style={{ marginTop: 4 }}>/ 2,680 kcal</div>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              {[
                { l: 'Protein', v: '134g', target: '/ 200', pct: 67, color: 'var(--ios-blue)' },
                { l: 'Carbs', v: '168g', target: '/ 300', pct: 56, color: 'var(--ios-orange)' },
                { l: 'Fat', v: '51g', target: '/ 80', pct: 64, color: 'var(--ios-green)' },
              ].map(m => (
                <div key={m.l} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span className="label2">{m.l}</span>
                    <span className="num"><b>{m.v}</b> <span className="label2">{m.target}</span></span>
                  </div>
                  <div style={{ height: 4, background: 'var(--ios-fill)', borderRadius: 999, marginTop: 4, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: m.pct + '%', background: m.color, borderRadius: 999 }}/>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Meals */}
        <div className="ios-section" style={{ padding: '0 20px 32px' }}>
          {meals.map(m => (
            <div key={m.type} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '0 4px 6px' }}>
                <div>
                  <div className="ios-rounded" style={{ fontSize: 18, fontWeight: 700 }}>{m.type}</div>
                  <div className="ios-caption">{m.at}</div>
                </div>
                <div className="ios-caption num">
                  {m.items === 0 ? '—' : `${m.kcal} kcal · ${m.p}p`}
                </div>
              </div>
              <div className="ios-card" style={{ padding: m.items === 0 ? 14 : 0 }}>
                {m.items === 0 ? (
                  <button className="ios-btn gray-tonal" style={{ width: '100%', height: 40, fontSize: 14 }}>
                    <IconPlus size={16}/> Add to {m.type.toLowerCase()}
                  </button>
                ) : (
                  <>
                    {m.type === 'Breakfast' && <>
                      <Row icon={<IconStar size={14}/>} iconBg="orange" title="Oats, rolled" detail={<span className="num">304 kcal</span>}/>
                      <Row icon={<IconBarcode size={14}/>} iconBg="indigo" title="Whey isolate" detail={<span className="num">117 kcal</span>}/>
                      <Row icon={<IconStar size={14}/>} iconBg="purple" title="Blueberries" detail={<span className="num">69 kcal</span>} last/>
                    </>}
                    {m.type === 'Lunch' && <>
                      <Row icon={<IconCamera size={14}/>} iconBg="green" title="Chicken thigh" detail={<span className="num">410 kcal</span>}/>
                      <Row icon={<IconStar size={14}/>} iconBg="yellow" title="Jasmine rice" detail={<span className="num">234 kcal</span>}/>
                      <Row title="Greens + olive oil" detail={<span className="num">116 kcal</span>} last/>
                    </>}
                    {m.type === 'Snack' && <>
                      <Row icon={<IconBarcode size={14}/>} iconBg="indigo" title="Greek yogurt" detail={<span className="num">130 kcal</span>}/>
                      <Row title="Honey" detail={<span className="num">46 kcal</span>} last/>
                    </>}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <TabBar active="nutrition"/>
    </>
  );
}

Object.assign(window, { ScreenTodayIOS, ScreenWorkoutsIOS, ScreenNutritionIOS });
