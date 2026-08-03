# US Demographic Reports for QGIS

[![QGIS Version](https://img.shields.io/badge/QGIS-3.40+-green.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

Professional demographic reporting plugin for QGIS. Generate reports and datafills from US Census block group data with accurate spatial aggregation and professional formatting.

## Features

### Point Reports
- Click anywhere on the map to select a location
- Choose your analysis type:
  - **Radius (miles)** — up to 3 cumulative rings (e.g. 1, 3, and 5 miles)
  - **Drive time (minutes)** — up to 3 cumulative drive-time areas (e.g. 5, 10, and 15 minutes) via a [Valhalla](https://github.com/valhalla/valhalla) routing server (see [Drive-Time Reports](#drive-time-reports))
- Generate professional PDF reports with:
  - Proper formatting (currency, percentages, years)
  - Custom branding (logo and company colors)
  - Organized by demographic categories
  - One column per radius, side by side, for easy comparison
  - Metadata about the analysis area

### Polygon Datafill
- Aggregate block group data into custom polygon boundaries
- Export to CSV
- Proportional area allocation for accurate results
- Progress indicator for large datasets

### Smart Calculations
- **Densities**: Population and household density per square mile
- **Weighted Averages**: Median age, average household income
- **Growth Rates**: Population growth calculations
- **Aggregate Values**: Total income, average household size

### Data Package Support
- **Basic Package**: Core demographic variables
- **Expanded Package**: Additional demographic detail
- **Professional Package**: Complete dataset

## Requirements

- **QGIS**: 3.40 or higher (Bratislava or newer)
- **Python**: 3.10+ (included with QGIS)
- **ReportLab**: For PDF generation (installation instructions below)

## Installation

### From QGIS Plugin Repository (Recommended)

1. Open QGIS
2. Go to **Plugins → Manage and Install Plugins**
3. Search for "US Demographic Reports"
4. Click **Install Plugin**

### From ZIP File

1. Download the latest release from [GitHub Releases](https://github.com/retailgravity/qgis-demographic-reports/releases)
2. In QGIS, go to **Plugins → Manage and Install Plugins**
3. Click **Install from ZIP**
4. Select the downloaded ZIP file
5. Click **Install Plugin**

### Installing ReportLab

The plugin requires ReportLab for PDF generation. Install it using:

**Windows:**
1. Open **OSGeo4W Shell** (search in Start menu)
2. Run:
```bash
python -m pip install reportlab
```

**Mac:**
```bash
/Applications/QGIS.app/Contents/MacOS/bin/python3 -m pip install reportlab
```

**Linux:**
```bash
python3 -m pip install reportlab
```

## Usage

### Preparing Your Data

Your demographic data should be joined to a block group geography layer:
- **Format**: GeoPackage (.gpkg) or Shapefile
- **Geometry**: Polygon (block groups)
- **CRS**: Any (plugin handles transformations)
- **Required Fields**: See [Data Requirements](#data-requirements)

### Generating a Point Report

1. Click the plugin icon in the toolbar
2. Select the **Point Report** tab
3. Choose your data package tier
4. Select your block group layer from the dropdown
5. Leave **Analysis type** on **Radius (miles)** (the default)
6. Click **Select Point on Map**
7. Click anywhere on the map
8. Enter Radius 1 in miles (e.g., `1.0` for 1 mile). Optionally enter Radius 2 and/or Radius 3 for additional cumulative rings (e.g., `3.0`, `5.0`) — each radius must be larger than the last
9. Click **Generate Report**
10. Choose to save as PDF or view in browser — results are shown side by side, one column per radius

### Drive-Time Reports

Instead of straight-line radii, you can analyze **drive-time areas** (isochrones) — the area reachable by car within a given number of minutes. This uses a [Valhalla](https://github.com/valhalla/valhalla) routing server.

**One-time setup:** enter a Valhalla server URL in the **Drive-time server URL** field on the Point Report tab (it is saved for future sessions). See [Routing server options](#routing-server-options) below.

**To generate a drive-time report:**

1. Set **Analysis type** to **Drive time (minutes)**
2. Choose your data package and block group layer as usual
3. Click **Select Point on Map** and click a location
4. Enter Drive time 1 in minutes (e.g., `5`). Optionally add Drive time 2 and/or 3 (e.g., `10`, `15`) — each must be larger than the last
5. Click **Generate Report** — one column per drive-time area, side by side

The drive-time polygons feed the same proportional-area aggregation as radii, so results are cumulative in exactly the same way.

#### Routing server options

The routing-server URL is **not set by default**. Choose one of:

- **Run your own Valhalla server** (recommended for regular or bulk use, and required for high volume). See the [Valhalla Docker quick-start](https://github.com/gis-ops/docker-valhalla). Point the plugin at your own server's URL (e.g. `http://localhost:8002`).
- **Use the public FOSSGIS demo server** (`https://valhalla1.openstreetmap.de`) for light, personal use. This is a free, volunteer-funded service with a **fair-use limit of ~1 request per second**. Please read and respect the [current usage policy](https://valhalla.github.io/valhalla/#demo-server). Do **not** point automated/bulk workflows at it, and do not redistribute this plugin pre-configured to use it for other people — run your own server for anything beyond occasional personal reports.

This plugin identifies its requests with an `X-Client-Id` header and throttles itself to at most one routing request per second.

**Attribution:** Drive-time areas are derived from © OpenStreetMap contributors (road network, ODbL) via the Valhalla routing engine, hosted by FOSSGIS e.V. when the public demo server is used. This attribution is printed on drive-time reports.

### Generating a Datafill

1. Select the **Layer Datafill** tab
2. Choose your data package tier
3. Select your block group layer
4. Select your target polygon layer
5. Click **Browse** to choose output CSV location
6. Click **Generate Datafill**
7. Wait for processing (progress bar shows status)

### Customizing PDF Reports

Edit `pdf_generator.py` to customize:
- Company name
- Website URL
- Logo (place your logo as `my_company_logo.png` in plugin folder)
- Brand color (hex code)

```python
generator = DemographicPDFGenerator(
    logo_path="my_company_logo.png",
    company_name="Your Organization",
    website="www.yourwebsite.com",
    brand_color="#3498db"
)
```

## Data Requirements

### Required Base Fields

Your block group layer must include these fields for calculations to work:

```
CY_POP          - Current Year Population
CY_MPOP         - Male Population
CY_FPOP         - Female Population
FY_POP          - Future Year Population (5-year projection)
CY_HOUSEHOLDS   - Current Year Households
LAND_AREA       - Land Area (in square miles)
CY_MEDAGE       - Median Age
CY_MMEDAGE      - Median Male Age
CY_FMEDAGE      - Median Female Age
CY_AVGHHINC     - Average Household Income
CY_MEDHHINC     - Median Household Income
CY_MEDYEAR      - Median Year Structure Built
```

### Calculated Fields

These fields are computed automatically:
- `POP_DENSITY` = CY_POP / LAND_AREA
- `HH_DENSITY` = CY_HOUSEHOLDS / LAND_AREA
- `POP_GROWTH` = (FY_POP - CY_POP) / CY_POP
- `CY_AVGHHSIZE` = CY_POP / CY_HOUSEHOLDS
- `CY_AGGINCOME` = CY_HOUSEHOLDS × CY_AVGHHINC

Weighted averages (by population or households):
- `CY_MEDAGE`, `CY_MMEDAGE`, `CY_FMEDAGE`
- `CY_AVGHHINC`, `CY_MEDHHINC`, `CY_MEDYEAR`

## Methodology

### Proportional Area Allocation

The plugin uses accurate spatial aggregation:

1. **For each block group** that intersects your analysis area:
   - Calculate the percentage of overlap
   - If 60% of a block group is within the area, it contributes 60% of its values

2. **Sum proportional values** for all intersecting block groups

3. **Calculate derived fields** after aggregation:
   - Densities use total population ÷ total area
   - Weighted averages use appropriate weights
   - Growth rates use proportional totals

### Performance Optimization

- **Spatial indexing** for faster intersection tests
- **Bounding box filtering** before precise calculations
- **Progress indicators** for long-running operations

## Configuration

### Package Tiers

Edit `package_config.py` to define your data packages:

```python
BASIC_VARIABLES = [
    'BGID', 'CY_POP', 'CY_HOUSEHOLDS', ...
]

EXPANDED_VARIABLES = [
    # All basic variables plus:
    'CY_MEDAGE', 'CY_AVGHHINC', ...
]

PROFESSIONAL_VARIABLES = [
    # All variables
]
```

### Variable Categories

Organize variables into categories for better report layout:

```python
VARIABLE_CATEGORIES = {
    'POPULATION': ['CY_POP', 'CY_MPOP', 'CY_FPOP'],
    'HOUSEHOLDS': ['CY_HOUSEHOLDS', 'CY_AVGHHINC'],
    'DENSITY': ['POP_DENSITY', 'HH_DENSITY'],
    # ...
}
```

## Output Formats

### PDF Reports
- Professional formatting with branding
- Currency: `$65,432`
- Percentages: `5.25%`
- Years: `1998`
- Decimals based on variable type

### CSV Files
- Metadata header (commented lines)
- Proper rounding per variable
- UTF-8 encoding
- Standard CSV format

## Troubleshooting

### "ReportLab not found"
Install ReportLab using the instructions above, then restart QGIS.

### "No block groups intersecting"
- Check that layers have valid CRS
- Verify layers overlap spatially
- Try a larger radius

### "Missing required fields"
Your data is missing required demographic variables. Check the [Data Requirements](#data-requirements) section.

### Slow performance
- Use smaller analysis areas
- Enable spatial index (plugin does this automatically)
- Use GeoPackage instead of Shapefile

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/retailgravity/qgis-demographic-reports.git

# Link to QGIS plugins directory (Windows example)
mklink /D "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\demographic_reports" "path\to\repo"

# Reload plugin in QGIS using Plugin Reloader
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

This means you are free to:
- Use the plugin for any purpose
- Modify the source code
- Distribute the plugin
- Distribute your modifications

Under the conditions that:
- You disclose the source code
- You license your modifications under GPL v3
- You include the original copyright notice

## Credits

Developed by Brad Thomas @ Retail Gravity

Special thanks to:
- QGIS Development Team
- ReportLab developers
- Demographic data sources: U.S. Census, American Community Survey (ACS) estimates, Public Use Microdata Samples (PUMS), OpenStreetMap (OSM) for geospatial features, and the Multi-Resolution Land Characteristics (MRLC) Consortium for land cover classifications and annual change.

## Support

- **Issues**: [GitHub Issues](https://github.com/retailgravity/qgis-demographic-reports/issues)
- **Discussions**: [GitHub Discussions](https://github.com/retailgravity/qgis-demographic-reports/discussions)
- **Email**: brad@retailgravity.com

## Changelog

### Version 1.2.0 (2026-08-03)
- Point reports can now use **drive-time areas** (Valhalla isochrones) as an alternative to radii — up to 3 cumulative drive times, side by side
- Routing-server URL is a configurable setting; ships un-set (opt-in) and self-throttles to respect fair-use limits
- Drive-time reports include OpenStreetMap/Valhalla/FOSSGIS attribution

### Version 1.1.0 (2026-08-01)
- Point reports now support up to 3 radii (cumulative rings) instead of a single radius
- PDF and in-app reports lay out multi-radius results as side-by-side columns

### Version 1.0.0 (2026-01-27)
- Initial release
- Point-based reporting with customizable radius
- Polygon datafill with proportional allocation
- PDF report generation with custom branding
- CSV export
- Support for three data package tiers
- Calculated fields (densities, weighted averages, growth)
- Spatial indexing for performance

## Roadmap

Future enhancements may include:
- Bulk PDF reports
- Multiple output format options
- Bulk processing from point list
- Comparison reports between areas

## Citation

If you use this plugin in research or publications, please cite:

```
Retail Gravity (2026). US Demographic Reports for QGIS (Version 1.0.0) [Computer software].
https://github.com/retailgravity/qgis-demographic-reports
```
