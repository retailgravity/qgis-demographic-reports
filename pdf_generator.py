# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 05:58:19 2026

@author: brad@retailgravity.com
"""

"""
PDF report generator for demographic reports.

Produces a branded, client-facing demographic report. The layout adapts to the
number of analysis areas (radii or drive times):

  * 1 area  -> a headline "Market Snapshot" strip of stat tiles, then two-column
               category tables that use the full page width.
  * 2-3 areas -> a "Market Snapshot" comparison grid (stats as rows, areas as
               columns), then full-width category tables with one value column
               per area, read side by side.

A branded header (logo + accent rule) and a footer with page numbers are painted
on every page by an onPage canvas callback.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Flowable,
    FrameBreak,
    KeepTogether,
    NextPageTemplate,
)
from datetime import datetime
import os

# ---------------------------------------------------------------------------
# Palette (matches the Retail Gravity brand)
# ---------------------------------------------------------------------------
NAVY = colors.HexColor('#182839')
GREY = colors.HexColor('#64748B')
LGREY = colors.HexColor('#E2E8F0')
ZEBRA = colors.HexColor('#F8FAFC')
TILE = colors.HexColor('#F1F5F9')

# Page geometry (points; letter = 612 x 792)
PAGE_W, PAGE_H = letter
MARGIN = 36            # 0.5"
HEADER_H = 60          # top band: logo + accent rule
FOOTER_H = 26
COL_GAP = 18           # gap between the two columns in single-area layout

# Headline stats for the Market Snapshot (shown if present in the results).
SNAPSHOT_STATS = [
    ('CY_POP', 'Population'),
    ('CY_HOUSEHOLDS', 'Households'),
    ('CY_MEDHHINC', 'Median HH Income'),
    ('CY_MEDAGE', 'Median Age'),
    ('POP_GROWTH', '5-Yr Growth'),
    ('CY_AVGHHSIZE', 'Avg HH Size'),
]


class _KPIBand(Flowable):
    """A full-width row of headline stat tiles (single-area snapshot)."""

    def __init__(self, tiles, width, accent):
        super().__init__()
        self.tiles = tiles
        self.width = width
        self.accent = accent
        self.height = 66

    def wrap(self, avail_w, avail_h):
        return self.width, self.height

    def draw(self):
        c = self.canv
        n = len(self.tiles)
        if n == 0:
            return
        gap = 8
        tw = (self.width - gap * (n - 1)) / n
        th = 58
        y = self.height - th - 6
        for i, (val, lbl) in enumerate(self.tiles):
            x = i * (tw + gap)
            c.setFillColor(TILE)
            c.setStrokeColor(LGREY)
            c.setLineWidth(0.6)
            c.roundRect(x, y, tw, th, 5, fill=1, stroke=1)
            c.setFillColor(self.accent)
            c.rect(x, y + th - 3, tw, 3, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont('Helvetica-Bold', 15)
            c.drawCentredString(x + tw / 2, y + 26, val)
            c.setFillColor(GREY)
            c.setFont('Helvetica', 6.3)
            c.drawCentredString(x + tw / 2, y + 12, lbl.upper())


class DemographicPDFGenerator:
    """
    Generates professional PDF reports for demographic data.
    """
    def __init__(self, logo_path=None, company_name="Retail Gravity",
                 website="www.retailgravity.com", brand_color="#3498db"):
        """
        Initialize the PDF generator with custom branding.

        Args:
            logo_path: str - Path to company logo image file (PNG, JPG)
            company_name: str - Your company name for the footer
            website: str - Your website URL for the footer
            brand_color: str - Hex accent color (used for the header rule and
                stat-tile caps)
        """
        self.logo_path = logo_path
        self.company_name = company_name
        self.website = website
        self.accent = colors.HexColor(brand_color)
        self._build_styles()

    def _build_styles(self):
        """Paragraph styles used across the report."""
        self.styles = {
            'title': ParagraphStyle(
                'title', fontName='Helvetica-Bold', fontSize=22, textColor=NAVY,
                alignment=TA_LEFT, spaceAfter=2, leading=24),
            'meta': ParagraphStyle(
                'meta', fontName='Helvetica', fontSize=8.5, textColor=GREY,
                alignment=TA_LEFT, leading=12),
            'cell': ParagraphStyle(
                'cell', fontName='Helvetica', fontSize=7.6, textColor=NAVY,
                leading=9),
            'cell_r': ParagraphStyle(
                'cell_r', fontName='Helvetica-Bold', fontSize=7.6, textColor=NAVY,
                leading=9, alignment=TA_RIGHT),
            'head': ParagraphStyle(
                'head', fontName='Helvetica-Bold', fontSize=7.8,
                textColor=colors.white, leading=9),
            'head_r': ParagraphStyle(
                'head_r', fontName='Helvetica-Bold', fontSize=7.8,
                textColor=colors.white, leading=9, alignment=TA_RIGHT),
            'snap_lbl': ParagraphStyle(
                'snap_lbl', fontName='Helvetica', fontSize=8, textColor=GREY,
                leading=9.5),
            'snap_val': ParagraphStyle(
                'snap_val', fontName='Helvetica-Bold', fontSize=10.5,
                textColor=NAVY, leading=12, alignment=TA_RIGHT),
            'attribution': ParagraphStyle(
                'attribution', fontName='Helvetica-Oblique', fontSize=6.8,
                textColor=GREY, leading=8.5),
        }

    def _clean_description(self, description):
        """Remove common estimate-period prefixes from a variable description."""
        prefixes_to_remove = [
            "Current Year Estimate: ",
            "Future 5-Year Estimate: ",
            "Current Year estimate: ",
            "Future 5-Year estimate: ",
        ]
        cleaned = description
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        return cleaned

    # -- page chrome (header + footer), painted on every page -----------------
    def _draw_chrome(self, canvas, doc):
        canvas.saveState()
        # Logo, left-aligned in the header band
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img = ImageReader(self.logo_path)
                iw, ih = img.getSize()
                h = 34.0
                w = iw * (h / ih)
                canvas.drawImage(img, MARGIN, PAGE_H - MARGIN - h + 2,
                                 width=w, height=h, mask='auto',
                                 preserveAspectRatio=True)
            except Exception as e:
                print(f"Warning: Could not load logo: {e}")
        # Header rule: navy full-width line with a short accent underline
        rule_y = PAGE_H - MARGIN - HEADER_H + 8
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.4)
        canvas.line(MARGIN, rule_y, PAGE_W - MARGIN, rule_y)
        canvas.setStrokeColor(self.accent)
        canvas.setLineWidth(1.4)
        canvas.line(MARGIN, rule_y - 1.6, MARGIN + 120, rule_y - 1.6)
        # Footer
        canvas.setStrokeColor(LGREY)
        canvas.setLineWidth(0.75)
        canvas.line(MARGIN, MARGIN + FOOTER_H, PAGE_W - MARGIN, MARGIN + FOOTER_H)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(MARGIN, MARGIN + 10,
                          f"{self.company_name}   |   {self.website}")
        canvas.drawRightString(
            PAGE_W - MARGIN, MARGIN + 10,
            "Generated %s   |   Page %d"
            % (datetime.now().strftime("%B %d, %Y"), doc.page))
        canvas.restoreState()

    # -- Market Snapshot ------------------------------------------------------
    def _snapshot_tiles(self, results, usable_w):
        """Single-area headline stat tiles."""
        from .formatting_utils import format_value_for_display
        tiles = [
            (format_value_for_display(var, results[var]), label)
            for var, label in SNAPSHOT_STATS if var in results
        ]
        return _KPIBand(tiles, usable_w, self.accent)

    def _snapshot_grid(self, analyses, area_unit, desc_w, val_w):
        """Multi-area headline comparison grid (stats as rows, areas as cols)."""
        from .formatting_utils import format_value_for_display, format_area_label
        first_results = analyses[0][1]
        head = [Paragraph('Market Snapshot', self.styles['head'])]
        for area_value, _, _ in analyses:
            head.append(Paragraph(format_area_label(area_value, area_unit),
                                  self.styles['head_r']))
        data = [head]
        for var, label in SNAPSHOT_STATS:
            if var not in first_results:
                continue
            row = [Paragraph(label, self.styles['snap_lbl'])]
            for _, results, _ in analyses:
                row.append(Paragraph(
                    format_value_for_display(var, results.get(var, 0)),
                    self.styles['snap_val']))
            data.append(row)
        num_areas = len(analyses)
        t = Table(data, colWidths=[desc_w] + [val_w] * num_areas, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.accent),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, TILE]),
            ('LINEBELOW', (0, 1), (-1, -1), 0.4, LGREY),
            ('BOX', (0, 0), (-1, -1), 0.6, LGREY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    # -- category table -------------------------------------------------------
    def _category_table(self, category, category_vars, analyses, area_unit,
                        variable_definitions, desc_w, val_w):
        """
        One category table. Description column + one value column per area.
        Used for both single-area (narrow, two-column flow) and multi-area
        (full-width) layouts -- only the column widths differ.
        """
        from .formatting_utils import format_value_for_display, format_area_label

        head = [Paragraph(category, self.styles['head'])]
        for area_value, _, _ in analyses:
            head.append(Paragraph(format_area_label(area_value, area_unit),
                                  self.styles['head_r']))
        data = [head]
        for var in category_vars:
            desc = self._clean_description(variable_definitions.get(var, var))
            row = [Paragraph(desc, self.styles['cell'])]
            for _, results, _ in analyses:
                row.append(Paragraph(
                    format_value_for_display(var, results.get(var, 0)),
                    self.styles['cell_r']))
            data.append(row)

        num_areas = len(analyses)
        t = Table(data, colWidths=[desc_w] + [val_w] * num_areas, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, 0), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 1.8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1.8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZEBRA]),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, LGREY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    def generate_point_report(self, output_path, analyses, package,
                            location_coords, variable_categories, variable_definitions,
                            area_unit='mi'):
        """
        Generate a PDF report for a point-based demographic analysis, with one
        column of values per analysis area (up to 3), side by side.

        Args:
            output_path: str - Path where PDF will be saved
            analyses: list[tuple] - (area_value, results, metadata) for each
                analysis area, sorted ascending. area_value is radius-miles when
                area_unit='mi' or drive-time-minutes when area_unit='min'. Each area
                is cumulative, so larger areas already include everything smaller.
            package: str - Package name
            location_coords: tuple - (x, y) coordinates of selected point
            variable_categories: dict - Variables organized by category
            variable_definitions: dict - Variable definitions
            area_unit: str - 'mi' for radius miles, 'min' for drive-time minutes
        """
        from .formatting_utils import format_area_caption

        num_areas = len(analyses)
        multi = num_areas >= 2
        first_results = analyses[0][1]

        usable_w = PAGE_W - 2 * MARGIN
        content_top = PAGE_H - MARGIN - HEADER_H
        content_bottom = MARGIN + FOOTER_H

        doc = BaseDocTemplate(
            output_path, pagesize=letter,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN)

        # --- title + metadata (shared) ---
        area_summary = "  |  ".join(
            format_area_caption(area_value, area_unit)
            for area_value, _, _ in analyses)
        area_heading = "Drive Times" if area_unit == 'min' else "Radii"
        meta_text = (
            "<b>Package:</b> %s &nbsp;|&nbsp; "
            "<b>Location:</b> %.5f, %.5f &nbsp;|&nbsp; "
            "<b>%s (cumulative):</b> %s"
            % (package, location_coords[1], location_coords[0],
               area_heading, area_summary))

        story = []

        if multi:
            # ---- multi-area: single full-width column ----
            val_w = 78
            desc_w = usable_w - val_w * num_areas
            frame = Frame(MARGIN, content_bottom, usable_w,
                          content_top - content_bottom,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0, id='main')
            doc.addPageTemplates([
                PageTemplate(id='main', frames=[frame], onPage=self._draw_chrome)])

            story.append(Paragraph("Demographic Report", self.styles['title']))
            story.append(Paragraph(meta_text, self.styles['meta']))
            story.append(Spacer(1, 10))
            story.append(self._snapshot_grid(analyses, area_unit, desc_w, val_w))
            story.append(Spacer(1, 14))

            tables = self._build_category_flow(
                variable_categories, variable_definitions, analyses, area_unit,
                first_results, desc_w, val_w, trailing_space=9)
        else:
            # ---- single area: KPI band on top, two-column category tables ----
            col_w = (usable_w - COL_GAP) / 2
            val_w = 0.9 * inch
            desc_w = col_w - val_w
            KPI_H = 124
            lx = MARGIN
            rx = MARGIN + col_w + COL_GAP
            fkw = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
            kpi_frame = Frame(MARGIN, content_top - KPI_H, usable_w, KPI_H,
                              id='kpi', **fkw)
            f_left1 = Frame(lx, content_bottom, col_w,
                            content_top - KPI_H - content_bottom - 6, id='l1', **fkw)
            f_right1 = Frame(rx, content_bottom, col_w,
                             content_top - KPI_H - content_bottom - 6, id='r1', **fkw)
            f_left = Frame(lx, content_bottom, col_w,
                           content_top - content_bottom, id='l', **fkw)
            f_right = Frame(rx, content_bottom, col_w,
                            content_top - content_bottom, id='r', **fkw)
            doc.addPageTemplates([
                PageTemplate(id='first', frames=[kpi_frame, f_left1, f_right1],
                             onPage=self._draw_chrome),
                PageTemplate(id='later', frames=[f_left, f_right],
                             onPage=self._draw_chrome),
            ])

            story.append(NextPageTemplate('later'))
            story.append(Paragraph("Demographic Report", self.styles['title']))
            story.append(Paragraph(meta_text, self.styles['meta']))
            story.append(Spacer(1, 8))
            story.append(self._snapshot_tiles(first_results, usable_w))
            story.append(FrameBreak())

            tables = self._build_category_flow(
                variable_categories, variable_definitions, analyses, area_unit,
                first_results, desc_w, val_w, trailing_space=9)

        # Drive-time data attribution (required when isochrones are used).
        # Pin it to the last category table via KeepTogether so a lone line can
        # never orphan a near-empty final page.
        if area_unit == 'min' and tables:
            attribution = Paragraph(
                "Drive-time areas &copy; OpenStreetMap contributors, via the "
                "Valhalla routing engine (FOSSGIS e.V.). Road data licensed under ODbL.",
                self.styles['attribution'])
            tables.pop()                       # drop trailing spacer after last table
            last_table = tables.pop()
            tables.append(KeepTogether([last_table, Spacer(1, 6), attribution]))

        story.extend(tables)
        doc.build(story)
        return output_path

    def _build_category_flow(self, variable_categories, variable_definitions,
                            analyses, area_unit, first_results, desc_w, val_w,
                            trailing_space):
        """Build the ordered list of category tables (+ spacers) for the story."""
        flow = []
        for category, var_list in variable_categories.items():
            category_vars = [v for v in var_list
                             if v in first_results and v != 'BGID']
            if not category_vars:
                continue
            flow.append(self._category_table(
                category, category_vars, analyses, area_unit,
                variable_definitions, desc_w, val_w))
            flow.append(Spacer(1, trailing_space))
        return flow
