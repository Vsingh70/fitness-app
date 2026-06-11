// iOS UI building blocks. Exports to window for cross-script use.
// Loaded after React + babel + ios-frame.jsx.

// ----- SF-Symbol-styled icon helpers -----
const Icon = ({ d, size = 22, stroke = 1.6, fill = "none", style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill === "none" ? "none" : fill}
       stroke={fill === "none" ? "currentColor" : "none"} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
    <path d={d}/>
  </svg>
);
const IconHeart = (p) => <Icon {...p} d="M20.8 7.6A5.4 5.4 0 0 0 12 4a5.4 5.4 0 0 0-8.8 3.6c0 6.4 8.8 11.4 8.8 11.4s8.8-5 8.8-11.4z"/>;
const IconMoon = (p) => <Icon {...p} d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>;
const IconBolt = (p) => <Icon {...p} d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>;
const IconFlame = (p) => <Icon {...p} d="M12 2c1 4-1 6-3 8s-3 5-3 7a6 6 0 0 0 12 0c0-3-1-5-3-7-3-2-4-5-3-8z"/>;
const IconFoot = (p) => <Icon {...p} d="M7 4c1 0 2 1 2 3 0 4-3 7-3 10 0 1.5 1 3 3 3M16 9c1 0 2 1 2 3 0 3-2 5-2 7 0 1.5 1 3 2 3"/>;
const IconCalendar = (p) => <Icon {...p} d="M3 6.5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3V19a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3zM3 9h18M8 2v4M16 2v4"/>;
const IconDumbbell = (p) => <Icon {...p} d="M6 8v8M3 10v4M18 8v8M21 10v4M6 12h12"/>;
const IconList = (p) => <Icon {...p} d="M3 6h18M3 12h18M3 18h18"/>;
const IconUtensils = (p) => <Icon {...p} d="M7 3v8a2 2 0 0 0 2 2v8M9 3v6M5 3v6M17 14v7M17 14c-2 0-3-2-3-5 0-4 1.5-6 3-6s3 2 3 6c0 3-1 5-3 5z"/>;
const IconChart = (p) => <Icon {...p} d="M4 19V5M4 19h16M8 15l3-4 3 3 5-7"/>;
const IconGear = (p) => <Icon {...p} d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM21 12c0-.6-.1-1.1-.2-1.7l1.7-1.3a1 1 0 0 0 .2-1.2l-1.6-2.7a1 1 0 0 0-1.2-.4l-2 .8c-.9-.7-1.9-1.2-3-1.5L14.5 2a1 1 0 0 0-1-.8h-3a1 1 0 0 0-1 .8l-.4 2c-1.1.3-2.1.8-3 1.5l-2-.8a1 1 0 0 0-1.2.4L1.3 7.8a1 1 0 0 0 .2 1.2l1.7 1.3c-.1.6-.2 1.1-.2 1.7s.1 1.1.2 1.7l-1.7 1.3a1 1 0 0 0-.2 1.2l1.6 2.7c.3.4.8.6 1.2.4l2-.8c.9.7 1.9 1.2 3 1.5l.4 2c.1.4.5.8 1 .8h3c.5 0 .9-.4 1-.8l.4-2c1.1-.3 2.1-.8 3-1.5l2 .8c.4.2.9 0 1.2-.4l1.6-2.7a1 1 0 0 0-.2-1.2l-1.7-1.3c.1-.6.2-1.1.2-1.7z"/>;
const IconPlus = (p) => <Icon {...p} d="M12 5v14M5 12h14"/>;
const IconChevron = (p) => <Icon {...p} size={p?.size || 14} stroke={p?.stroke || 2.2} d="M9 6l6 6-6 6"/>;
const IconChevronL = (p) => <Icon {...p} size={p?.size || 14} stroke={p?.stroke || 2.2} d="M15 18l-6-6 6-6"/>;
const IconSearch = (p) => <Icon {...p} d="M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zM20 20l-3.5-3.5"/>;
const IconCheckmark = (p) => <Icon {...p} stroke={2.6} d="M5 12l5 5 10-12"/>;
const IconCamera = (p) => <Icon {...p} d="M3 7a2 2 0 0 1 2-2h2.5l1.5-2h6l1.5 2H19a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM12 9a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"/>;
const IconBarcode = (p) => <Icon {...p} d="M4 6v12M7 6v12M10 6v12M13 6v12M16 6v12M19 6v12M22 6v12"/>;
const IconAppleHealth = (p) => <Icon {...p} fill="currentColor" stroke="none" d="M12 21s-7-4.5-9-9c-1.6-3.6 1-7 4-7 2 0 3 1 5 3 2-2 3-3 5-3 3 0 5.6 3.4 4 7-2 4.5-9 9-9 9z"/>;
const IconWatch = (p) => <Icon {...p} d="M9 3l1 3h4l1-3M9 21l1-3h4l1 3M6 8a3 3 0 0 1 3-3h6a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3z"/>;
const IconShare = (p) => <Icon {...p} d="M12 3v12M8 7l4-4 4 4M5 12v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>;
const IconPlay = (p) => <Icon {...p} fill="currentColor" stroke="none" d="M6 4l14 8-14 8z"/>;
const IconTimer = (p) => <Icon {...p} d="M12 6V3M10 3h4M21 14a9 9 0 1 1-9-9M12 9v5l3 2"/>;
const IconArrow = (p) => <Icon {...p} d="M5 12h14M13 5l7 7-7 7"/>;
const IconStar = (p) => <Icon {...p} fill="currentColor" stroke="none" d="M12 2 14.4 9.5 22 9.6l-6.2 4.6 2.3 7.5L12 17.3 5.9 21.7l2.3-7.5L2 9.6l7.6-.1z"/>;
const IconBolt2 = (p) => <Icon {...p} d="M3 13h4l2-4 3 8 2-5h7"/>;
const IconDrop = (p) => <Icon {...p} d="M12 2C8 8 5 12 5 16a7 7 0 0 0 14 0c0-4-3-8-7-14z"/>;
const IconUpload = (p) => <Icon {...p} d="M12 3v12M7 8l5-5 5 5M5 16v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/>;

// ----- Stat tile -----
function StatTile({ label, value, unit, delta, deltaCls = "", icon, accent, big }) {
  return (
    <div className="stat-tile" style={big ? { padding: '16px 18px' } : undefined}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="lab">{label}</span>
        {icon && <span style={{ color: accent || 'var(--ios-label2)' }}>{icon}</span>}
      </div>
      <div className="v" style={big ? { fontSize: 36 } : undefined}>
        {value}{unit && <span className="u">{unit}</span>}
      </div>
      {delta && <div className={"delta " + deltaCls}>{delta}</div>}
    </div>
  );
}

// ----- Activity ring -----
function ActivityRing({ size = 80, stroke = 9, value = 0.5, color, track }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(1, value)));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={track || "rgba(120,120,128,0.18)"} strokeWidth={stroke}/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color || "var(--ios-blue)"} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}/>
    </svg>
  );
}

// ----- Triple ring (Apple Fitness-style: move/exercise/stand) -----
function TripleRing({ size = 96, stroke = 9, rings }) {
  const r1 = (size - stroke) / 2;
  const r2 = r1 - (stroke + 3);
  const r3 = r2 - (stroke + 3);
  const radii = [r1, r2, r3];
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
      {rings.map((ring, i) => {
        const r = radii[i];
        const c = 2 * Math.PI * r;
        const off = c * (1 - Math.max(0, Math.min(1, ring.value)));
        return (
          <g key={i}>
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={ring.color} strokeOpacity="0.18" strokeWidth={stroke}/>
            <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={ring.color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}/>
          </g>
        );
      })}
    </svg>
  );
}

// ----- Tab bar -----
function TabBar({ active }) {
  const tabs = [
    { id: 'today', label: 'Today', icon: <IconCalendar size={26}/> },
    { id: 'workouts', label: 'Workouts', icon: <IconDumbbell size={26}/> },
    { id: 'nutrition', label: 'Nutrition', icon: <IconUtensils size={26}/> },
    { id: 'insights', label: 'Insights', icon: <IconChart size={26}/> },
    { id: 'settings', label: 'Settings', icon: <IconGear size={26}/> },
  ];
  return (
    <div className="ios-tabbar">
      {tabs.map(t => (
        <div key={t.id} className={"tab " + (t.id === active ? "on" : "")}>
          {t.icon}
          <span>{t.label}</span>
        </div>
      ))}
    </div>
  );
}

// ----- Large title header -----
function LargeTitle({ title, subtitle, trailing }) {
  return (
    <div style={{ padding: '14px 24px 18px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
      <div>
        {subtitle && <div className="ios-kicker" style={{ marginBottom: 8 }}>{subtitle}</div>}
        <h1 className="ios-large-title" style={{ margin: 0 }}>{title}</h1>
      </div>
      {trailing}
    </div>
  );
}

// ----- Inline nav header (compact) -----
function CompactNav({ leading, title, trailing }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center',
      padding: '10px 16px', minHeight: 44,
    }}>
      <div style={{ justifySelf: 'start' }}>{leading}</div>
      <div className="ios-headline" style={{ fontSize: 17, fontWeight: 600 }}>{title}</div>
      <div style={{ justifySelf: 'end' }}>{trailing}</div>
    </div>
  );
}

// ----- Grouped list row -----
function Row({ icon, iconBg, title, detail, chevron, switchOn, last, accessory }) {
  return (
    <div className={"ios-row " + (last ? "no-sep-after" : "")}>
      {icon ? <span className={"icon" + (iconBg ? " colored " + iconBg : "")}>{icon}</span> : <span/>}
      <span className="title">{title}</span>
      {detail && <span className="detail">{detail}</span>}
      {accessory ? accessory : (chevron ? <IconChevron size={14}/> : (switchOn !== undefined ? <div className={"ios-switch" + (switchOn ? " on" : "")}/> : <span/>))}
    </div>
  );
}

// expose to global scope for cross-script use
Object.assign(window, {
  Icon, IconHeart, IconMoon, IconBolt, IconFlame, IconFoot, IconCalendar, IconDumbbell,
  IconList, IconUtensils, IconChart, IconGear, IconPlus, IconChevron, IconChevronL,
  IconSearch, IconCheckmark, IconCamera, IconBarcode, IconAppleHealth, IconWatch,
  IconShare, IconPlay, IconTimer, IconArrow, IconStar, IconBolt2, IconDrop, IconUpload,
  StatTile, ActivityRing, TripleRing, TabBar, LargeTitle, CompactNav, Row,
});
