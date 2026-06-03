from datetime import date

from app.repositories.railway_provider import RailwayProviderInterface
from app.schemas.common import AvailabilityStatus, TravelClass
from app.services.dtos import AvailabilitySnapshot, StationStop, TrainRoute


class MockRailwayProvider(RailwayProviderInterface):
    """Real train routes, real station sequences, realistic availability data.

    Trains included:
      12952 - Mumbai Rajdhani Express       (NDLS → MMCT)  daily flagship
      12954 - August Kranti Rajdhani        (NZM  → MMCT)  alternate Mumbai
      12302 - Howrah Rajdhani Express       (NDLS → HWH)   Delhi–Kolkata flagship
      12724 - Telangana Express             (NDLS → HYB)   Delhi–Hyderabad daily
      12628 - Karnataka Express             (NDLS → SBC)   Delhi–Bangalore daily
    """

    _aliases = {
        # Delhi cluster
        "DELHI": "NDLS",
        "NEW DELHI": "NDLS",
        "NDLS": "NDLS",
        "HAZRAT NIZAMUDDIN": "NZM",
        "NIZAMUDDIN": "NZM",
        "NZM": "NZM",
        # UP / MP
        "MATHURA": "MTJ",
        "MATHURA JN": "MTJ",
        "MTJ": "MTJ",
        "AGRA": "AGC",
        "AGRA CANTT": "AGC",
        "AGC": "AGC",
        "GWALIOR": "GWL",
        "GWL": "GWL",
        "JHANSI": "VGLJ",
        "VGLJ": "VGLJ",
        "KOTA": "KOTA",
        "KOTA JN": "KOTA",
        "BHOPAL": "BPL",
        "BHOPAL JN": "BPL",
        "BPL": "BPL",
        "BINA": "BINA",
        "KANPUR": "CNB",
        "KANPUR CENTRAL": "CNB",
        "CNB": "CNB",
        "PRAYAGRAJ": "PRYJ",
        "ALLAHABAD": "PRYJ",
        "ALD": "PRYJ",
        "PRYJ": "PRYJ",
        # Bihar / Jharkhand / WB
        "DEEN DAYAL UPADHYAYA": "DDU",
        "MUGHALSARAI": "DDU",
        "DDU": "DDU",
        "GAYA": "GAYA",
        "GAYA JN": "GAYA",
        "DHANBAD": "DHN",
        "DHN": "DHN",
        "ASANSOL": "ASN",
        "ASN": "ASN",
        "HOWRAH": "HWH",
        "KOLKATA": "HWH",
        "HWH": "HWH",
        # Mumbai corridor
        "RATLAM": "RTM",
        "RTM": "RTM",
        "VADODARA": "BRC",
        "BARODA": "BRC",
        "BRC": "BRC",
        "SURAT": "ST",
        "ST": "ST",
        "MUMBAI": "MMCT",
        "MUMBAI CENTRAL": "MMCT",
        "MMCT": "MMCT",
        # Hyderabad corridor
        "NAGPUR": "NGP",
        "NGP": "NGP",
        "KAZIPET": "KZJ",
        "KZJ": "KZJ",
        "SECUNDERABAD": "SC",
        "SC": "SC",
        "HYDERABAD": "HYB",
        "HYDERABAD DECCAN": "HYB",
        "HYB": "HYB",
        # Bangalore corridor
        "ITARSI": "ET",
        "ET": "ET",
        "MANMAD": "MMR",
        "MMR": "MMR",
        "GUNTAKAL": "GTL",
        "GTL": "GTL",
        "BANGALORE": "SBC",
        "BENGALURU": "SBC",
        "KSR BENGALURU": "SBC",
        "SBC": "SBC",
    }

    def __init__(self) -> None:
        self._routes = self._build_routes()
        self._availability = self._build_availability()

    def normalize_station_code(self, station: str) -> str:
        normalized = " ".join(station.upper().split())
        return self._aliases.get(normalized, normalized)

    async def search_trains(
        self,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> list[TrainRoute]:
        source_code = self.normalize_station_code(source_station)
        destination_code = self.normalize_station_code(destination_station)
        matches: list[TrainRoute] = []
        for route in self._routes.values():
            index = route.index_by_station_code()
            if (
                source_code in index
                and destination_code in index
                and index[source_code] < index[destination_code]
            ):
                matches.append(route)
        return matches

    async def get_train_route(self, train_number: str) -> TrainRoute | None:
        return self._routes.get(train_number)

    async def get_availability(
        self,
        train_number: str,
        source_station: str,
        destination_station: str,
        travel_date: date,
        travel_class: TravelClass,
    ) -> AvailabilitySnapshot:
        source_code = self.normalize_station_code(source_station)
        destination_code = self.normalize_station_code(destination_station)
        key = (train_number, source_code, destination_code, travel_class.value)
        status, available, rac, waitlist = self._availability.get(
            key,
            self._fallback_availability(train_number, source_code, destination_code),
        )
        return AvailabilitySnapshot(
            train_number=train_number,
            source_station_code=source_code,
            destination_station_code=destination_code,
            travel_date=travel_date,
            travel_class=travel_class,
            status=status,
            available_count=available,
            rac_count=rac,
            waitlist_count=waitlist,
        )

    def _fallback_availability(
        self,
        train_number: str,
        source_code: str,
        destination_code: str,
    ) -> tuple[AvailabilityStatus, int | None, int | None, int | None]:
        route = self._routes.get(train_number)
        if not route:
            return (AvailabilityStatus.UNKNOWN, None, None, None)
        index = route.index_by_station_code()
        if source_code not in index or destination_code not in index:
            return (AvailabilityStatus.UNKNOWN, None, None, None)
        span = index[destination_code] - index[source_code]
        if span <= 1:
            return (AvailabilityStatus.AVAILABLE, 4, None, None)
        if span == 2:
            return (AvailabilityStatus.RAC, None, 6, None)
        return (AvailabilityStatus.WAITLIST, None, None, 22)

    # ------------------------------------------------------------------
    # Route definitions  (real station codes, real distances, real times)
    # ------------------------------------------------------------------

    def _build_routes(self) -> dict[str, TrainRoute]:
        # ── 12952 Mumbai Rajdhani Express ─────────────────────────────
        # NDLS → MTJ → KOTA → BRC → ST → MMCT   1384 km
        rajdhani_stops = (
            StationStop("NDLS", "New Delhi",        0, 0,    departure="16:55"),
            StationStop("MTJ",  "Mathura Junction", 1, 141,  "18:20", "18:22"),
            StationStop("KOTA", "Kota Junction",    2, 465,  "22:40", "22:50"),
            StationStop("BRC",  "Vadodara Junction",3, 995,  "04:15", "04:25"),
            StationStop("ST",   "Surat",            4, 1124, "06:18", "06:23"),
            StationStop("MMCT", "Mumbai Central",   5, 1384, "08:35"),
        )

        # ── 12954 August Kranti Rajdhani ──────────────────────────────
        # NZM → MTJ → KOTA → RTM → BRC → ST → MMCT   1378 km
        aug_kranti_stops = (
            StationStop("NZM",  "Hazrat Nizamuddin",0, 0,    departure="17:15"),
            StationStop("MTJ",  "Mathura Junction", 1, 134,  "18:40", "18:42"),
            StationStop("KOTA", "Kota Junction",    2, 458,  "23:05", "23:15"),
            StationStop("RTM",  "Ratlam Junction",  3, 724,  "02:25", "02:35"),
            StationStop("BRC",  "Vadodara Junction",4, 985,  "05:58", "06:06"),
            StationStop("ST",   "Surat",            5, 1113, "07:42", "07:47"),
            StationStop("MMCT", "Mumbai Central",   6, 1378, "10:05"),
        )

        # ── 12302 Howrah Rajdhani Express (via Gaya) ──────────────────
        # NDLS → CNB → PRYJ → DDU → GAYA → DHN → ASN → HWH   1447 km
        hwh_rajdhani_stops = (
            StationStop("NDLS", "New Delhi",                0, 0,    departure="16:50"),
            StationStop("CNB",  "Kanpur Central",           1, 440,  "21:30", "21:35"),
            StationStop("PRYJ", "Prayagraj Junction",       2, 634,  "23:41", "23:43"),
            StationStop("DDU",  "Pt Deen Dayal Upadhyaya", 3, 786,  "01:33", "01:40"),
            StationStop("GAYA", "Gaya Junction",            4, 989,  "03:57", "04:00"),
            StationStop("DHN",  "Dhanbad Junction",         5, 1188, "06:33", "06:38"),
            StationStop("ASN",  "Asansol Junction",         6, 1247, "07:18", "07:20"),
            StationStop("HWH",  "Howrah Junction",          7, 1447, "09:55"),
        )

        # ── 12724 Telangana Express ────────────────────────────────────
        # NDLS → MTJ → AGC → GWL → VGLJ → BPL → NGP → KZJ → SC → HYB
        # 1677 km   25h 10m   daily   SL/3A/2A/1A
        telangana_stops = (
            StationStop("NDLS", "New Delhi",               0, 0,    departure="16:00"),
            StationStop("MTJ",  "Mathura Junction",        1, 141,  "17:52", "17:54"),
            StationStop("AGC",  "Agra Cantt",              2, 195,  "18:50", "18:55"),
            StationStop("GWL",  "Gwalior Junction",        3, 319,  "20:28", "20:30"),
            StationStop("VGLJ", "Virangana Lakshmibai Jhansi", 4, 403, "21:35", "21:45"),
            StationStop("BPL",  "Bhopal Junction",         5, 705,  "02:05", "02:15"),
            StationStop("NGP",  "Nagpur Junction",         6, 1093, "08:00", "08:05"),
            StationStop("KZJ",  "Kazipet Junction",        7, 1469, "13:42", "13:44"),
            StationStop("SC",   "Secunderabad Junction",   8, 1572, "15:45", "15:50"),
            StationStop("HYB",  "Hyderabad Deccan",        9, 1677, "17:10"),
        )

        # ── 12628 Karnataka Express ───────────────────────────────────
        # NDLS → NZM → MTJ → AGC → GWL → VGLJ → BPL → ET → NGP → GTL → SBC
        # 2392 km   37h 40m   daily   SL/3A/2A
        # (running NDLS→SBC direction — reverse of 12627)
        karnataka_stops = (
            StationStop("NDLS", "New Delhi",               0, 0,    departure="20:20"),
            StationStop("NZM",  "Hazrat Nizamuddin",       1, 7,    "20:35", "20:37"),
            StationStop("MTJ",  "Mathura Junction",        2, 141,  "22:15", "22:17"),
            StationStop("AGC",  "Agra Cantt",              3, 195,  "23:05", "23:10"),
            StationStop("GWL",  "Gwalior Junction",        4, 319,  "00:42", "00:44"),
            StationStop("VGLJ", "Virangana Lakshmibai Jhansi", 5, 403, "01:50", "01:58"),
            StationStop("BPL",  "Bhopal Junction",         6, 705,  "06:35", "06:45"),
            StationStop("ET",   "Itarsi Junction",         7, 799,  "08:10", "08:15"),
            StationStop("NGP",  "Nagpur Junction",         8, 1093, "12:30", "12:40"),
            StationStop("GTL",  "Guntakal Junction",       9, 1555, "20:05", "20:15"),
            StationStop("SBC",  "KSR Bengaluru City",      10, 1930, "08:30"),
        )

        return {
            "12952": TrainRoute("12952", "Mumbai Rajdhani Express",
                                "NDLS", "MMCT", rajdhani_stops),
            "12954": TrainRoute("12954", "August Kranti Rajdhani Express",
                                "NZM",  "MMCT", aug_kranti_stops),
            "12302": TrainRoute("12302", "Howrah Rajdhani Express",
                                "NDLS", "HWH",  hwh_rajdhani_stops),
            "12724": TrainRoute("12724", "Telangana Express",
                                "NDLS", "HYB",  telangana_stops),
            "12628": TrainRoute("12628", "Karnataka Express",
                                "NDLS", "SBC",  karnataka_stops),
        }

    # ------------------------------------------------------------------
    # Availability  — realistic waitlist on trunk segments,
    # confirmed seats on intermediate / later-boarding segments
    # (this is the data that makes hidden segment detection interesting)
    # ------------------------------------------------------------------

    def _build_availability(
        self,
    ) -> dict[tuple[str, str, str, str], tuple[AvailabilityStatus, int | None, int | None, int | None]]:
        A = AvailabilityStatus.AVAILABLE
        R = AvailabilityStatus.RAC
        W = AvailabilityStatus.WAITLIST

        rows = [
            # ── 12952 Mumbai Rajdhani ─────────────────────────────────
            # Direct NDLS→MMCT: heavily waitlisted
            ("12952", "NDLS", "MMCT", "3A", W, None, None, 120),
            ("12952", "NDLS", "MMCT", "SL", W, None, None, 64),
            ("12952", "NDLS", "MMCT", "2A", W, None, None, 38),
            # Later boarding → destination: confirmed (HIDDEN GEMS)
            ("12952", "MTJ",  "MMCT", "3A", A, 9,    None, None),
            ("12952", "MTJ",  "MMCT", "SL", R, None, 18,   None),
            ("12952", "KOTA", "MMCT", "3A", R, None, 4,    None),
            ("12952", "BRC",  "MMCT", "3A", A, 22,   None, None),
            # Early detrain: confirmed (HIDDEN GEM — board Delhi, leave early)
            ("12952", "NDLS", "KOTA", "3A", A, 18,   None, None),
            ("12952", "NDLS", "BRC",  "3A", R, None, 12,   None),
            # Short intermediate segments: available
            ("12952", "MTJ",  "KOTA", "3A", A, 14,   None, None),
            ("12952", "KOTA", "BRC",  "3A", A, 7,    None, None),

            # ── 12954 August Kranti Rajdhani ─────────────────────────
            ("12954", "NZM",  "MMCT", "3A", W, None, None, 42),
            ("12954", "NZM",  "MMCT", "SL", W, None, None, 89),
            ("12954", "MTJ",  "MMCT", "3A", A, 4,    None, None),
            ("12954", "NZM",  "KOTA", "3A", A, 11,   None, None),
            ("12954", "RTM",  "MMCT", "3A", A, 7,    None, None),
            ("12954", "KOTA", "MMCT", "3A", R, None, 3,    None),

            # ── 12302 Howrah Rajdhani ─────────────────────────────────
            # Trunk Delhi→Howrah: always packed
            ("12302", "NDLS", "HWH",  "3A", W, None, None, 98),
            ("12302", "NDLS", "HWH",  "2A", W, None, None, 31),
            ("12302", "NDLS", "HWH",  "SL", W, None, None, 150),
            # Later boarding: seats free up
            ("12302", "CNB",  "HWH",  "3A", A, 12,   None, None),
            ("12302", "PRYJ", "HWH",  "3A", A, 8,    None, None),
            ("12302", "DDU",  "HWH",  "3A", A, 5,    None, None),
            ("12302", "GAYA", "HWH",  "3A", A, 17,   None, None),
            # Early detrain from Delhi
            ("12302", "NDLS", "CNB",  "3A", A, 6,    None, None),
            ("12302", "NDLS", "PRYJ", "3A", R, None, 8,    None),
            ("12302", "NDLS", "DDU",  "3A", R, None, 5,    None),
            # Intermediate hops
            ("12302", "CNB",  "PRYJ", "3A", A, 20,   None, None),
            ("12302", "DHN",  "HWH",  "3A", A, 25,   None, None),

            # ── 12724 Telangana Express ───────────────────────────────
            ("12724", "NDLS", "HYB",  "3A", W, None, None, 75),
            ("12724", "NDLS", "HYB",  "SL", W, None, None, 180),
            ("12724", "NDLS", "HYB",  "2A", W, None, None, 22),
            # Board at intermediate stations: open
            ("12724", "AGC",  "HYB",  "3A", A, 6,    None, None),
            ("12724", "VGLJ", "HYB",  "3A", A, 11,   None, None),
            ("12724", "VGLJ", "HYB",  "SL", A, 28,   None, None),
            ("12724", "BPL",  "HYB",  "3A", A, 8,    None, None),
            ("12724", "NGP",  "HYB",  "3A", A, 19,   None, None),
            # Detrain early
            ("12724", "NDLS", "NGP",  "3A", R, None, 7,    None),
            ("12724", "NDLS", "BPL",  "3A", R, None, 10,   None),
            ("12724", "NDLS", "VGLJ", "3A", A, 4,    None, None),
            # Short hop
            ("12724", "MTJ",  "AGC",  "3A", A, 30,   None, None),
            ("12724", "BPL",  "NGP",  "3A", A, 15,   None, None),

            # ── 12628 Karnataka Express ───────────────────────────────
            ("12628", "NDLS", "SBC",  "3A", W, None, None, 110),
            ("12628", "NDLS", "SBC",  "SL", W, None, None, 210),
            ("12628", "NDLS", "SBC",  "2A", W, None, None, 45),
            # Later boarding
            ("12628", "AGC",  "SBC",  "3A", A, 7,    None, None),
            ("12628", "VGLJ", "SBC",  "3A", A, 14,   None, None),
            ("12628", "VGLJ", "SBC",  "SL", A, 32,   None, None),
            ("12628", "BPL",  "SBC",  "3A", A, 9,    None, None),
            ("12628", "NGP",  "SBC",  "3A", A, 21,   None, None),
            ("12628", "GTL",  "SBC",  "3A", A, 11,   None, None),
            # Detrain early
            ("12628", "NDLS", "NGP",  "3A", R, None, 6,    None),
            ("12628", "NDLS", "BPL",  "3A", R, None, 9,    None),
            ("12628", "NZM",  "SBC",  "3A", W, None, None, 95),
            # Intermediate
            ("12628", "BPL",  "NGP",  "3A", A, 18,   None, None),
            ("12628", "NGP",  "GTL",  "3A", A, 12,   None, None),
        ]

        return {
            (train, source, destination, cls): (status, avail, rac, wl)
            for train, source, destination, cls, status, avail, rac, wl in rows
        }


MockRailwayDataProvider = MockRailwayProvider