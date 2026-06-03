import { Activity, ArrowRight, Gauge, Route, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Metric } from "@/components/metric";
import { availabilityLabel, coverageLabel, statusTone } from "@/lib/display";
import type { SegmentOpportunity } from "@/lib/types";
import { formatPercent, formatScore } from "@/lib/utils";

interface OpportunityCardProps {
  segment: SegmentOpportunity;
  rank?: number;
}

export function OpportunityCard({ segment, rank }: OpportunityCardProps) {
  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm">
              {typeof rank === "number" ? <span className="text-muted-foreground">#{rank}</span> : null}
              <span>{segment.source.code}</span>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
              <span>{segment.destination.code}</span>
            </CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">
              {segment.source.name} to {segment.destination.name}
            </p>
          </div>
          <Badge variant={statusTone(segment.availability.status)}>
            {availabilityLabel(segment.availability)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid metric-grid gap-2">
          <Metric label="Usefulness" value={formatScore(segment.usefulness_score)} tone="good" />
          <Metric label="Overlap" value={formatPercent(segment.overlap_ratio)} />
          <Metric label="Confirm chance" value={formatPercent(segment.confirmation_probability)} />
          <Metric label="Mismatch" value={formatScore(segment.route_mismatch_score)} tone="warn" />
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Route className="h-4 w-4" />
            {segment.distance_km} km segment
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Gauge className="h-4 w-4" />
            {coverageLabel(segment.coverage_type)}
          </div>
        </div>
        {segment.reason_codes.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {segment.reason_codes.slice(0, 4).map((reason) => (
              <Badge key={reason} variant="outline" className="gap-1">
                {reason.includes("CONFIRMED") ? (
                  <ShieldCheck className="h-3 w-3" />
                ) : (
                  <Activity className="h-3 w-3" />
                )}
                {coverageLabel(reason)}
              </Badge>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

