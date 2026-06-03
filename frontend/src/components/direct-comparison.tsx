import { ArrowRight, BadgeCheck, GitCompareArrows } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { availabilityLabel, statusTone } from "@/lib/display";
import type { Recommendation, TrainSearchResult } from "@/lib/types";
import { formatPercent, formatScore } from "@/lib/utils";

interface DirectComparisonProps {
  result: TrainSearchResult;
  recommendation: Recommendation | undefined;
}

export function DirectComparison({ result, recommendation }: DirectComparisonProps) {
  const bestSegment = recommendation?.segment;

  return (
    <div className="rounded-md border bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
        <GitCompareArrows className="h-4 w-4 text-primary" />
        Direct route vs suggested opportunity
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_auto_1fr] lg:items-stretch">
        <RoutePanel
          label="Direct route"
          source={result.direct_availability.source_station_code}
          destination={result.direct_availability.destination_station_code}
          status={availabilityLabel(result.direct_availability)}
          statusTone={statusTone(result.direct_availability.status)}
        />
        <div className="hidden items-center justify-center lg:flex">
          <ArrowRight className="h-5 w-5 text-muted-foreground" />
        </div>
        {bestSegment ? (
          <RoutePanel
            label="Suggested route"
            source={bestSegment.source.code}
            destination={bestSegment.destination.code}
            status={availabilityLabel(bestSegment.availability)}
            statusTone={statusTone(bestSegment.availability.status)}
            footer={`Usefulness ${formatScore(bestSegment.usefulness_score)} · overlap ${formatPercent(
              bestSegment.overlap_ratio,
            )}`}
            highlighted
          />
        ) : (
          <div className="rounded-md border border-dashed bg-muted/40 p-4">
            <div className="text-sm font-semibold">No stronger suggestion yet</div>
            <p className="mt-2 text-sm text-muted-foreground">
              The backend did not find a useful hidden segment for this train.
            </p>
          </div>
        )}
      </div>
      {recommendation ? (
        <div className="mt-4 flex gap-2 rounded-md bg-accent px-3 py-2 text-sm text-accent-foreground">
          <BadgeCheck className="mt-0.5 h-4 w-4 flex-none" />
          <span>{recommendation.explanation}</span>
        </div>
      ) : null}
    </div>
  );
}

function RoutePanel({
  label,
  source,
  destination,
  status,
  statusTone,
  footer,
  highlighted,
}: {
  label: string;
  source: string;
  destination: string;
  status: string;
  statusTone: "available" | "rac" | "waitlist" | "muted";
  footer?: string;
  highlighted?: boolean;
}) {
  return (
    <div className={highlighted ? "rounded-md border border-emerald-300 bg-emerald-50 p-4" : "rounded-md border p-4"}>
      <div className="text-xs font-medium uppercase text-muted-foreground">{label}</div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-lg font-semibold">
        <span>{source}</span>
        <ArrowRight className="h-4 w-4 text-muted-foreground" />
        <span>{destination}</span>
      </div>
      <div className="mt-3">
        <Badge variant={statusTone}>{status}</Badge>
      </div>
      {footer ? <div className="mt-3 text-sm text-muted-foreground">{footer}</div> : null}
    </div>
  );
}

