import httpx

import ticketmaster_client as tm


def _event(**overrides):
    event = {
        "id":   "ev1",
        "name": "Phoebe Bridgers: The Reunion Tour",
        "url":  "https://ticketmaster.example/ev1",
        "dates": {"start": {"dateTime": "2026-11-20T01:00:00Z"}},
        "priceRanges": [{"min": 45.0, "max": 120.0}],
        "_embedded": {
            "attractions": [{"name": "Phoebe Bridgers"}],
            "venues": [{"name": "The Salt Shed", "city": {"name": "Chicago"}, "state": {"stateCode": "IL"}}],
        },
    }
    event.update(overrides)
    return event


class TestMatchesArtist:
    def test_exact_attraction_match(self):
        assert tm._matches_artist(_event(), "Phoebe Bridgers")

    def test_case_and_whitespace_insensitive(self):
        assert tm._matches_artist(_event(), "  phoebe bridgers ")

    def test_tribute_act_with_different_attraction_is_rejected(self):
        event = _event(_embedded={"attractions": [{"name": "Moon Song: A Phoebe Tribute"}]})
        assert not tm._matches_artist(event, "Phoebe Bridgers")

    def test_any_matching_attraction_counts(self):
        event = _event(_embedded={"attractions": [{"name": "Opener"}, {"name": "Phoebe Bridgers"}]})
        assert tm._matches_artist(event, "Phoebe Bridgers")

    def test_falls_back_to_event_name_with_stricter_threshold(self):
        assert tm._matches_artist({"name": "Boygenius"}, "boygenius")
        assert not tm._matches_artist({"name": "Boygenius Karaoke Night"}, "boygenius")


class TestParseEvent:
    def test_full_event(self):
        assert tm._parse_event(_event()) == {
            "event_id":   "ev1",
            "event_name": "Phoebe Bridgers: The Reunion Tour",
            "venue_name": "The Salt Shed",
            "venue_city": "Chicago, IL",
            "event_date": "2026-11-20T01:00:00Z",
            "ticket_url": "https://ticketmaster.example/ev1",
            "price_min":  45.0,
            "price_max":  120.0,
        }

    def test_date_only_gets_midday_time(self):
        parsed = tm._parse_event(_event(dates={"start": {"localDate": "2026-12-01"}}))
        assert parsed["event_date"] == "2026-12-01T12:00:00Z"

    def test_missing_date_is_skipped(self):
        assert tm._parse_event(_event(dates={"start": {}})) is None

    def test_missing_venue_state_and_prices(self):
        event = _event(priceRanges=[], _embedded={"venues": [{"name": "Venue", "city": {"name": "London"}}]})
        parsed = tm._parse_event(event)
        assert parsed["venue_city"] == "London"
        assert parsed["price_min"] is None
        assert parsed["price_max"] is None


class TestFetchEvents:
    def test_no_api_key_returns_empty_without_calling_api(self, monkeypatch):
        def fail(*args, **kwargs):
            raise AssertionError("Ticketmaster should not be called without a key")

        monkeypatch.setenv("TICKETMASTER_API_KEY", "")
        monkeypatch.setattr(httpx, "get", fail)
        assert tm.fetch_events_for_artist("Anyone") == []

    def test_filters_non_matching_events_and_passes_location(self, monkeypatch):
        captured = {}

        def fake_get(url, params, timeout):
            captured.update(params)
            body = {"_embedded": {"events": [
                _event(),
                _event(id="ev2", _embedded={"attractions": [{"name": "Somebody Else"}]}),
            ]}}
            return httpx.Response(200, json=body, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx, "get", fake_get)
        results = tm.fetch_events_for_artist("Phoebe Bridgers", 41.88, -87.63)
        assert [r["event_id"] for r in results] == ["ev1"]
        assert captured["latlong"] == "41.88,-87.63"
        assert captured["keyword"] == "Phoebe Bridgers"

    def test_http_error_returns_empty(self, monkeypatch):
        def fake_get(url, params, timeout):
            return httpx.Response(429, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx, "get", fake_get)
        assert tm.fetch_events_for_artist("Phoebe Bridgers") == []
