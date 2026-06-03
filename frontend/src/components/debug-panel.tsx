"use client";

import { ChevronDown, ChevronRight, Code2, Timer } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { SearchTelemetry, TrainSearchResponse } from "@/lib/types";

interface DebugPanelProps {
  response: TrainSearchResponse | null;
  telemetry: SearchTelemetry | null;
  isOpen: boolean;
  onToggle: () => void;
}

export function DebugPanel({ response, telemetry, isOpen, onToggle }: DebugPanelProps) {
  return (
    <section className="border-t border-border py-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Code2 className="h-4 w-4 text-primary" />
            Debug
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Raw response and request timing for backend iteration.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {telemetry ? (
            <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm">
              <Timer className="h-4 w-4 text-muted-foreground" />
              {telemetry.latencyMs} ms
            </div>
          ) : null}
          <Button type="button" variant="outline" onClick={onToggle}>
            {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            JSON
          </Button>
        </div>
      </div>
      {isOpen ? (
        <div className="mt-4 overflow-hidden rounded-md border bg-[#111827] text-[#e5e7eb]">
          <pre className="max-h-[420px] overflow-auto p-4 text-xs leading-5">
            {response ? JSON.stringify({ telemetry, response }, null, 2) : "No response yet."}
          </pre>
        </div>
      ) : null}
    </section>
  );
}

