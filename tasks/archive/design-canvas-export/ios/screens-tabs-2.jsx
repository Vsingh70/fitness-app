// iOS tab screens: Insights, Settings
// Exports: ScreenInsightsIOS, ScreenSettingsIOS

const MUSCLES_IOS = ["chest","front_delts","side_delts","rear_delts","traps","mid_back","lats","lower_back","biceps","triceps","forearms","abs","obliques","glutes","quads","hamstrings","adductors","abductors","calves"];

function muscleLevel(s, t) {
  if (!s || !t) return 0;
  const r = s / t;
  if (r >= 1.2) return 4;
  if (r >= 0.9) return 3;
  if (r >= 0.6) return 2;
  if (r > 0) return 1;
  return 0;
}

function ScreenInsightsIOS() {
  const v = window.MOCK?.volume_week || {};
  return (
    <>
      <div style={{ padding: '8px 0 100px', overflow: 'auto', height: '100%' }}>
        <LargeTitle title="Insights" trailing={
          <div className="ios-segmented">
            <button>1w</button>
            <button className="on">4w</button>
            <button>3m</button>
          </div>
        }/>

        {/* Top stats */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <StatTile label="Sessions / wk" value="5.2" delta="↑ 0.8" deltaCls="up"/>
            <StatTile label="Sets / wk" value="96" delta="↑ 11" deltaCls="up"/>
            <StatTile label="Tonnage / wk" value="23,180" unit="kg" delta="↑ 6%" deltaCls="up"/>
            <StatTile label="PRs · block" value="7" delta="↑ 3" deltaCls="up"/>
          </div>
        </div>

        {/* Volume heat */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>Volume by muscle</span>
            <span className="more">7 days</span>
          </div>
          <div className="ios-card" style={{ padding: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
              {MUSCLES_IOS.map(m => {
                const d = v[m] || { sets: 0, target: 0 };
                const lvl = muscleLevel(d.sets, d.target);
                return (
                  <div key={m} className={"ios-muscle-cell h" + lvl}>
                    <span className="nm">{m.replace("_", " ")}</span>
                    <span className="v">{d.sets}</span>
                  </div>
                );
              })}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, padding: '0 4px' }}>
              <span className="ios-caption-2">Tile = sets vs target</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span className="ios-caption-2">Less</span>
                {[0,1,2,3,4].map(i => <span key={i} style={{ width: 12, height: 12, borderRadius: 3, background: ['var(--ios-fill)','color-mix(in oklab, var(--ios-accent) 16%, transparent)','color-mix(in oklab, var(--ios-accent) 34%, transparent)','color-mix(in oklab, var(--ios-accent) 62%, transparent)','var(--ios-accent)'][i] }}/>)}
                <span className="ios-caption-2">More</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tonnage trend */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>Tonnage trend</span>
            <span className="more">8 weeks</span>
          </div>
          <div className="ios-card" style={{ padding: 16 }}>
            <div className="ios-rounded num" style={{ fontSize: 34, fontWeight: 500, letterSpacing: '-0.02em' }}>
              23,180 <span style={{ fontSize: 14, color: 'var(--ios-label2)', fontWeight: 500 }}>kg / wk</span>
            </div>
            <div className="ios-caption" style={{ color: 'var(--ios-green)', marginBottom: 8 }}>↑ 6% vs prior 4 weeks</div>
            <svg viewBox="0 0 320 100" style={{ width: '100%', display: 'block', marginTop: 4 }} preserveAspectRatio="none">
              <defs>
                <linearGradient id="ggrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0" stopColor="var(--ios-blue)" stopOpacity="0.25"/>
                  <stop offset="1" stopColor="var(--ios-blue)" stopOpacity="0"/>
                </linearGradient>
              </defs>
              <path d="M 0 78 L 40 70 L 80 60 L 120 55 L 160 47 L 200 38 L 240 30 L 280 18 L 320 10 L 320 100 L 0 100 Z" fill="url(#ggrad)"/>
              <path d="M 0 78 L 40 70 L 80 60 L 120 55 L 160 47 L 200 38 L 240 30 L 280 18 L 320 10" fill="none" stroke="var(--ios-blue)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="320" cy="10" r="4" fill="var(--ios-blue)" stroke="var(--ios-bg2)" strokeWidth="2"/>
            </svg>
          </div>
        </div>

        {/* Insights cards */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>This week</span>
            <span className="more">4 cards</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { kind: 'PR streak', title: 'Three PRs this week', body: 'Bench, OHP, Bulgarian split squat all moved up.', color: 'var(--ios-green)' },
              { kind: 'Plateau', title: 'Pull-ups stuck at 9 reps', body: 'Three sessions. Try a BW deload or rest-pause.', color: 'var(--ios-blue)' },
              { kind: 'Under recovered', title: 'Sleep dipped this week', body: 'Average 6.4h vs 7.5h baseline.', color: 'var(--ios-orange)' },
            ].map((c, i) => (
              <div key={i} style={{ padding: '2px 0 2px 14px', borderLeft: `2px solid ${c.color}` }}>
                <div className="ios-caption" style={{ color: c.color, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>{c.kind}</div>
                <div className="ios-headline" style={{ marginTop: 2 }}>{c.title}</div>
                <div className="ios-footnote" style={{ marginTop: 4 }}>{c.body}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Progress photos teaser */}
        <div className="ios-section" style={{ padding: '0 20px 32px' }}>
          <div className="ios-section-h-large" style={{ padding: '0 0 8px' }}>
            <span>Progress photos</span>
            <span className="more">Compare</span>
          </div>
          <div className="ios-card" style={{ padding: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 10, alignItems: 'center' }}>
              <div className="ios-placeholder" style={{ aspectRatio: '3/4' }}>
                <div>
                  <div style={{ fontSize: 9, marginBottom: 6 }}>FRONT</div>
                  <div style={{ fontSize: 10 }}>13 WEEKS AGO</div>
                </div>
              </div>
              <IconArrow size={18} style={{ color: 'var(--ios-label3)' }}/>
              <div className="ios-placeholder" style={{ aspectRatio: '3/4' }}>
                <div>
                  <div style={{ fontSize: 9, marginBottom: 6 }}>FRONT</div>
                  <div style={{ fontSize: 10 }}>TODAY</div>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12, padding: '0 4px' }}>
              <span className="ios-caption">Bodyweight</span>
              <span className="ios-caption num" style={{ color: 'var(--ios-green)' }}>−3.8 kg · ↓ 4.6%</span>
            </div>
          </div>
        </div>
      </div>
      <TabBar active="insights"/>
    </>
  );
}

// ===== Settings =====
function ScreenSettingsIOS() {
  return (
    <>
      <div style={{ padding: '8px 0 100px', overflow: 'auto', height: '100%' }}>
        <LargeTitle title="Settings"/>

        {/* Profile card */}
        <div className="ios-section" style={{ padding: '0 20px 18px' }}>
          <div className="ios-card" style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 60, height: 60, borderRadius: 30,
              border: '1px solid var(--ios-label)',
              color: 'var(--ios-label)', display: 'grid', placeItems: 'center',
              fontFamily: 'var(--ios-serif)', fontWeight: 500, fontSize: 24,
            }}>AC</div>
            <div style={{ flex: 1 }}>
              <div className="ios-headline" style={{ fontSize: 20, fontWeight: 600 }}>Alex Chen</div>
              <div className="ios-footnote" style={{ marginTop: 2 }}>alex@chen.fyi · Apple ID</div>
            </div>
            <IconChevron size={14}/>
          </div>
        </div>

        {/* Appearance */}
        <div className="ios-section">
          <div className="ios-section-h">Appearance</div>
          <div className="ios-list">
            <Row icon={<IconStar size={14}/>} iconBg="purple" title="Accent color" accessory={
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {['#9D5635','#4C4A57','#4F6B63','#B07B3C','#99506A'].map((c, i) => (
                  <span key={i} style={{ width: 16, height: 16, borderRadius: 8, background: c, outline: i === 0 ? '1.5px solid var(--ios-label)' : 'none', outlineOffset: 2 }}/>
                ))}
                <IconChevron size={14}/>
              </div>
            }/>
            <Row icon={<IconMoon size={14}/>} iconBg="indigo" title="Appearance" accessory={
              <div className="ios-segmented">
                <button>Light</button>
                <button className="on">Auto</button>
                <button>Dark</button>
              </div>
            } last/>
          </div>
        </div>

        {/* Units */}
        <div className="ios-section">
          <div className="ios-section-h">Units</div>
          <div className="ios-list">
            <Row icon={<IconDumbbell size={14}/>} iconBg="orange" title="Weight" accessory={
              <div className="ios-segmented">
                <button className="on">kg</button>
                <button>lb</button>
              </div>
            }/>
            <Row icon={<IconFoot size={14}/>} iconBg="blue" title="Distance" accessory={
              <div className="ios-segmented">
                <button className="on">km</button>
                <button>mi</button>
              </div>
            } last/>
          </div>
        </div>

        {/* Training */}
        <div className="ios-section">
          <div className="ios-section-h">Training</div>
          <div className="ios-list">
            <Row icon={<IconList size={14}/>} iconBg="green" title="Active program" detail="PPL · W4" chevron/>
            <Row icon={<IconTimer size={14}/>} iconBg="pink" title="Default rest" detail="2:00" chevron/>
            <Row icon={<IconBolt size={14}/>} iconBg="yellow" title="Plate set" detail="25/20/15/10/5/2.5" chevron last/>
          </div>
        </div>

        {/* Connections */}
        <div className="ios-section">
          <div className="ios-section-h">Connected services</div>
          <div className="ios-list">
            <Row icon={<IconWatch size={14}/>} iconBg="mint" title="Fitbit" detail="Synced 2m ago" switchOn/>
            <Row icon={<IconAppleHealth size={14}/>} iconBg="red" title="Apple Health" detail="Not connected" switchOn={false}/>
            <Row icon={<IconBolt2 size={14}/>} iconBg="indigo" title="Ollama (insights)" detail="Local · healthy" switchOn last/>
          </div>
        </div>

        {/* Data */}
        <div className="ios-section">
          <div className="ios-section-h">Data</div>
          <div className="ios-list">
            <Row icon={<IconShare size={14}/>} iconBg="blue" title="Export CSV" chevron/>
            <Row icon={<IconUpload size={14}/>} iconBg="purple" title="Cloud backup" detail="Off" chevron last/>
          </div>
        </div>

        {/* About / Sign out */}
        <div className="ios-section" style={{ paddingBottom: 32 }}>
          <div className="ios-list">
            <Row title={<span style={{ color: 'var(--ios-blue)' }}>About gym</span>} chevron/>
            <Row title={<span style={{ color: 'var(--ios-red)', fontWeight: 600 }}>Sign out</span>} last/>
          </div>
          <div className="ios-caption" style={{ textAlign: 'center', padding: '14px 0' }}>v0.32.1</div>
        </div>
      </div>
      <TabBar active="settings"/>
    </>
  );
}

Object.assign(window, { ScreenInsightsIOS, ScreenSettingsIOS });
