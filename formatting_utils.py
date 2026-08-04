# -*- coding: utf-8 -*-
"""
Created on Tue Jan 27 18:38:16 2026

@author: brad@retailgravity.com
"""

"""
Formatting and rounding utilities for demographic data.
"""

def format_area_label(value, area_unit):
    """
    Short column label for an analysis area.

    Args:
        value: float - The area size (miles for radii, minutes for drive times)
        area_unit: str - 'mi' for radius miles, 'min' for drive-time minutes

    Returns:
        str - e.g. "1.00 mi" or "10 min"
    """
    if area_unit == 'min':
        return f"{value:.0f} min"
    return f"{value:.2f} mi"


def format_area_caption(value, area_unit):
    """
    Longer caption for an analysis area (adds km for radii, "drive" for times).

    Args:
        value: float - The area size (miles for radii, minutes for drive times)
        area_unit: str - 'mi' for radius miles, 'min' for drive-time minutes

    Returns:
        str - e.g. "1.00 mi (1.61 km)" or "10 min drive"
    """
    if area_unit == 'min':
        return f"{value:.0f} min drive"
    return f"{value:.2f} mi ({value * 1.60934:.2f} km)"


def round_value(variable_name, value):
    """
    Round a value according to variable-specific rules.
    
    Args:
        variable_name: str - Name of the variable
        value: float - Value to round
    
    Returns:
        float - Rounded value
    """
    if value is None:
        return 0.0
    
    try:
        value = float(value)
    except (ValueError, TypeError):
        return 0.0
    
    # One decimal place
    if variable_name in ['CY_MEDAGE', 'CY_MMEDAGE', 'CY_FMEDAGE']:
        return round(value, 1)
    
    # Three decimal places
    elif variable_name in ['POP_GROWTH', 'CY_AVGHHSIZE', 'LAND_AREA']:
        return round(value, 3)
    
    # Whole numbers (default)
    else:
        return round(value, 0)


def format_value_for_display(variable_name, value):
    """
    Format a value for display in reports (with commas, dollar signs, etc.)
    
    Args:
        variable_name: str - Name of the variable
        value: float - Value to format
    
    Returns:
        str - Formatted value as string
    """
    if value is None:
        return "N/A"
    
    try:
        value = float(value)
    except (ValueError, TypeError):
        return "N/A"
    
    # Round first
    rounded_value = round_value(variable_name, value)
    
    # Dollar formatting
    if variable_name in ['CY_AVGHHINC', 'CY_MEDHHINC', 'CY_AGGINCOME']:
        if rounded_value == 0:
            return "$0"
        return f"${rounded_value:,.0f}"
    
    # Year formatting (4 digits, no commas)
    elif variable_name == 'CY_MEDYEAR':
        if rounded_value == 0:
            return "N/A"
        return f"{int(rounded_value)}"
    
    # Percentage formatting (multiply by 100 for display)
    elif variable_name == 'POP_GROWTH':
        return f"{rounded_value * 100:,.2f}%"
    
    # One decimal place numbers
    elif variable_name in ['CY_MEDAGE', 'CY_MMEDAGE', 'CY_FMEDAGE', 'CY_AVGHHSIZE']:
        return f"{rounded_value:,.1f}"
    
    # Two decimal place numbers
    elif variable_name == 'LAND_AREA':
        return f"{rounded_value:,.2f}"
    
    # Default: whole numbers with commas
    else:
        return f"{int(rounded_value):,}"


def format_value_for_csv(variable_name, value):
    """
    Format a value for CSV export (just rounding, no formatting).
    
    Args:
        variable_name: str - Name of the variable
        value: float - Value to format
    
    Returns:
        float - Rounded value (as number, not string)
    """
    return round_value(variable_name, value)