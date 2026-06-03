"use client";

import type React from "react";
import { CalendarDays, Gauge, MapPin, Search, TrainFront } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { TrainSearchRequest, TravelClass } from "@/lib/types";

interface SearchFormProps {
  value: TrainSearchRequest;
  isLoading: boolean;
  onChange: (value: TrainSearchRequest) => void;
  onSubmit: () => void;
}

const travelClasses: Array<{ value: TravelClass; label: string }> = [
  { value: "3AC", label: "3AC" },
  { value: "2AC", label: "2AC" },
  { value: "SL", label: "SL" },
  { value: "1AC", label: "1AC" },
  { value: "CC", label: "CC" },
  { value: "EC", label: "EC" },
];

export function SearchForm({ value, isLoading, onChange, onSubmit }: SearchFormProps) {
  return (
    <form
      className="rounded-md border bg-card p-4 shadow-sm"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_160px_130px_120px_auto]">
        <FieldShell label="Source station" icon={<MapPin className="h-4 w-4" />}>
          <Input
            value={value.source_station}
            onChange={(event) => onChange({ ...value, source_station: event.target.value })}
            placeholder="Delhi or NDLS"
            autoComplete="off"
          />
        </FieldShell>

        <FieldShell label="Destination station" icon={<TrainFront className="h-4 w-4" />}>
          <Input
            value={value.destination_station}
            onChange={(event) => onChange({ ...value, destination_station: event.target.value })}
            placeholder="Mumbai or MMCT"
            autoComplete="off"
          />
        </FieldShell>

        <FieldShell label="Travel date" icon={<CalendarDays className="h-4 w-4" />}>
          <Input
            type="date"
            value={value.travel_date}
            onChange={(event) => onChange({ ...value, travel_date: event.target.value })}
          />
        </FieldShell>

        <FieldShell label="Class" icon={<Gauge className="h-4 w-4" />}>
          <Select
            value={value.travel_class}
            onValueChange={(travelClass) =>
              onChange({ ...value, travel_class: travelClass as TravelClass })
            }
          >
            <SelectTrigger aria-label="Travel class">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {travelClasses.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FieldShell>

        <FieldShell label="Max results" icon={<Search className="h-4 w-4" />}>
          <Input
            type="number"
            min={1}
            max={25}
            value={value.max_results}
            onChange={(event) => onChange({ ...value, max_results: Number(event.target.value) })}
          />
        </FieldShell>

        <div className="flex items-end">
          <Button type="submit" className="w-full whitespace-nowrap" disabled={isLoading}>
            <Search className="h-4 w-4" />
            {isLoading ? "Searching" : "Find Better Routes"}
          </Button>
        </div>
      </div>
    </form>
  );
}

function FieldShell({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label className="flex items-center gap-2 text-muted-foreground">
        {icon}
        {label}
      </Label>
      {children}
    </div>
  );
}
