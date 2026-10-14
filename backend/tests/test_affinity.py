from artists import _MAX_RAW, _compute_scores


def _artists(*ids):
    return [{"id": i, "name": i.upper(), "images": [{"url": f"https://img/{i}"}], "genres": ["indie"]}
            for i in ids]


def test_max_raw_is_300():
    assert _MAX_RAW == 300


def test_number_one_in_every_window_scores_100():
    scores = _compute_scores({tr: _artists("a") for tr in ("short_term", "medium_term", "long_term")})
    assert scores["a"]["affinity"] == 100.0


def test_recent_listening_outweighs_long_term():
    scores = _compute_scores({
        "short_term":  _artists("recent"),
        "medium_term": [],
        "long_term":   _artists("old"),
    })
    # #1 short_term = 50*3 = 150 -> 50.0; #1 long_term = 50*1 = 50 -> 16.67
    assert scores["recent"]["affinity"] == 50.0
    assert scores["old"]["affinity"] == 16.67


def test_rank_position_decreases_score():
    scores = _compute_scores({"short_term": _artists("first", "second"), "medium_term": [], "long_term": []})
    assert scores["first"]["raw"] == 150
    assert scores["second"]["raw"] == 147


def test_contributions_sum_across_windows():
    scores = _compute_scores({
        "short_term":  _artists("x", "a"),       # a at idx 1 -> 49 * 3 = 147
        "medium_term": _artists("a"),            # a at idx 0 -> 50 * 2 = 100
        "long_term":   _artists("y", "z", "a"),  # a at idx 2 -> 48 * 1 = 48
    })
    assert scores["a"]["raw"] == 295
    assert scores["a"]["affinity"] == round(295 / 300 * 100, 2)


def test_missing_images_and_genres_tolerated():
    scores = _compute_scores({
        "short_term":  [{"id": "a", "name": "Artist A"}],
        "medium_term": [],
        "long_term":   [],
    })
    assert scores["a"]["name"] == "Artist A"
    assert scores["a"]["image_url"] is None
    assert scores["a"]["genres"] == []
