"use client";

import { useMemo, useState } from "react";
import { AlertCircle, DatabaseZap, Info, RefreshCcw, ShieldCheck, TrainFront } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchForm } from "@/components/search-form";
import { TrainResult } from "@/components/train-result";
import { DebugPanel } from "@/components/debug-panel";
import { LoadingResults } from "@/components/loading-results";
import { searchTrains } from "@/lib/api";
import type { TrainSearchRequest, SearchState } from "@/lib/types";

const initialSearch: TrainSearchRequest = {
  source_station: "Delhi",
  destination_station: "Mumbai",
  travel_date: getDefaultTravelDate(),
  travel_class: "3AC",
  max_results: 5,
  include_explanations: true,
};

export default function RailIntelPage() {
  const [formValue, setFormValue] = useState<TrainSearchRequest>(initialSearch);
  const [searchState, setSearchState] = useState<SearchState>({ response: null, telemetry: null });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [debugOpen, setDebugOpen] = useState(false);

  const totalOpportunities = useMemo(() => {
    return searchState.response?.results.reduce((sum, result) => sum + result.hidden_segments.length, 0) ?? 0;
  }, [searchState.response]);

  async function handleSearch() {
    setError(null);
    if (!formValue.source_station.trim() || !formValue.destination_station.trim()) {
      setError("Enter both source and destination stations.");
      return;
    }
    if (!formValue.travel_date) {
      setError("Choose a travel date.");
      return;
    }

    setIsLoading(true);
    try {
      const result = await searchTrains({
        ...formValue,
        source_station: formValue.source_station.trim(),
        destination_station: formValue.destination_station.trim(),
        max_results: Math.min(Math.max(formValue.max_results || 1, 1), 25),
      });
      setSearchState({ response: result.data, telemetry: result.telemetry });
    } catch (requestError) {
      setSearchState((current) => ({ ...current, response: null }));
      setError(requestError instanceof Error ? requestError.message : "Unable to reach the backend.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <TrainFront className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold">Rail Intel MVP</h1>
                <p className="text-sm text-muted-foreground">
                  Search direct availability and compare hidden segment opportunities.
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
            Analysis only. No booking automation.
          </div>
        </header>

        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Search route intelligence</h2>
              <p className="text-sm text-muted-foreground">
                Try Delhi to Mumbai in 3AC to see the mock backend’s hidden segment detection.
              </p>
            </div>
            {searchState.telemetry ? (
              <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm">
                <DatabaseZap className="h-4 w-4 text-primary" />
                Last response {searchState.telemetry.latencyMs} ms
              </div>
            ) : null}
          </div>
          <SearchForm value={formValue} isLoading={isLoading} onChange={setFormValue} onSubmit={handleSearch} />
        </section>

        {error ? (
          <section className="rounded-md border border-rose-200 bg-rose-50 p-4 text-rose-900">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex gap-2">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-none" />
                <div>
                  <div className="font-semibold">Search failed</div>
                  <p className="mt-1 text-sm">{error}</p>
                </div>
              </div>
              <Button type="button" variant="outline" onClick={handleSearch} disabled={isLoading}>
                <RefreshCcw className="h-4 w-4" />
                Retry
              </Button>
            </div>
          </section>
        ) : null}

        {isLoading ? <LoadingResults /> : null}

        {!isLoading && searchState.response ? (
          <section className="space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
              <div>
                <h2 className="text-lg font-semibold">Results</h2>
                <p className="text-sm text-muted-foreground">
                  {searchState.response.results.length} trains, {totalOpportunities} hidden opportunities.
                </p>
              </div>
              <div className="rounded-md border bg-card px-3 py-2 text-sm text-muted-foreground">
                Query ID {searchState.response.query_id.slice(0, 8)}
              </div>
            </div>

            {searchState.response.results.length > 0 ? (
              searchState.response.results.map((result) => (
                <TrainResult key={result.train.number} result={result} />
              ))
            ) : (
              <EmptyResults />
            )}
          </section>
        ) : null}

        {!isLoading && !searchState.response && !error ? <InitialState /> : null}

        <DebugPanel
          response={searchState.response}
          telemetry={searchState.telemetry}
          isOpen={debugOpen}
          onToggle={() => setDebugOpen((open) => !open)}
        />
      </div>
    </main>
  );
}

function InitialState() {
  return (
    <section className="rounded-md border border-dashed bg-muted/40 p-5">
      <div className="flex gap-3">
        <Info className="mt-0.5 h-5 w-5 text-primary" />
        <div>
          <div className="font-semibold">Ready for a route search</div>
          <p className="mt-1 text-sm text-muted-foreground">
            Results will show direct status, ranked recommendations, and hidden segment opportunities.
          </p>
        </div>
      </div>
    </section>
  );
}

function EmptyResults() {
  return (
    <section className="rounded-md border border-dashed bg-muted/40 p-5">
      <div className="font-semibold">No trains found</div>
      <p className="mt-1 text-sm text-muted-foreground">
        Try station codes such as NDLS and MMCT, or broaden max results.
      </p>
    </section>
  );
}

function getDefaultTravelDate() {
  const date = new Date();
  date.setDate(date.getDate() + 14);
  return date.toISOString().slice(0, 10);
}

