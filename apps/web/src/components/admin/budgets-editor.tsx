"use client";

import { useState } from "react";
import { BellRing, Check, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { formatUsd, type AlertItem } from "@/lib/playground-types";

export type BudgetsData = {
  org_cap_usd: number; default_user_cap_usd: number;
  user_caps: { user_id: string; name: string; cap_usd: number }[];
  department_caps: { department: string; cap_usd: number }[];
  departments: string[];
};
type Person = { id: string; name: string };

export function BudgetsEditor({ initial, people, alerts: initialAlerts }: { initial: BudgetsData; people: Person[]; alerts: AlertItem[] }) {
  const [data, setData] = useState(initial);
  const [alerts, setAlerts] = useState(initialAlerts);
  const [newUser, setNewUser] = useState(people[0]?.id ?? "");
  const [newUserCap, setNewUserCap] = useState(25);
  const [newDept, setNewDept] = useState(initial.departments[0] ?? "");
  const [newDeptCap, setNewDeptCap] = useState(500);

  const save = async () => {
    const body = {
      org_cap_usd: data.org_cap_usd, default_user_cap_usd: data.default_user_cap_usd,
      user_caps: Object.fromEntries(data.user_caps.map((u) => [u.user_id, u.cap_usd])),
      department_caps: Object.fromEntries(data.department_caps.map((d) => [d.department, d.cap_usd])),
    };
    const res = await fetch("/api/pg/v1/admin/budgets", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    if (res.ok) toast.success("Budgets saved"); else toast.error("Could not save budgets");
  };
  const ack = async (id: string) => {
    await fetch(`/api/pg/v1/alerts/${id}/ack`, { method: "POST" });
    setAlerts((as) => as.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
      <div className="space-y-4">
        <section className="rounded-2xl border bg-card p-4">
          <h2 className="text-sm font-semibold">Caps</h2>
          <p className="mt-1 text-xs text-muted-foreground">Alerts fire at 50, 80 and 100 percent. At 100 percent new calls are blocked until the month rolls over or the cap is raised.</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="text-xs">Organization cap per month
              <input type="number" min={0} step={50} value={data.org_cap_usd} onChange={(e) => setData({ ...data, org_cap_usd: Number(e.target.value) })} aria-label="Organization monthly cap" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 font-mono" />
            </label>
            <label className="text-xs">Default cap per person per month
              <input type="number" min={0} step={5} value={data.default_user_cap_usd} onChange={(e) => setData({ ...data, default_user_cap_usd: Number(e.target.value) })} aria-label="Default user monthly cap" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 font-mono" />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border bg-card p-4">
          <h2 className="text-sm font-semibold">Per-person overrides</h2>
          <ul className="mt-2 divide-y text-xs">
            {data.user_caps.map((u) => (
              <li key={u.user_id} className="flex items-center gap-2 py-2">
                <span className="flex-1">{u.name}</span>
                <span className="font-mono">{formatUsd(u.cap_usd)}</span>
                <button type="button" aria-label={`Remove cap for ${u.name}`} onClick={() => setData({ ...data, user_caps: data.user_caps.filter((x) => x.user_id !== u.user_id) })} className="grid size-7 place-items-center rounded-md hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <select value={newUser} onChange={(e) => setNewUser(e.target.value)} aria-label="Person to cap" className="h-8 rounded-lg border bg-background px-2">
              {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <input type="number" min={0} step={1} value={newUserCap} onChange={(e) => setNewUserCap(Number(e.target.value))} aria-label="Cap amount" className="h-8 w-24 rounded-lg border bg-background px-2 font-mono" />
            <Button size="sm" variant="outline" onClick={() => {
              const person = people.find((p) => p.id === newUser); if (!person) return;
              setData({ ...data, user_caps: [...data.user_caps.filter((x) => x.user_id !== newUser), { user_id: newUser, name: person.name, cap_usd: newUserCap }] });
            }}>Add person cap</Button>
          </div>
        </section>

        <section className="rounded-2xl border bg-card p-4">
          <h2 className="text-sm font-semibold">Department caps</h2>
          <ul className="mt-2 divide-y text-xs">
            {data.department_caps.map((d) => (
              <li key={d.department} className="flex items-center gap-2 py-2">
                <span className="flex-1">{d.department}</span>
                <span className="font-mono">{formatUsd(d.cap_usd)}</span>
                <button type="button" aria-label={`Remove cap for ${d.department}`} onClick={() => setData({ ...data, department_caps: data.department_caps.filter((x) => x.department !== d.department) })} className="grid size-7 place-items-center rounded-md hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <select value={newDept} onChange={(e) => setNewDept(e.target.value)} aria-label="Department to cap" className="h-8 rounded-lg border bg-background px-2">
              {data.departments.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <input type="number" min={0} step={10} value={newDeptCap} onChange={(e) => setNewDeptCap(Number(e.target.value))} aria-label="Department cap amount" className="h-8 w-24 rounded-lg border bg-background px-2 font-mono" />
            <Button size="sm" variant="outline" onClick={() => { if (!newDept) return; setData({ ...data, department_caps: [...data.department_caps.filter((x) => x.department !== newDept), { department: newDept, cap_usd: newDeptCap }] }); }}>Add department cap</Button>
          </div>
        </section>

        <Button onClick={save} className="glow-violet">Save budgets</Button>
      </div>

      <section className="rounded-2xl border bg-card p-4" aria-label="Budget alerts">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><BellRing className="size-4 text-brand-amber" /> Alerts</h2>
        <ul className="mt-2 space-y-2 text-xs" data-testid="alerts-list">
          {alerts.length === 0 && <li className="rounded-lg border border-dashed p-4 text-center text-muted-foreground">No thresholds crossed this month.</li>}
          {alerts.map((a) => (
            <li key={a.id} className={`flex items-start gap-2 rounded-lg border p-2.5 ${a.acknowledged ? "opacity-60" : a.threshold >= 100 ? "border-brand-rose/50 bg-brand-rose/5" : "border-brand-amber/50 bg-brand-amber/5"}`}>
              <div className="flex-1">
                <p className="font-medium">{a.label} reached {a.threshold}%</p>
                <p className="text-muted-foreground">{formatUsd(a.spend_usd)} of {formatUsd(a.cap_usd)} · {a.period}</p>
              </div>
              {!a.acknowledged && <button type="button" onClick={() => ack(a.id)} aria-label="Acknowledge alert" className="grid size-7 place-items-center rounded-md hover:bg-muted"><Check className="size-3.5" /></button>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
