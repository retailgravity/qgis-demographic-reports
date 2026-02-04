# -*- coding: utf-8 -*-
"""
Created on Tue Jan 20 15:39:56 2026

@author: brad@retailgravity.com
"""

"""
Map tool for selecting points on the canvas.
Allows users to click the map to set a location for demographic reporting.
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsPointXY, QgsWkbTypes


class PointTool(QgsMapTool):
    """
    Custom map tool for clicking points on the map canvas.
    Emits a signal when a point is clicked.
    """
    
    # Signal emitted when user clicks on map
    # Sends the clicked point coordinates
    pointSelected = pyqtSignal(QgsPointXY)
    
    def __init__(self, canvas):
        """
        Initialize the point selection tool.
        
        Args:
            canvas: QgsMapCanvas - The QGIS map canvas
        """
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        
        # Create a rubber band to show where user clicked
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0, 180))  # Red, semi-transparent
        self.rubber_band.setWidth(10)
        
    def canvasPressEvent(self, event):
        """
        Called when user clicks on the map canvas.
        
        Args:
            event: QgsMapMouseEvent - Mouse event with click information
        """
        # Get the clicked point in map coordinates
        point = self.toMapCoordinates(event.pos())
        
        # Clear any previous marker
        self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        
        # Add new marker at clicked location
        self.rubber_band.addPoint(point)
        
        # Emit signal with the clicked point
        self.pointSelected.emit(point)
        
    def deactivate(self):
        """
        Called when the tool is deactivated.
        Clears the rubber band marker.
        """
        self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        QgsMapTool.deactivate(self)
        
    def activate(self):
        """
        Called when the tool is activated.
        """
        QgsMapTool.activate(self)