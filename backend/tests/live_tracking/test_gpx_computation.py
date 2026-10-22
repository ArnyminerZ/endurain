from datetime import UTC, datetime

import modules.live_tracking.gpx_computation as gpx_computation
import modules.live_tracking.schema as live_tracking_schema


def _read(lat, lon, second, **extra):
    return live_tracking_schema.LivePointRead(
        recorded_at=datetime(2026, 10, 22, 8, 0, second, tzinfo=UTC), latitude=lat, longitude=lon, **extra
    )


class TestBuildGpx:
    def test_contains_track_metadata_and_points(self):
        xml = gpx_computation.build_gpx([_read(39.1, -0.5, 0, elevation=12.5), _read(39.2, -0.5, 10)], "Morning", "Run")
        assert "<name>Morning</name>" in xml
        assert "<type>Run</type>" in xml
        assert 'lat="39.1" lon="-0.5"' in xml
        assert "<ele>12.5</ele>" in xml
        assert "2026-10-22T08:00:10+00:00" in xml

    def test_sensors_use_garmin_extension(self):
        xml = gpx_computation.build_gpx([_read(39.1, -0.5, 0, heart_rate=140, cadence=80)], None, "Ride")
        assert "<gpxtpx:hr>140</gpxtpx:hr>" in xml
        assert "<gpxtpx:cad>80</gpxtpx:cad>" in xml
        assert "<name>" not in xml

    def test_temperature_is_written_but_skin_temperature_is_not(self):
        xml = gpx_computation.build_gpx([_read(39.1, -0.5, 0, temperature=18.5, skin_temperature=33.1)], None, "Run")
        assert "<gpxtpx:atemp>18.5</gpxtpx:atemp>" in xml
        assert "33.1" not in xml

    def test_user_text_is_escaped(self):
        xml = gpx_computation.build_gpx([_read(1, 1, 0)], "A & <B>", "Run")
        assert "A &amp; &lt;B&gt;" in xml

    def test_parses_with_the_ingestion_parser(self, tmp_path):
        import gpxpy

        points = [_read(39.0 + i * 0.001, -0.5, i * 10, heart_rate=120) for i in range(4)]
        gpx = gpxpy.parse(gpx_computation.build_gpx(points, "T", "Run"))
        assert len(gpx.tracks[0].segments[0].points) == 4
        assert gpx.tracks[0].type == "Run"
