import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";

export default function TodayPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
        <p className="text-text-secondary mt-1">
          Your training summary lives here once workouts and nutrition land.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Weekly sets" value="0" trend="flat" delta="vs last week" />
        <StatTile label="Tonnage" value="0" unit="kg" trend="flat" delta="vs last week" />
        <StatTile label="Streak" value="0" unit="days" />
        <StatTile label="Sleep" value="0" unit="h" />
      </section>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Up next</h2>
        </CardHeader>
        <CardContent>
          <p className="text-text-secondary">
            No scheduled workout. Pick a program in <span className="text-text">Programs</span> or
            start an ad-hoc session from <span className="text-text">Workouts</span>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
