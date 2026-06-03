import { BarChart3, Clock, ListChecks, TrainFront } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DirectComparison } from "@/components/direct-comparison";
import { OpportunityCard } from "@/components/opportunity-card";
import { availabilityLabel, statusTone } from "@/lib/display";
import type { TrainSearchResult } from "@/lib/types";

interface TrainResultProps {
  result: TrainSearchResult;
}

export function TrainResult({ result }: TrainResultProps) {
  const topRecommendation = result.recommendations[0];

  return (
    <section className="space-y-4 border-t border-border py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <TrainFront className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">
              {result.train.number} · {result.train.name}
            </h2>
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              {result.route.length} stops
            </span>
            <span className="flex items-center gap-1">
              <ListChecks className="h-4 w-4" />
              {result.pairs_considered} pairs checked
            </span>
            <span className="flex items-center gap-1">
              <BarChart3 className="h-4 w-4" />
              {result.hidden_segments.length} hidden opportunities
            </span>
          </div>
        </div>
        <Badge variant={statusTone(result.direct_availability.status)}>
          Direct: {availabilityLabel(result.direct_availability)}
        </Badge>
      </div>

      <DirectComparison result={result} recommendation={topRecommendation} />

      {result.recommendations.length > 0 ? (
        <div className="rounded-md border bg-background p-4">
          <div className="mb-3 text-sm font-semibold">Recommendation ranking</div>
          <div className="grid gap-3">
            {result.recommendations.map((recommendation) => (
              <div
                key={`${recommendation.rank}-${recommendation.segment.source.code}-${recommendation.segment.destination.code}`}
                className="grid gap-3 rounded-md border bg-card p-3 md:grid-cols-[48px_1fr_auto]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
                  #{recommendation.rank}
                </div>
                <div>
                  <div className="font-medium">{recommendation.title}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{recommendation.explanation}</div>
                </div>
                <div className="flex flex-wrap items-center gap-2 md:justify-end">
                  <Badge variant="outline">score {recommendation.score.toFixed(2)}</Badge>
                  <Badge variant="outline">confidence {Math.round(recommendation.confidence * 100)}%</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div>
        <div className="mb-3 text-sm font-semibold">Hidden segment opportunities</div>
        {result.hidden_segments.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {result.hidden_segments.map((segment, index) => (
              <OpportunityCard
                key={`${segment.source.code}-${segment.destination.code}-${index}`}
                segment={segment}
                rank={index + 1}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-dashed bg-muted/40 p-4 text-sm text-muted-foreground">
            No hidden segment passed the usefulness threshold for this train.
          </div>
        )}
      </div>
    </section>
  );
}

