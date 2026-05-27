from scraper import parse_float, parse_river_watch_html


def test_parse_float_handles_units_and_missing_values():
    assert parse_float("5.20 m") == 5.2
    assert parse_float("--") is None


def test_parse_river_watch_html_maps_table_headers():
    html = """
    <table>
      <thead>
        <tr>
          <th>Station No</th>
          <th>Basin</th>
          <th>Station Name</th>
          <th>District</th>
          <th>Water Level</th>
          <th>Warning Level</th>
          <th>Danger Level</th>
          <th>Trend</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>501</td>
          <td>Bagmati</td>
          <td>Bagmati River at Gaurighat</td>
          <td>Kathmandu</td>
          <td>3.45 m</td>
          <td>5.0 m</td>
          <td>6.8 m</td>
          <td>Rising</td>
          <td>Below Warning Level</td>
        </tr>
      </tbody>
    </table>
    """

    rows = parse_river_watch_html(html)

    assert rows == [
        {
            "station_no": "501",
            "basin_name": "Bagmati",
            "station_name": "Bagmati River at Gaurighat",
            "district_name": "Kathmandu",
            "water_level_m": 3.45,
            "warning_level_m": 5.0,
            "danger_level_m": 6.8,
            "trend": "Rising",
            "status": "Below Warning Level",
        }
    ]


def test_parse_river_watch_html_maps_realtime_stream_table():
    html = """
    <table>
      <thead>
        <tr>
          <th>S.No.</th>
          <th>Basin Name</th>
          <th>Station Index</th>
          <th>Station Name</th>
          <th>District Name</th>
          <th>Water Level (m)</th>
          <th>Discharge(m3/s)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td>Narayani</td>
          <td>445.3</td>
          <td>Ankhu Khola at Ankhu Bagar</td>
          <td>Dhading</td>
          <td>1.14</td>
          <td></td>
        </tr>
      </tbody>
    </table>
    """

    rows = parse_river_watch_html(html)

    assert rows[0]["station_no"] == "445.3"
    assert rows[0]["station_name"] == "Ankhu Khola at Ankhu Bagar"
    assert rows[0]["water_level_m"] == 1.14


def test_parse_river_watch_html_extracts_embedded_coordinates():
    html = """
    <script>
      var coordinates = [{
        "name": "Arun at Turkeghat",
        "stationIndex": "604.5",
        "basin": "Koshi",
        "district": "Sankhuwasabha",
        "waterLevel": {"value": 2.68620014191},
        "warning_level": "6",
        "danger_level": "",
        "steady": "STEADY",
        "status": "BELOW WARNING LEVEL"
      }];
    </script>
    """

    rows = parse_river_watch_html(html)

    assert rows[0]["station_no"] == "604.5"
    assert rows[0]["water_level_m"] == 2.68620014191
    assert rows[0]["warning_level_m"] == 6.0
    assert rows[0]["trend"] == "Steady"
