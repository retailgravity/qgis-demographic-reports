# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 05:58:19 2026

@author: brad@retailgravity.com
"""

"""
PDF report generator for demographic reports.
Creates professional formatted PDF reports with tables and statistics.
With custom branding and simplified layout.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
SimpleDocTemplate,
Table,
TableStyle,
Paragraph,
Spacer,
PageBreak,
KeepTogether,
Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os

class DemographicPDFGenerator:
    """
    Generates professional PDF reports for demographic data.
    """
    def __init__(self, logo_path=None, company_name="Retail Gravity", 
                 website="www.retailgravity.com", brand_color="#182839"):
        """
        Initialize the PDF generator with custom branding.
        
        Args:
            logo_path: str - Path to company logo image file (PNG, JPG)
            company_name: str - Your company name for footer
            website: str - Your website URL for footer
            brand_color: str - Hex color code for branding (default blue)
        """
        self.styles = getSampleStyleSheet()
        self.logo_path = logo_path
        self.company_name = company_name
        self.website = website
        self.brand_color = colors.HexColor(brand_color)
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report."""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#182839'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Category header style
        self.styles.add(ParagraphStyle(
            name='CategoryHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.brand_color,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#94A3B8'),
            spaceAfter=4,
            leading=12
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#182839'),
            alignment=TA_CENTER
        ))
        
        # Company branding style
        self.styles.add(ParagraphStyle(
            name='Branding',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.brand_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
    
    def _clean_description(self, description):
        """
        Clean up variable descriptions by removing common prefixes.
        
        Args:
            description: str - Original variable description
        
        Returns:
            str - Cleaned description
        """
        # Remove common prefixes
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
    
    def _add_header(self, story):
        """
        Add header with logo and company branding.
        
        Args:
            story: list - The story (PDF elements) to add header to
        """
        # Add logo if provided
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                # Add logo - adjust size as needed
                logo = Image(self.logo_path, width=2*inch, height=0.8*inch, kind='proportional')
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.1*inch))
            except Exception as e:
                print(f"Warning: Could not load logo: {e}")
        
        # Add separator line
        line_data = [[''] * 1]
        line_table = Table(line_data, colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#182839')),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 0.1*inch))
    
    def _add_footer(self, story):
        """
        Add footer with company information.
        
        Args:
            story: list - The story (PDF elements) to add footer to
        """
        # Add separator line
        line_data = [[''] * 1]
        line_table = Table(line_data, colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#182839')),
        ]))
        story.append(Spacer(1, 0.1*inch))
        story.append(line_table)
        story.append(Spacer(1, 0.1*inch))
        
        # Source
        footer_text = f"""
        Source Data: <b>Retail Gravity</b><br/>
        www.retailgravity.com<br/>
        Generated: {datetime.now().strftime("%B %d, %Y")}
        """
        footer = Paragraph(footer_text, self.styles['Footer'])
        story.append(footer)
    
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
        from .formatting_utils import (
            format_value_for_display, format_area_label, format_area_caption
        )

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Container for PDF elements
        story = []

        # Add header with branding
        self._add_header(story)

        # Add title
        title = Paragraph("Demographic Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 0.15*inch))

        # Add report metadata
        report_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        area_summary = "  |  ".join(
            format_area_caption(area_value, area_unit)
            for area_value, _, _ in analyses
        )
        area_heading = "Analysis Drive Times" if area_unit == 'min' else "Analysis Radii"

        metadata_text = f"""
        <b>Report Generated:</b> {report_date}   |  <b>Data Package:</b> {package}<br/>
        <b>Analysis Location:</b> {location_coords[1]:.6f}, {location_coords[0]:.6f}<br/>
        <b>{area_heading} (cumulative):</b> {area_summary}
        """

        metadata_para = Paragraph(metadata_text, self.styles['Metadata'])
        story.append(metadata_para)
        story.append(Spacer(1, 0.2*inch))

        # Column layout: description column + one value column per analysis area
        num_areas = len(analyses)
        value_col_width = 0.9 * inch
        desc_col_width = 7 * inch - (value_col_width * num_areas)
        col_widths = [desc_col_width] + [value_col_width] * num_areas

        header_row = ['Variable'] + [
            format_area_label(area_value, area_unit) for area_value, _, _ in analyses
        ]

        # Add detailed data by category
        first_results = analyses[0][1]
        for category, var_list in variable_categories.items():
            # Check if any variables in this category are in results
            category_vars = [v for v in var_list if v in first_results and v != 'BGID']

            if not category_vars:
                continue

            # Create table data for this category - use category name as header
            table_data = [[category] + header_row[1:]]

            for var in category_vars:
                definition = variable_definitions.get(var, var)

                # Clean the description
                cleaned_def = self._clean_description(definition)

                # Add variable name in parentheses
                description_with_var = f"{cleaned_def} ({var})"

                row = [description_with_var]
                for _, results, _ in analyses:
                    value = results.get(var, 0)
                    row.append(format_value_for_display(var, value))

                table_data.append(row)

            # Create and style the table
            category_table = Table(
                table_data,
                colWidths=col_widths
            )

            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#182839')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))

            # Keep category header and table together
            story.append(category_table)
            story.append(Spacer(1, 0.15*inch))

        # Drive-time data attribution (required when isochrones are used)
        if area_unit == 'min':
            story.append(Spacer(1, 0.1*inch))
            attribution = Paragraph(
                "Drive-time areas &copy; OpenStreetMap contributors, via the "
                "Valhalla routing engine (FOSSGIS e.V.). Road data licensed under ODbL.",
                self.styles['Metadata']
            )
            story.append(attribution)

        # Add footer with branding
        self._add_footer(story)

        # Build PDF
        doc.build(story)

        return output_path