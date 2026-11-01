"use client";

import { useId } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function GroupCompletionChart({
  data,
}: {
  data: { name: string; completion: number | null }[];
}) {
  const gradientId = useId();
  return (
    <section
      aria-label="Completion percentage by group"
      className="flex h-[calc(var(--dashboard-height)*0.55)] min-h-0 shrink-0 flex-col overflow-hidden rounded-lg bg-white px-4 pt-5 pb-[calc((var(--app-footer-height)-2rem+1px)/2)] shadow-[0_2px_3px_rgba(0,0,0,0.04),0_8px_18px_-8px_rgba(0,0,0,0.18)]"
    >
      <h2 className="mb-5 shrink-0 text-base font-semibold text-emerald-700">Completion by group</h2>
      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
        <div className="h-full min-w-[560px]">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <AreaChart accessibilityLayer data={data} margin={{ top: 12, right: 24, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#047857" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#047857" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#e7e5e4" strokeDasharray="3 3" />
              <XAxis dataKey="name" height={32} axisLine={false} tickLine={false} tickMargin={12} interval={0} tick={{ fontSize: 12, fill: "#78716c" }} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(value) => `${value}%`} axisLine={false} tickLine={false} tickMargin={8} width={52} tick={{ fontSize: 12, fill: "#78716c" }} />
              <Tooltip
                formatter={(value) => [`${Math.round(Number(value))}%`, "Completion"]}
                contentStyle={{ border: "none", borderRadius: 8, fontSize: 13, boxShadow: "0 4px 18px rgb(0 0 0 / 0.1)" }}
              />
              <Area
                type="monotone"
                dataKey="completion"
                stroke="#047857"
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={{ r: 4, fill: "#047857", stroke: "white", strokeWidth: 2 }}
                activeDot={{ r: 5 }}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
