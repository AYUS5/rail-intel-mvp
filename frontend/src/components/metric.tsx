import { cn } from "@/lib/utils";

interface MetricProps {
  label: string;
  value: string;
  tone?: "default" | "good" | "warn" | "bad";
}

export function Metric({ label, value, tone = "default" }: MetricProps) {
  return (
    <div className={cn("rounded-md border bg-background px-3 py-2", toneClass[tone])}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  );
}

const toneClass = {
  default: "border-border",
  good: "border-emerald-200 bg-emerald-50",
  warn: "border-amber-200 bg-amber-50",
  bad: "border-rose-200 bg-rose-50",
};

