import type { Availability, AvailabilityStatus, SegmentOpportunity } from "@/lib/types";

export function availabilityLabel(availability: Availability) {
  if (availability.status === "AVAILABLE") {
    return availability.available_count ? `AVAILABLE ${availability.available_count}` : "AVAILABLE";
  }
  if (availability.status === "RAC") {
    return availability.rac_count ? `RAC ${availability.rac_count}` : "RAC";
  }
  if (availability.status === "WAITLIST") {
    return availability.waitlist_count ? `WL ${availability.waitlist_count}` : "WAITLIST";
  }
  if (availability.status === "NOT_AVAILABLE") {
    return "NOT AVAILABLE";
  }
  return "UNKNOWN";
}

export function statusTone(status: AvailabilityStatus): "available" | "rac" | "waitlist" | "muted" {
  if (status === "AVAILABLE") return "available";
  if (status === "RAC") return "rac";
  if (status === "WAITLIST" || status === "NOT_AVAILABLE") return "waitlist";
  return "muted";
}

export function stationPairLabel(segment: SegmentOpportunity) {
  return `${segment.source.code} -> ${segment.destination.code}`;
}

export function coverageLabel(value: string) {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
