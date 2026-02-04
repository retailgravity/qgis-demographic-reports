# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 15:48:35 2026

@author: brad@retailgravity.com
"""

"""
Spatial processing functions for demographic analysis.
Handles buffer creation, intersection, and proportional calculations.
"""

from qgis.core import (
    QgsGeometry,
    QgsPointXY,
    QgsFeature,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsDistanceArea
)


class SpatialProcessor:
    """
    Handles all spatial operations for demographic reporting.
    """
    
    # Define fields that should not be summed
    CALCULATED_FIELDS = {
        'POP_DENSITY',      # CY_POP / LAND_AREA
        'POP_GROWTH',       # (FY_POP - CY_POP) / CY_POP
        'CY_MEDAGE',        # weighted average by CY_POP
        'CY_MMEDAGE',       # weighted average by CY_POP
        'CY_FMEDAGE',       # weighted average by CY_POP
        'HH_DENSITY',       # CY_HOUSEHOLDS / LAND_AREA
        'CY_AVGHHINC',      # weighted average by CY_HOUSEHOLDS
        'CY_MEDHHINC',      # median from income bins
        'CY_AGGINCOME',     # CY_HOUSEHOLDS * CY_AVGHHINC
        'CY_MEDYEAR',       # median from year bins
        'CY_AVGHHSIZE',     # CY_POP / CY_HOUSEHOLDS
    }
    
    def __init__(self):
        """Initialize the spatial processor."""
        # Create distance calculator for accurate area measurements
        self.distance_area = QgsDistanceArea()
        self.distance_area.setEllipsoid('WGS84')
    
    def create_buffer(self, point, radius_meters, source_crs):
        """
        Create a circular buffer around a point.
        
        Args:
            point: QgsPointXY - Center point
            radius_meters: float - Radius in meters
            source_crs: QgsCoordinateReferenceSystem - CRS of the input point
        
        Returns:
            QgsGeometry - Buffer polygon geometry in source CRS
        """
        print(f"Creating buffer: radius={radius_meters}m, source CRS={source_crs.authid()}")
        
        # Web Mercator (EPSG:3857) for buffering
        web_mercator = QgsCoordinateReferenceSystem('EPSG:3857')
        
        # Create transform from source CRS to Web Mercator
        transform_to_mercator = QgsCoordinateTransform(
            source_crs,
            web_mercator,
            QgsProject.instance()
        )
        
        # Transform back to original CRS
        transform_to_original = QgsCoordinateTransform(
            web_mercator,
            source_crs,
            QgsProject.instance()
        )
        
        # Transform point to Web Mercator
        point_geom = QgsGeometry.fromPointXY(point)
        point_geom.transform(transform_to_mercator)
        
        print(f"  Point in Web Mercator: {point_geom.asPoint().x():.2f}, {point_geom.asPoint().y():.2f}")
        
        # Create buffer in meters
        buffer_geom = point_geom.buffer(radius_meters, 32)  # 32 segments for smooth circle
        
        print(f"  Buffer area in Web Mercator: {buffer_geom.area():,.2f} sq meters")
        
        # Transform buffer back to original CRS
        buffer_geom.transform(transform_to_original)
        
        print(f"  Buffer created in {source_crs.authid()}")
        
        return buffer_geom
    
    def calculate_intersection_ratio(self, block_group_geom, analysis_geom, bg_crs, analysis_crs):
        """
        Calculate what proportion of a block group intersects with analysis area.
        
        Args:
            block_group_geom: QgsGeometry - Block group polygon
            analysis_geom: QgsGeometry - Analysis area (buffer or polygon)
            bg_crs: QgsCoordinateReferenceSystem - CRS of block group
            analysis_crs: QgsCoordinateReferenceSystem - CRS of analysis geometry
        
        Returns:
            float - Ratio of block group area within analysis area (0.0 to 1.0)
        """
        # Make copies
        bg_geom = QgsGeometry(block_group_geom)
        analysis_geom_copy = QgsGeometry(analysis_geom)
        
        # If CRS don't match, transform analysis geometry to block group CRS
        if bg_crs != analysis_crs:
            transform = QgsCoordinateTransform(
                analysis_crs,
                bg_crs,
                QgsProject.instance()
            )
            analysis_geom_copy.transform(transform)
        
        # Check if geometries intersect
        if not bg_geom.intersects(analysis_geom_copy):
            return 0.0
        
        # Calculate intersection geometry
        intersection = bg_geom.intersection(analysis_geom_copy)
        
        if intersection.isEmpty():
            return 0.0
        
        # Set CRS for area calculation
        self.distance_area.setSourceCrs(
            bg_crs,
            QgsProject.instance().transformContext()
        )
        
        # Calculate areas using ellipsoidal calculation for accuracy
        bg_area = self.distance_area.measureArea(bg_geom)
        intersection_area = self.distance_area.measureArea(intersection)
        
        # Avoid division by zero
        if bg_area == 0:
            return 0.0
        
        # Calculate ratio
        ratio = intersection_area / bg_area
        
        # Ensure ratio is between 0 and 1 (handle floating point errors)
        return min(max(ratio, 0.0), 1.0)
    
    def _calculate_derived_fields(self, results, weighted_sums):
        """
        Calculate fields that require special computation after aggregation.
        
        Args:
            results: dict - Aggregated demographic values
            weighted_sums: dict - Weighted sums for averaging
        
        Returns:
            dict - Results with calculated fields added
        """
        # POP_DENSITY = CY_POP / LAND_AREA (per square mile)
        if 'CY_POP' in results and 'LAND_AREA' in results and results['LAND_AREA'] > 0:
            results['POP_DENSITY'] = results['CY_POP'] / results['LAND_AREA']
        
        # POP_GROWTH = (FY_POP - CY_POP) / CY_POP
        if 'FY_POP' in results and 'CY_POP' in results and results['CY_POP'] > 0:
            results['POP_GROWTH'] = (results['FY_POP'] - results['CY_POP']) / results['CY_POP']
        
        # CY_MEDAGE = weighted average by CY_POP
        if 'CY_MEDAGE_WEIGHTED' in weighted_sums and results.get('CY_POP', 0) > 0:
            results['CY_MEDAGE'] = weighted_sums['CY_MEDAGE_WEIGHTED'] / results['CY_POP']
        
        # CY_MMEDAGE = weighted average by CY_MPOP
        if 'CY_MMEDAGE_WEIGHTED' in weighted_sums and results.get('CY_MPOP', 0) > 0:
            results['CY_MMEDAGE'] = weighted_sums['CY_MMEDAGE_WEIGHTED'] / results['CY_MPOP']
        
        # CY_FMEDAGE = weighted average by CY_FPOP
        if 'CY_FMEDAGE_WEIGHTED' in weighted_sums and results.get('CY_FPOP', 0) > 0:
            results['CY_FMEDAGE'] = weighted_sums['CY_FMEDAGE_WEIGHTED'] / results['CY_FPOP']
        
        # HH_DENSITY = CY_HOUSEHOLDS / LAND_AREA (per square mile)
        if 'CY_HOUSEHOLDS' in results and 'LAND_AREA' in results and results['LAND_AREA'] > 0:
            results['HH_DENSITY'] = results['CY_HOUSEHOLDS'] / results['LAND_AREA']
        
        # CY_AVGHHINC = weighted average by CY_HOUSEHOLDS
        if 'CY_AVGHHINC_WEIGHTED' in weighted_sums and results.get('CY_HOUSEHOLDS', 0) > 0:
            results['CY_AVGHHINC'] = weighted_sums['CY_AVGHHINC_WEIGHTED'] / results['CY_HOUSEHOLDS']
        
        # CY_AGGINCOME = CY_HOUSEHOLDS * CY_AVGHHINC
        if 'CY_HOUSEHOLDS' in results and 'CY_AVGHHINC' in results:
            results['CY_AGGINCOME'] = results['CY_HOUSEHOLDS'] * results['CY_AVGHHINC']
        
        # CY_AVGHHSIZE = CY_POP / CY_HOUSEHOLDS
        if 'CY_POP' in results and 'CY_HOUSEHOLDS' in results and results['CY_HOUSEHOLDS'] > 0:
            results['CY_AVGHHSIZE'] = results['CY_POP'] / results['CY_HOUSEHOLDS']
        
        # CY_MEDHHINC and CY_MEDYEAR require income/year bins - calculated if bins exist
        # These would need the actual bin data which may not be in your dataset
        # Placeholder: if you have the actual median values in the data, use weighted average
        if 'CY_MEDHHINC_WEIGHTED' in weighted_sums and results.get('CY_HOUSEHOLDS', 0) > 0:
            results['CY_MEDHHINC'] = weighted_sums['CY_MEDHHINC_WEIGHTED'] / results['CY_HOUSEHOLDS']
        
        if 'CY_MEDYEAR_WEIGHTED' in weighted_sums and results.get('CY_HOUSEHOLDS', 0) > 0:
            results['CY_MEDYEAR'] = weighted_sums['CY_MEDYEAR_WEIGHTED'] / results['CY_HOUSEHOLDS']
        
        return results
    
    def aggregate_demographics(self, block_groups_layer, analysis_geom, analysis_crs, variables, package_name=None):
        """
        Aggregate demographic data from block groups that intersect analysis area.
        Uses proportional allocation based on area overlap.
        Adds spatial index for better performance
        
        Args:
            block_groups_layer: QgsVectorLayer - Layer with block group polygons
            analysis_geom: QgsGeometry - Analysis area geometry
            analysis_crs: QgsCoordinateReferenceSystem - CRS of analysis geometry
            variables: list - List of variable names to aggregate
            package_name: str - Package name for validation (optional)
        
        Returns:
            dict - Dictionary with aggregated values for each variable
            dict - Dictionary with metadata (block groups processed, total area, etc.)
        """
        print(f"Aggregating demographics:")
        print(f"  Block group layer CRS: {block_groups_layer.crs().authid()}")
        print(f"  Analysis geometry CRS: {analysis_crs.authid()}")
        print(f"  Variables to aggregate: {len(variables)}")
        
        # Create spatial index for faster processing
        from qgis.core import QgsSpatialIndex
        print("  Creating spatial index...")
        spatial_index = QgsSpatialIndex(block_groups_layer.getFeatures())
        print("  Spatial index created")
        
        # Initialize results dictionary
        results = {}
        for var in variables:
            results[var] = 0.0
        
        # Track weighted sums for averaging
        weighted_sums = {
            'CY_MEDAGE_WEIGHTED': 0.0,
            'CY_MMEDAGE_WEIGHTED': 0.0,
            'CY_FMEDAGE_WEIGHTED': 0.0,
            'CY_AVGHHINC_WEIGHTED': 0.0,
            'CY_MEDHHINC_WEIGHTED': 0.0,
            'CY_MEDYEAR_WEIGHTED': 0.0,
        }
        
        # Get the CRS of the block groups layer
        bg_crs = block_groups_layer.crs()
        
        # Transform analysis geometry to block group CRS if needed
        analysis_geom_in_bg_crs = QgsGeometry(analysis_geom)
        if bg_crs != analysis_crs:
            print(f"  Transforming analysis geometry from {analysis_crs.authid()} to {bg_crs.authid()}")
            transform = QgsCoordinateTransform(
                analysis_crs,
                bg_crs,
                QgsProject.instance()
            )
            analysis_geom_in_bg_crs.transform(transform)
        
        # Set CRS for area calculation
        self.distance_area.setSourceCrs(
            bg_crs,
            QgsProject.instance().transformContext()
        )
        
        # Track metadata
        metadata = {
            'block_groups_processed': 0,
            'block_groups_intersecting': 0,
            'total_analysis_area_sqm': self.distance_area.measureArea(analysis_geom_in_bg_crs)
        }
        
        print(f"  Analysis area: {metadata['total_analysis_area_sqm']:,.2f} sq meters")
        
        # Get bounding box for spatial filter
        bbox = analysis_geom_in_bg_crs.boundingBox()
        print(f"  Bounding box: {bbox.toString()}")
        
        # Use spatial index to get candidate features
        candidate_ids = spatial_index.intersects(bbox)
        print(f"  Spatial index found {len(candidate_ids)} candidate features")
        
        # Get features using the candidate IDs
        request = block_groups_layer.getFeatures(candidate_ids)
        
        # Process each block group
        for feature in request:
            metadata['block_groups_processed'] += 1
            
            # Get block group geometry
            bg_geom = feature.geometry()
            
            if bg_geom is None or bg_geom.isEmpty():
                continue
            
            # Quick bounding box check first
            if not bg_geom.boundingBox().intersects(bbox):
                continue
            
            # Calculate intersection ratio
            ratio = self.calculate_intersection_ratio(
                bg_geom, 
                analysis_geom_in_bg_crs,
                bg_crs,
                bg_crs
            )
            
            if ratio > 0.0:
                metadata['block_groups_intersecting'] += 1
                
                # Debug first few intersections
                if metadata['block_groups_intersecting'] <= 3:
                    print(f"  Block group {metadata['block_groups_intersecting']}: ratio={ratio:.4f}")
                
                # Aggregate each variable
                for var in variables:
                    # Skip BGID and calculated fields
                    if var == 'BGID' or var in self.CALCULATED_FIELDS:
                        continue
                    
                    # Get value from feature
                    value = feature[var]
                    
                    # Handle None/NULL values
                    if value is None:
                        value = 0
                    
                    # Convert to float if needed
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        if metadata['block_groups_intersecting'] <= 3:
                            print(f"  Warning: Could not convert {var}={value} to float, using 0")
                        value = 0.0
                    
                    # Add proportional value to result
                    results[var] += value * ratio
                
                # Handle weighted averages - need to track weighted sums
                # Helper function to safely get field value
                def safe_get_field(feature, field_name):
                    """Safely get field value, returning 0 if None or doesn't exist."""
                    try:
                        val = feature[field_name]
                        return val if val is not None else 0
                    except KeyError:
                        return 0
                
                # CY_MEDAGE weighted by CY_POP
                if 'CY_MEDAGE' in variables:
                    medage_val = safe_get_field(feature, 'CY_MEDAGE')
                    pop_val = safe_get_field(feature, 'CY_POP')
                    try:
                        weighted_sums['CY_MEDAGE_WEIGHTED'] += float(medage_val) * float(pop_val) * ratio
                    except (ValueError, TypeError):
                        pass
                
                # CY_MMEDAGE weighted by CY_MPOP
                if 'CY_MMEDAGE' in variables:
                    mmedage_val = safe_get_field(feature, 'CY_MMEDAGE')
                    mpop_val = safe_get_field(feature, 'CY_MPOP')
                    try:
                        weighted_sums['CY_MMEDAGE_WEIGHTED'] += float(mmedage_val) * float(mpop_val) * ratio
                    except (ValueError, TypeError):
                        pass
                
                # CY_FMEDAGE weighted by CY_FPOP
                if 'CY_FMEDAGE' in variables:
                    fmedage_val = safe_get_field(feature, 'CY_FMEDAGE')
                    fpop_val = safe_get_field(feature, 'CY_FPOP')
                    try:
                        weighted_sums['CY_FMEDAGE_WEIGHTED'] += float(fmedage_val) * float(fpop_val) * ratio
                    except (ValueError, TypeError):
                        pass
                
                # CY_AVGHHINC weighted by CY_HOUSEHOLDS
                if 'CY_AVGHHINC' in variables:
                    avghhinc_val = safe_get_field(feature, 'CY_AVGHHINC')
                    hh_val = safe_get_field(feature, 'CY_HOUSEHOLDS')
                    try:
                        weighted_sums['CY_AVGHHINC_WEIGHTED'] += float(avghhinc_val) * float(hh_val) * ratio
                    except (ValueError, TypeError):
                        pass
                
                # CY_MEDHHINC weighted by CY_HOUSEHOLDS (approximation)
                if 'CY_MEDHHINC' in variables:
                    medhhinc_val = safe_get_field(feature, 'CY_MEDHHINC')
                    hh_val = safe_get_field(feature, 'CY_HOUSEHOLDS')
                    try:
                        weighted_sums['CY_MEDHHINC_WEIGHTED'] += float(medhhinc_val) * float(hh_val) * ratio
                    except (ValueError, TypeError):
                        pass
                
                # CY_MEDYEAR weighted by CY_HOUSEHOLDS (approximation)
                if 'CY_MEDYEAR' in variables:
                    medyear_val = safe_get_field(feature, 'CY_MEDYEAR')
                    hh_val = safe_get_field(feature, 'CY_HOUSEHOLDS')
                    try:
                        weighted_sums['CY_MEDYEAR_WEIGHTED'] += float(medyear_val) * float(hh_val) * ratio
                    except (ValueError, TypeError):
                        pass
        
        print(f"  Total block groups processed: {metadata['block_groups_processed']}")
        print(f"  Block groups intersecting: {metadata['block_groups_intersecting']}")
        
        # Calculate derived fields
        results = self._calculate_derived_fields(results, weighted_sums)
        
        # Show sample of results for debugging
        sample_vars = [v for v in list(results.keys())[:5] if v != 'BGID']
        for var in sample_vars:
            print(f"  {var}: {results[var]:,.2f}")
        
        return results, metadata


def validate_layer_for_analysis(layer, variables):
    """
    Validate that a layer has all required variables.
    
    Args:
        layer: QgsVectorLayer - Layer to validate
        variables: list - List of required variable names
    
    Returns:
        tuple: (is_valid, missing_variables, error_message)
    """
    if not layer or not layer.isValid():
        return False, [], "Layer is not valid"
    
    # Get field names
    field_names = [field.name() for field in layer.fields()]
    
    # Check for missing variables
    # Don't require calculated fields to be present
    required_vars = [v for v in variables if v not in SpatialProcessor.CALCULATED_FIELDS]
    missing = [var for var in required_vars if var not in field_names]
    
    if missing:
        msg = f"Layer is missing {len(missing)} required variables"
        return False, missing, msg
    
    return True, [], "Layer is valid"