"""Section 7.3 (v2 addendum) — config validation at startup.

Validates config.yaml against an explicit expected-keys/types schema and
fails loud with a specific, actionable message (which key, what was
expected) instead of silently misbehaving on a bad value.
"""

NUMBER = (int, float)

# section -> key -> (type(s), predicate or None)
SCHEMA: dict = {
    "correlation": {
        "same_window_similarity_threshold": (NUMBER, lambda v: 0 < v <= 1),
        "historical_similarity_threshold": (NUMBER, lambda v: 0 < v <= 1),
        "same_window_max_gap_hours": (NUMBER, lambda v: v > 0),
        "geo_overlap_radius_km": (NUMBER, lambda v: v > 0),
        "near_duplicate_similarity_threshold": (NUMBER, lambda v: 0 < v <= 1),
        "entity_alias_fuzzy_match_floor": (NUMBER, lambda v: 0 < v <= 1),
        "entity_overlap_boost": (NUMBER, lambda v: 0 <= v < 0.5),
    },
    "instability": {
        "weight_volume": (NUMBER, lambda v: 0 <= v <= 1),
        "weight_severity": (NUMBER, lambda v: 0 <= v <= 1),
        "weight_spread": (NUMBER, lambda v: 0 <= v <= 1),
        "recompute_interval_seconds": (NUMBER, lambda v: v >= 30),
        "rolling_window_hours": (NUMBER, lambda v: v > 0),
        "recalibration_pending": (bool, None),                         # v6 §22
        "baseline_divisor": (NUMBER, lambda v: v >= 1),                # v6 §22
    },
    "ingestion_intervals_seconds": {},   # any source-type -> positive number
    "map": {
        "cluster_pin_threshold": (int, lambda v: v > 0),
        "cluster_radius_km": (NUMBER, lambda v: v > 0),
    },
    "resilience": {
        "max_backoff_seconds": (NUMBER, lambda v: v > 0),
        "backoff_multiplier": (NUMBER, lambda v: v >= 1),
    },
    "graphics": {
        "quality_tier": (str, lambda v: v in ("standard", "high", "ultra")),
        "idle_tour_seconds": (NUMBER, lambda v: v == 0 or v >= 5),   # v6.6.6 — 0 disables idle auto-rotation
        "ambient_sound_default": (bool, None),
    },
    "ops": {},          # nested; validated below
    "briefing": {
        "daily_briefing_hour_utc": (int, lambda v: 0 <= v <= 23),
        "top_n_stories": (int, lambda v: v > 0),
    },
    "predictions": {
        "resolve_interval_seconds": (NUMBER, lambda v: v >= 60),
        "batch_size": (int, lambda v: v > 0),
    },
    "second_order": {
        "scan_interval_seconds": (NUMBER, lambda v: v >= 60),
        "max_pairs_per_scan": (int, lambda v: v > 0),
        "min_shared_entities": (int, lambda v: v >= 1),
    },
    "gazetteer": {
        "dataset": (str, lambda v: v in ("cities15000", "cities1000", "allCountries")),
        "min_population_threshold": (int, lambda v: v >= 0),
    },
    # --- v3 legendary tier (§25) ---
    "debate": {
        "personas": (list, lambda v: len(v) >= 2 and all(isinstance(x, str) for x in v)),
        "disagreement_flag_threshold": (NUMBER, lambda v: 0 < v <= 1),
    },
    "devils_advocate": {
        "enabled": (bool, None),
    },
    "embedding": {
        "model_name": (str, lambda v: len(v) > 0),
    },
    "self_tuning": {
        "adjustment_step": (NUMBER, lambda v: 0 < v < 0.1),
        "min_threshold": (NUMBER, lambda v: 0 < v < 1),
        "max_threshold": (NUMBER, lambda v: 0 < v <= 1),
        "aggregation_interval_hours": (NUMBER, lambda v: v > 0),
    },
    "anomaly": {
        "zscore_window_days": (NUMBER, lambda v: v > 0),
        "zscore_flag_threshold": (NUMBER, lambda v: v > 0),
        "cusum_enabled": (bool, None),
    },
    "forecasting": {
        "enabled": (bool, None),
        "min_resolved_predictions_for_high_confidence": (int, lambda v: v >= 0),
        "calibration_brier_ceiling": ((int, float), lambda v: 0 < v <= 1),
        "calibration_min_graded": (int, lambda v: v >= 1),
        "auto_enable_earned": (bool, None),
        "default_horizon_hours": (int, lambda v: v > 0),
    },
    "satellite_overlay": {
        "tle_refresh_interval_hours": (NUMBER, lambda v: v > 0),
    },
    "provenance": {
        "hash_chain_enabled": (bool, None),
    },
    "geopolitical_entities": {
        "wikidata_refresh_interval_hours": (NUMBER, lambda v: v > 0),
        "agenda_synthesis_interval_hours": (NUMBER, lambda v: v > 0),
        "trade_stats_refresh_interval_hours": (NUMBER, lambda v: v > 0),
        "conflict_autotag_confidence_floor": (NUMBER, lambda v: 0 < v <= 1),
        "bilateral_relations_refresh_interval_hours": (NUMBER, lambda v: v > 0),
        "election_triggered_leadership_refresh": (bool, None),
    },
    # --- v4 (manual §26) ---
    "globe": {
        "hit_test_use_facing_occlusion": (bool, None),
        "cluster_screen_distance_px": (NUMBER, lambda v: 0 < v <= 300),
        "boundary_resolution": (str, lambda v: v in ("10m", "50m", "110m")),
        "boundary_resolution_far_zoom": (str, lambda v: v in ("10m", "50m", "110m")),
        "terrain_texture_enabled": (bool, None),                        # v5 §8
        "beacon_render_mode": (str, lambda v: v in ("sdf", "sprite")),  # v5 §16
    },
    "geocoding": {
        "min_confidence_for_solid_marker": (NUMBER, lambda v: 0 <= v <= 1),
    },
    "map2d": {
        "wraparound_enabled": (bool, None),
        # city_label_min_population_by_zoom validated below (nested map)
    },
    "entity_completeness": {
        "reference_country_count": (int, lambda v: v > 0),
        "completeness_warning_tolerance": (int, lambda v: v >= 0),
    },
    "relevance": {
        "global_relevance_default_filter": (bool, None),
        "global_relevance_floor": (NUMBER, lambda v: 0 <= v <= 1),
    },
    "audio": {
        "master_gain_default": (NUMBER, lambda v: 0 <= v <= 1),
        "preset": (str, lambda v: v in (
            "ambient_default", "vaporwave", "dune", "metal", "technohouse",
            "numbers_station", "berlin_industrial", "war_room_orchestral",
            "data_sonification", "modal_drift", "arctic_calm",
            "crystalline_chimes", "deep_glacier", "aurora_drift")),  # v6.1
        "presets_active": (list, lambda v: all(isinstance(x, str) for x in v)),  # v6 §17
    },
    "sourcing": {
        "historical_backfill_on_entity_add": (bool, None),
        "dynamic_polling_by_conflict_activity": (bool, None),
    },
    "external_content": {
        "wikipedia_enabled": (bool, None),
        "grokipedia_enabled": (bool, None),
        "refresh_interval_hours": (NUMBER, lambda v: v > 0),
        "entities_per_cycle": (int, lambda v: v > 0),
    },
    "onboarding": {
        "require_ai_key_before_first_run": (bool, None),
    },
    "analyst_panel_fixes": {
        "clear_focus_on_panel_close": (bool, None),
        "focus_staleness_timeout_seconds": (NUMBER, lambda v: v > 0),
        "question_text_takes_precedence_over_focus": (bool, None),
        "conflict_token_strip_generic_words": (bool, None),
        "conflict_alias_individual_parties": (bool, None),
    },
    "panes": {
        "transition_duration_ms": (NUMBER, lambda v: 0 <= v <= 2000),
        "respect_prefers_reduced_motion": (bool, None),
    },
    "annotations": {
        "enabled": (bool, None),
    },
    "alerts": {
        "in_app_breaking_alert_severity_floor": (int, lambda v: 1 <= v <= 5),
    },
    "coverage": {
        "thin_coverage_story_floor": (int, lambda v: v >= 0),
    },
    "prognosis": {
        "horizon_hours": (int, lambda v: v > 0),
        "refresh_interval_hours": (NUMBER, lambda v: v > 0),
    },
    # --- v5 (manual §22) ---
    "content": {
        "strip_links_from_titles": (bool, None),
    },
    "source_quality": {
        "reliability_tiers_enabled": (bool, None),
        "gdelt_events_enabled": (bool, None),                          # v6 §2
        "gdelt_cloud_enabled": (bool, None),                           # v6 §2
    },
    "conflict_tagging": {
        "development_types": (list, lambda v: all(isinstance(x, str) for x in v)),
        "conflict_tab_filter": (str, lambda v: v in ("conflict", "military")),
    },
    "panels": {
        "resizable": (bool, None),
        "min_width_px": (int, lambda v: v > 0),
        "max_width_px": (int, lambda v: v > 0),
        "persist_across_restarts": (bool, None),
    },
    "themes": {
        "available": (list, lambda v: len(v) >= 1 and all(isinstance(x, str) for x in v)),
    },
    "llm_provider": {
        "primary": (str, lambda v: len(v) > 0),
        "fallback_order": (list, lambda v: all(isinstance(x, str) for x in v)),
        "groq_model": (str, lambda v: len(v) > 0),                     # v6 §1
        "ollama_model": (str, lambda v: len(v) > 0),                   # v6.5
        "ollama_timeout_floor_seconds": (NUMBER, lambda v: v > 0),     # v6.5
        "causal_link_override": (str, None),                           # v6 §1
    },
    "leadership_data": {
        "staleness_warning_days": (NUMBER, lambda v: v > 0),
    },
    "analyst_panel": {
        "enabled": (bool, None),
        "auto_navigate_default": (bool, None),
        "min_confidence_to_navigate": (str, lambda v: v in ("high", "medium", "low")),
        "model": (str, lambda v: len(v) > 0),
        "max_context_stories_per_query": (int, lambda v: v > 0),
        "freeform_retrieval_lookback_days": (NUMBER, lambda v: v > 0),
        "embedding_scan_limit": (int, lambda v: v > 0),          # v6.2
        "embedding_retrieval_enabled": (bool, None),             # v6.3
        "answer_max_tokens": (int, lambda v: v > 0),             # v6.3
        "answer_timeout_seconds": (NUMBER, lambda v: v > 0),     # v6.3
        "empty_retrieval_response": (str, None),
        "session_history_retention": (str, None),
        "conversation_history_turns": (int, lambda v: v >= 0),
        "web_search_enabled": (bool, None),
        "web_search_max_results": (int, lambda v: v >= 0),
        "live_verify_on_hot_path": (bool, None),                 # v6.2
        "include_causal_narrative_in_context": (bool, None),
    },
    # ----- v6.4.1 — LLM transport hardening -----
    "network": {
        "dns_cache_ttl_seconds": (NUMBER, lambda v: v > 0),
        "request_deadline_buffer_seconds": (NUMBER, lambda v: v >= 0),
        "prefer_ipv4": (bool, None),
    },
    # ----- v6 (manual §32) -----
    "translation": {
        "instant_translate_on_arrival": (bool, None),
        "cache_by_content_and_language": (bool, None),
    },
    "war_mode": {
        "enabled": (bool, None),
    },
    "map_rendering": {
        "tile_based_2d": (bool, None),
        "tile_size_deg": (NUMBER, lambda v: 1 <= v <= 90),
    },
    "accuracy": {
        "web_search_verification_enabled": (bool, None),
        "search_provider": (str, lambda v: len(v) > 0),
    },
    "ui": {
        "vr_button_visible": (bool, None),
        "city_lights_enabled_default": (bool, None),
        "wordmark_transliteration": (bool, None),
        "terrain_button_visible": (bool, None),   # v6.1.1
    },
    # v7 Part 6 — historical backfill
    "backfill": {
        "enabled": (bool, None),
        "days": (int, lambda v: 1 <= v <= 3650),
        "days_per_tick": (int, lambda v: 1 <= v <= 60),
        "max_events_per_day": (int, lambda v: 1 <= v <= 200),
        "tick_interval_seconds": ((int, float), lambda v: v >= 10),
    },
}


class ConfigError(SystemExit):
    pass


def _fail(msg: str):
    raise ConfigError(f"config.yaml invalid: {msg}")


def validate_config(config: dict) -> None:
    for section, keys in SCHEMA.items():
        if section not in config:
            _fail(f"missing section '{section}'")
        block = config[section]
        if not isinstance(block, dict):
            _fail(f"section '{section}' must be a mapping, got {type(block).__name__}")
        for key, (types, pred) in keys.items():
            if key not in block:
                _fail(f"missing key '{section}.{key}'")
            value = block[key]
            if isinstance(value, bool) and types is not bool and bool not in (
                    types if isinstance(types, tuple) else (types,)):
                _fail(f"'{section}.{key}' must be {types}, got bool")
            if not isinstance(value, types):
                expected = getattr(types, "__name__", "/".join(t.__name__ for t in types))
                _fail(f"'{section}.{key}' must be {expected}, got "
                      f"{type(value).__name__} ({value!r})")
            if pred and not pred(value):
                _fail(f"'{section}.{key}' value {value!r} out of allowed range")

    for stype, interval in config["ingestion_intervals_seconds"].items():
        if not isinstance(interval, (int, float)) or interval <= 0:
            _fail(f"'ingestion_intervals_seconds.{stype}' must be a positive number,"
                  f" got {interval!r}")

    ops = config["ops"]
    budgets = ops.get("daily_request_budgets")
    if not isinstance(budgets, dict):
        _fail("'ops.daily_request_budgets' must be a mapping of source-name -> int")
    for name, budget in budgets.items():
        if not isinstance(budget, int) or budget < 0:
            _fail(f"'ops.daily_request_budgets.{name}' must be a non-negative int,"
                  f" got {budget!r}")
    zooms = config["map2d"].get("city_label_min_population_by_zoom")
    if not isinstance(zooms, dict) or not all(
            isinstance(zooms.get(k), int) and zooms[k] >= 0
            for k in ("far", "mid", "near")):
        _fail("'map2d.city_label_min_population_by_zoom' must map far/mid/near"
              " to non-negative ints")

    backup = ops.get("db_backup")
    if not isinstance(backup, dict):
        _fail("'ops.db_backup' must be a mapping")
    for key, kind in (("keep_last_n", int), ("backup_dir", str), ("backup_hour_utc", int)):
        if key not in backup or not isinstance(backup[key], kind):
            _fail(f"'ops.db_backup.{key}' must be {kind.__name__}")
