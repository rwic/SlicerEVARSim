import logging
import os
from typing import Annotated, Optional

import vtk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLMarkupsCurveNode, vtkMRMLModelNode


#
# EVARSim
#


class EVARSim(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("EVAR Simulator")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Modeling")]
        self.parent.dependencies = []
        self.parent.contributors = ["EVARSim Development Team"]
        self.parent.helpText = _("""
This module allows users to place endovascular devices along centerline curves for EVAR (Endovascular Aneurysm Repair) simulation.
Users can adjust device position, radius, length, and resolution parameters through the GUI interface.
""")
        self.parent.acknowledgementText = _("""

""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # Sample data registration can be added here when specific test datasets
    # for centerline curves and EVAR simulation become available.
    pass


#
# EVARSimParameterNode
#


@parameterNodeWrapper
class EVARSimParameterNode:
    """
    The parameters needed by module.

    centerlineCurve - The curve that defines the centerline for cylinder placement.
    inputModel - Alternative input: model from which to extract centerline.
    cylinderRadius - The radius of the cylindrical object.
    cylinderLength - The length of the cylindrical object.
    cylinderPosition - Position along centerline (0.0 = start, 1.0 = end).
    numberOfTubes - Number of tubes to create along the centerline.
    cylinderResolution - The resolution (number of sides) of the cylinder.
    outputModel - The output model that will contain the cylindrical object.
    """

    centerlineCurve: vtkMRMLMarkupsCurveNode
    inputModel: vtkMRMLModelNode
    cylinderRadius: Annotated[float, WithinRange(0.1, 50.0)] = 2.0
    cylinderLength: Annotated[float, WithinRange(0.1, 200.0)] = 10.0
    cylinderPosition: Annotated[float, WithinRange(0.0, 1.0)] = 0.0
    numberOfTubes: Annotated[float, WithinRange(1.0, 10.0)] = 1.0
    cylinderResolution: Annotated[float, WithinRange(6.0, 64.0)] = 16.0
    smoothingFactor: Annotated[float, WithinRange(0.0, 1.0)] = 0.3
    outputModel: vtkMRMLModelNode


#
# EVARSimWidget
#


class EVARSimWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/EVARSim.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = EVARSimLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Connect node selectors to validation check
        self.ui.centerlineSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanApply)
        self.ui.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._onInputModelChanged)
        self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanApply)
        
        # Connect parameter sliders to real-time preview updates
        self.ui.cylinderRadiusSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderLengthSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderPositionSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.numberOfTubesSliderWidget.connect("valueChanged(double)", self._onTubeCountChanged)
        self.ui.cylinderResolutionSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.smoothingFactorSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        
        # Connect tube selector
        self.ui.tubeSelector.connect("currentIndexChanged(int)", self._onTubeSelected)
        
        # Connect branch selector
        self.ui.branchSelector.connect("currentIndexChanged(int)", self._onBranchSelected)
        
        # Initialize tube parameters storage
        self.tubeParameters = {}
        self.currentlySelectedTube = 1  # Start with tube 1 selected
        
        # Initialize branch selection storage (separate from tube logic)
        self.availableBranches = []

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module.
           Do not react to parameter node changes (GUI will be updated when the user enters into the module)"""
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.centerlineCurve:
            firstCurveNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsCurveNode")
            if firstCurveNode:
                self._parameterNode.centerlineCurve = firstCurveNode

    def setParameterNode(self, inputParameterNode: Optional[EVARSimParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        centerlineNode = self.ui.centerlineSelector.currentNode()
        inputModelNode = self.ui.inputModelSelector.currentNode()
        outputNode = self.ui.outputSelector.currentNode()
        
        # Need either a centerline curve OR an input model, plus an output model
        hasInput = centerlineNode or inputModelNode
        
        if hasInput and outputNode:
            self.ui.applyButton.toolTip = _("Create device")
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select centerline curve OR input model, and output model")
            self.ui.applyButton.enabled = False

    def _onTubeCountChanged(self) -> None:
        """Called when number of tubes changes."""
        # Update tube selector
        self._updateTubeSelector()
        # Regenerate all tubes
        if (self.ui.centerlineSelector.currentNode() or self.ui.inputModelSelector.currentNode()) and self.ui.outputSelector.currentNode():
            self.onApplyButton()

    def _onTubeSelected(self) -> None:
        """Called when user selects a different tube."""
        print(f"Tube selection changed to index {self.ui.tubeSelector.currentIndex}")
        
        # Save current slider values for the previously selected tube
        self._saveCurrentTubeParameters()
        
        # Update currently selected tube
        self.currentlySelectedTube = self.ui.tubeSelector.currentIndex + 1
        print(f"Now controlling tube {self.currentlySelectedTube}")
        
        # Load parameters for the newly selected tube
        self._loadSelectedTubeParameters()

    def _onParameterChanged(self) -> None:
        """Called when any parameter slider changes - provides real-time preview."""
        # Only update if we have valid inputs
        if (self.ui.centerlineSelector.currentNode() or self.ui.inputModelSelector.currentNode()) and self.ui.outputSelector.currentNode():
            # Update only the currently selected tube
            self._updateSelectedTube()

    def _updateTubeSelector(self) -> None:
        """Update the tube selector dropdown based on number of tubes."""
        numberOfTubes = int(self.ui.numberOfTubesSliderWidget.value)
        
        # Clear current items
        self.ui.tubeSelector.clear()
        
        # Add items for each tube
        for i in range(numberOfTubes):
            self.ui.tubeSelector.addItem(f"Tube {i+1}")

    def _saveCurrentTubeParameters(self) -> None:
        """Save current slider values for the currently selected tube."""
        if hasattr(self, 'currentlySelectedTube') and self.currentlySelectedTube > 0:
            self.tubeParameters[self.currentlySelectedTube] = {
                'radius': self.ui.cylinderRadiusSliderWidget.value,
                'length': self.ui.cylinderLengthSliderWidget.value,
                'position': self.ui.cylinderPositionSliderWidget.value,
                'resolution': self.ui.cylinderResolutionSliderWidget.value,
                'smoothing': self.ui.smoothingFactorSliderWidget.value,
                'branch': self.ui.branchSelector.currentIndex  # Save branch selection per tube
            }
            print(f"Saved parameters for tube {self.currentlySelectedTube}: {self.tubeParameters[self.currentlySelectedTube]}")

    def _loadSelectedTubeParameters(self) -> None:
        """Load parameters for the currently selected tube."""
        currentTube = self.currentlySelectedTube
        
        # Temporarily disconnect parameter change signals to avoid triggering updates
        self.ui.cylinderRadiusSliderWidget.disconnect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderLengthSliderWidget.disconnect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderPositionSliderWidget.disconnect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderResolutionSliderWidget.disconnect("valueChanged(double)", self._onParameterChanged)
        self.ui.smoothingFactorSliderWidget.disconnect("valueChanged(double)", self._onParameterChanged)
        self.ui.branchSelector.disconnect("currentIndexChanged(int)", self._onBranchSelected)
        
        if currentTube in self.tubeParameters:
            # Load saved parameters
            params = self.tubeParameters[currentTube]
            print(f"Loading saved parameters for tube {currentTube}: {params}")
        else:
            # Set default parameters for new tube
            params = {
                'radius': 2.0,
                'length': 10.0,
                'position': 0.1 + (currentTube - 1) * 0.2,  # Spread tubes out
                'resolution': 16.0,
                'smoothing': 0.3,
                'branch': (currentTube - 1) % len(self.availableBranches) if self.availableBranches else 0  # Cycle through branches
            }
            self.tubeParameters[currentTube] = params
            print(f"Creating default parameters for tube {currentTube}: {params}")
        
        # Update sliders
        self.ui.cylinderRadiusSliderWidget.value = params['radius']
        self.ui.cylinderLengthSliderWidget.value = params['length']
        self.ui.cylinderPositionSliderWidget.value = params['position']
        self.ui.cylinderResolutionSliderWidget.value = params['resolution']
        self.ui.smoothingFactorSliderWidget.value = params.get('smoothing', 0.3)
        
        # Update branch selector
        if 'branch' in params and params['branch'] < self.ui.branchSelector.count:
            self.ui.branchSelector.setCurrentIndex(params['branch'])
        
        # Reconnect parameter change signals
        self.ui.cylinderRadiusSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderLengthSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderPositionSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.cylinderResolutionSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.smoothingFactorSliderWidget.connect("valueChanged(double)", self._onParameterChanged)
        self.ui.branchSelector.connect("currentIndexChanged(int)", self._onBranchSelected)

    def _updateSelectedTube(self) -> None:
        """Update only the currently selected tube."""
        try:
            currentTube = self.currentlySelectedTube
            if currentTube <= 0:
                return
            
            print(f"Updating tube {currentTube}")
                
            # Save current slider values to parameters
            self.tubeParameters[currentTube] = {
                'radius': self.ui.cylinderRadiusSliderWidget.value,
                'length': self.ui.cylinderLengthSliderWidget.value,
                'position': self.ui.cylinderPositionSliderWidget.value,
                'resolution': self.ui.cylinderResolutionSliderWidget.value,
                'smoothing': self.ui.smoothingFactorSliderWidget.value,
                'branch': self.ui.branchSelector.currentIndex
            }
            
            # Get centerline
            centerlineCurve = self.ui.centerlineSelector.currentNode()
            inputModel = self.ui.inputModelSelector.currentNode()
            
            if centerlineCurve:
                curvePoints = centerlineCurve.GetCurvePointsWorld()
            elif inputModel:
                # Use branch selection from tube parameters
                params = self.tubeParameters[currentTube]
                branchIndex = params.get('branch', 0)
                
                # Extract centerline from specific branch if available
                if self.availableBranches and branchIndex < len(self.availableBranches):
                    curvePoints = self.logic._extractBranchCenterline(inputModel, branchIndex)
                else:
                    curvePoints = self.logic._extractCenterlineFromModel(inputModel)
            else:
                return
            
            if not curvePoints or curvePoints.GetNumberOfPoints() < 2:
                return
            
            # Get current parameters
            params = self.tubeParameters[currentTube]
            
            # Apply smoothing to the centerline
            smoothingFactor = params.get('smoothing', 0.3)
            if smoothingFactor > 0:
                curvePoints = self.logic._smoothCenterline(curvePoints, smoothingFactor)
            
            # First position the tube segment, then reduce to 4 points
            positionedPoints = self.logic._positionTubeAlongCenterline(curvePoints, params['length'], params['position'])
            
            # Always reduce the positioned segment to 4 points for smooth tubes
            reducedPoints = self.logic._reduceCenterlinePoints(positionedPoints)
            tubePolyData = self.logic._createTubeAlongCurve(reducedPoints, params['radius'], int(params['resolution']))
            
            # Update the correct tube model
            if currentTube == 1:
                # Update main output model
                outputModel = self.ui.outputSelector.currentNode()
                if outputModel:
                    outputModel.SetAndObservePolyData(tubePolyData)
                    
                    # Ensure proper display node and appearance
                    if not outputModel.GetDisplayNode():
                        outputModel.CreateDefaultDisplayNodes()
                    
                    displayNode = outputModel.GetDisplayNode()
                    if displayNode:
                        displayNode.SetColor(0.8, 0.2, 0.2)  # Red color
                        displayNode.SetOpacity(0.8)
                        displayNode.SetInterpolation(2)  # Gouraud shading for smooth appearance
                    
                    print(f"Updated main tube (Tube 1)")
            else:
                # Update additional tube model
                tubeName = f"EVARSim_Tube_{currentTube}"
                tubeModel = slicer.mrmlScene.GetFirstNodeByName(tubeName)
                if tubeModel:
                    tubeModel.SetAndObservePolyData(tubePolyData)
                    
                    # Ensure proper display node and appearance
                    if not tubeModel.GetDisplayNode():
                        tubeModel.CreateDefaultDisplayNodes()
                    
                    displayNode = tubeModel.GetDisplayNode()
                    if displayNode:
                        # Use different colors for different tubes
                        colors = [(0.8, 0.2, 0.2), (0.2, 0.8, 0.2), (0.2, 0.2, 0.8), (0.8, 0.8, 0.2)]
                        colorIndex = (currentTube - 1) % len(colors)
                        displayNode.SetColor(*colors[colorIndex])
                        displayNode.SetOpacity(0.8)
                        displayNode.SetInterpolation(2)  # Gouraud shading for smooth appearance
                    
                    print(f"Updated {tubeName}")
                else:
                    print(f"Could not find tube model: {tubeName}")
            
        except Exception as e:
            print(f"Error updating selected tube: {e}")

    def _onInputModelChanged(self) -> None:
        """Called when input model changes."""
        inputModel = self.ui.inputModelSelector.currentNode()
        if inputModel:
            self._analyzeBranches(inputModel)
        else:
            self.availableBranches = []
            self._updateBranchSelector()
            self._removeBranchLabels()  # Remove labels when no model selected
        self._checkCanApply()

    def _onBranchSelected(self) -> None:
        # Called when user selects a different branch.
        print(f"Branch selection changed to index {self.ui.branchSelector.currentIndex}")
        
        # Update only the currently selected tube with the new branch
        if self.ui.inputModelSelector.currentNode() and self.ui.outputSelector.currentNode():
            self._updateSelectedTube()

    def _analyzeBranches(self, inputModel: vtkMRMLModelNode) -> None:
        # Analyze input model to identify branches - only for VTK polyline files.
        try:
            polyData = inputModel.GetPolyData()
            if not polyData:
                self.availableBranches = []
                self._updateBranchSelector()
                return
            
            # Check if this is a VTK polyline file
            lines = polyData.GetLines()
            if not lines or lines.GetNumberOfCells() == 0:
                self.availableBranches = []
                self._updateBranchSelector()
                return
            
            # Analyze line segments
            lines.InitTraversal()
            line_segments = []
            all_points = []
            
            while True:
                idList = vtk.vtkIdList()
                if lines.GetNextCell(idList) == 0:
                    break
                    
                line_points = []
                for j in range(idList.GetNumberOfIds()):
                    point_id = idList.GetId(j)
                    line_points.append(point_id)
                
                if len(line_points) > 2:  # Only consider meaningful segments
                    line_segments.append(line_points)
                    all_points.extend(line_points)
            
            # Find the most frequently used point (likely the branch point)
            from collections import defaultdict
            point_counts = defaultdict(int)
            for point_id in all_points:
                point_counts[point_id] += 1
            
            # Find segments that start from the same point (branches)
            branches = []
            if len(line_segments) > 1:  # Only if we have multiple segments
                for i, segment in enumerate(line_segments):
                    start_coords = polyData.GetPoint(segment[0])
                    end_coords = polyData.GetPoint(segment[-1])
                    
                    branches.append({
                        'segment_id': i,
                        'points': segment,
                        'length': len(segment),
                        'start_coords': start_coords,
                        'end_coords': end_coords
                    })
            
            self.availableBranches = branches
            self._updateBranchSelector()
            self._createBranchLabels()
            
            print(f"Found {len(self.availableBranches)} branches in model")
            
        except Exception as e:
            print(f"Error analyzing branches: {e}")
            self.availableBranches = []
            self._updateBranchSelector()

    def _updateBranchSelector(self) -> None:
        # Update branch selector dropdown."""
        self.ui.branchSelector.clear()
        
        if len(self.availableBranches) == 0:
            self.ui.branchSelector.addItem("No branches detected")
            self.ui.branchSelector.setEnabled(False)
        else:
            for i, branch in enumerate(self.availableBranches):
                self.ui.branchSelector.addItem(f"Branch {i+1} ({branch['length']} points)")
            self.ui.branchSelector.setEnabled(True)

    def _createBranchLabels(self) -> None:
        # Create 3D text labels for each branch in the scene."""
        # First, remove any existing branch labels
        self._removeBranchLabels()
        
        if not self.availableBranches:
            return
            
        try:
            # Get the input model to find branch positions
            inputModel = self.ui.inputModelSelector.currentNode()
            if not inputModel:
                return
                
            polyData = inputModel.GetPolyData()
            if not polyData:
                return
            
            # Create labels for each branch using fiducial markups
            for i, branch in enumerate(self.availableBranches):
                # Use the end coordinates of each branch for better separation
                position = branch['end_coords']
                branchNumber = i + 1
                
                # Create a fiducial markup for this branch
                fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                fiducialNode.SetName(f"EVARSim_BranchLabel_{branchNumber}")
                
                # Add the fiducial point
                fiducialNode.AddControlPoint(position)
                fiducialNode.SetNthControlPointLabel(0, f"{branchNumber}")
                
                # Set display properties for better visibility
                displayNode = fiducialNode.GetDisplayNode()
                if displayNode:
                    displayNode.SetTextScale(4.0)  # Large text
                    displayNode.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow color
                    displayNode.SetColor(1.0, 1.0, 0.0)  # Yellow color
                    displayNode.SetGlyphScale(2.0)  # Small but visible glyph
                    displayNode.SetPointLabelsVisibility(True)  # Show labels
                    displayNode.SetPropertiesLabelVisibility(False)  # Hide properties
                    displayNode.SetGlyphType(1)  # Use sphere glyph
                
                print(f"Created branch label {branchNumber} at position {position}")
                
        except Exception as e:
            print(f"Error creating branch labels: {e}")

    def _removeBranchLabels(self) -> None:
        # Remove all existing branch labels from the scene."""
        try:
            # Remove fiducial nodes
            fiducialNodes = slicer.util.getNodesByClass("vtkMRMLMarkupsFiducialNode")
            for node in fiducialNodes:
                if node.GetName().startswith("EVARSim_BranchLabel_"):
                    slicer.mrmlScene.RemoveNode(node)
                    
        except Exception as e:
            print(f"Error removing branch labels: {e}")

    def onApplyButton(self) -> None:
        # Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to create device."), waitCursor=True):
            # Create cylindrical object along centerline
            self.logic.process(
                self.ui.centerlineSelector.currentNode(),
                self.ui.inputModelSelector.currentNode(),
                self.ui.outputSelector.currentNode(),
                self.ui.cylinderRadiusSliderWidget.value,
                self.ui.cylinderLengthSliderWidget.value,
                self.ui.cylinderPositionSliderWidget.value,
                int(self.ui.numberOfTubesSliderWidget.value),
                int(self.ui.cylinderResolutionSliderWidget.value)
            )


#
# EVARSimLogic
#


class EVARSimLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return EVARSimParameterNode(super().getParameterNode())

    def _extractCenterlineFromModel(self, inputModel: vtkMRMLModelNode) -> vtk.vtkPoints:
        """
        Extract centerline from input model geometry by finding the medial axis.
        For tubular structures, this attempts to find points that run through the center of the geometry.
        """
        import numpy as np
        
        polyData = inputModel.GetPolyData()
        if not polyData or polyData.GetNumberOfPoints() == 0:
            raise ValueError("Input model has no geometry")
        
                
        # Get model bounds
        bounds = polyData.GetBounds()
        print(f"Debug: Model bounds: {bounds}")
        
        # Create a more sophisticated centerline extraction
        # Sample points along the longest axis and project them to find the center of mass at each slice
        
        xRange = bounds[1] - bounds[0]
        yRange = bounds[3] - bounds[2] 
        zRange = bounds[5] - bounds[4]
        
        print(f"Debug: Ranges - X: {xRange}, Y: {yRange}, Z: {zRange}")
        
        # Determine the longest axis (this will be our sampling direction)
        if zRange >= xRange and zRange >= yRange:
            # Z is longest - sample along Z axis
            numSlices = 20
            points = vtk.vtkPoints()
            
            for i in range(numSlices):
                t = i / (numSlices - 1.0)
                z = bounds[4] + t * zRange
                
                # Find center of mass of points at this Z level
                centerX, centerY = self._findCenterAtLevel(polyData, 'z', z, bounds)
                points.InsertNextPoint([centerX, centerY, z])
                
        elif yRange >= xRange and yRange >= zRange:
            # Y is longest - sample along Y axis
            numSlices = 20
            points = vtk.vtkPoints()
            
            for i in range(numSlices):
                t = i / (numSlices - 1.0)
                y = bounds[2] + t * yRange
                
                # Find center of mass of points at this Y level
                centerX, centerZ = self._findCenterAtLevel(polyData, 'y', y, bounds)
                points.InsertNextPoint([centerX, y, centerZ])
                
        else:
            # X is longest - sample along X axis
            numSlices = 20
            points = vtk.vtkPoints()
            
            for i in range(numSlices):
                t = i / (numSlices - 1.0)
                x = bounds[0] + t * xRange
                
                # Find center of mass of points at this X level
                centerY, centerZ = self._findCenterAtLevel(polyData, 'x', x, bounds)
                points.InsertNextPoint([x, centerY, centerZ])
        
        return points

    def _findCenterAtLevel(self, polyData: vtk.vtkPolyData, axis: str, level: float, bounds) -> tuple:
        
        # Find the center of mass of model points at a specific level along the given axis.
        
        import numpy as np
        
        # Get all points from the model
        points = []
        tolerance = max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4]) * 0.05  # 5% of largest dimension
        
        for i in range(polyData.GetNumberOfPoints()):
            point = polyData.GetPoint(i)
            
            # Check if point is at the current level (within tolerance)
            if axis == 'x' and abs(point[0] - level) <= tolerance:
                points.append([point[1], point[2]])  # Y, Z
            elif axis == 'y' and abs(point[1] - level) <= tolerance:
                points.append([point[0], point[2]])  # X, Z
            elif axis == 'z' and abs(point[2] - level) <= tolerance:
                points.append([point[0], point[1]])  # X, Y
        
        if len(points) == 0:
            # No points at this level, use bounding box center
            if axis == 'x':
                return ((bounds[2] + bounds[3]) / 2.0, (bounds[4] + bounds[5]) / 2.0)
            elif axis == 'y':
                return ((bounds[0] + bounds[1]) / 2.0, (bounds[4] + bounds[5]) / 2.0)
            else:  # axis == 'z'
                return ((bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0)
        
        # Calculate center of mass
        points = np.array(points)
        center = np.mean(points, axis=0)
        return (center[0], center[1])

    def _positionTubeAlongCenterline(self, curvePoints: vtk.vtkPoints, tubeLength: float, position: float) -> vtk.vtkPoints:
        """
        Extract a segment of the centerline for tube placement at the specified position.
        :param curvePoints: All centerline points
        :param tubeLength: Length of the tube to create
        :param position: Position along centerline (0.0 = start, 1.0 = end)
        """
        import numpy as np
        
        if curvePoints.GetNumberOfPoints() < 2:
            return curvePoints
        
        # Calculate total centerline length
        totalLength = 0.0
        segmentLengths = []
        
        prevPoint = np.array([0, 0, 0])
        curvePoints.GetPoint(0, prevPoint)
        
        for i in range(1, curvePoints.GetNumberOfPoints()):
            currentPoint = np.array([0, 0, 0])
            curvePoints.GetPoint(i, currentPoint)
            
            segmentLength = np.linalg.norm(currentPoint - prevPoint)
            segmentLengths.append(segmentLength)
            totalLength += segmentLength
            prevPoint = currentPoint
        
        # Calculate start position along centerline based on position parameter
        # Position 0.0 means tube starts at beginning
        # Position 1.0 means tube ends at the end
        if position == 0.0:
            startDistance = 0.0
        elif position == 1.0:
            startDistance = max(0.0, totalLength - tubeLength)
        else:
            # Position the tube so that position parameter represents center of tube
            centerDistance = position * totalLength
            startDistance = max(0.0, centerDistance - tubeLength / 2.0)
        
        endDistance = min(totalLength, startDistance + tubeLength)
        
        # Extract points between startDistance and endDistance
        positionedPoints = vtk.vtkPoints()
        currentDistance = 0.0
        
        # Add starting point
        if startDistance == 0.0:
            startPoint = [0, 0, 0]
            curvePoints.GetPoint(0, startPoint)
            positionedPoints.InsertNextPoint(startPoint)
        
        # Walk through segments and extract the tube portion
        segmentStart = 0.0
        for i in range(len(segmentLengths)):
            segmentEnd = segmentStart + segmentLengths[i]
            
            # If this segment intersects with our tube range
            if segmentEnd > startDistance and segmentStart < endDistance:
                # Get segment endpoints
                point1 = np.array([0, 0, 0])
                point2 = np.array([0, 0, 0])
                curvePoints.GetPoint(i, point1)
                curvePoints.GetPoint(i + 1, point2)
                
                # Calculate intersection points
                if segmentStart < startDistance < segmentEnd:
                    # Start of tube is within this segment
                    t = (startDistance - segmentStart) / segmentLengths[i]
                    startTubePoint = point1 + t * (point2 - point1)
                    positionedPoints.InsertNextPoint(startTubePoint)
                
                if startDistance <= segmentStart and segmentEnd <= endDistance:
                    # Entire segment is within tube
                    positionedPoints.InsertNextPoint(point2)
                
                if segmentStart < endDistance < segmentEnd:
                    # End of tube is within this segment
                    t = (endDistance - segmentStart) / segmentLengths[i]
                    endTubePoint = point1 + t * (point2 - point1)
                    positionedPoints.InsertNextPoint(endTubePoint)
            
            segmentStart = segmentEnd
        
        return positionedPoints

    def _createTubeAlongCurve(self, curvePoints: vtk.vtkPoints, radius: float, resolution: int) -> vtk.vtkPolyData:
        
        # Create a device that follows the curve points.
        
        import numpy as np
        
        # Use the resolution as specified, but ensure it's reasonable for smooth appearance
        actualResolution = max(int(resolution), 8)  # Minimum 8 sides
        
        # Ensure we have enough points for a proper tube
        if curvePoints.GetNumberOfPoints() < 2:
            return vtk.vtkPolyData()
        
        # Create tube body without caps first
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(curvePoints.GetNumberOfPoints())
        
        # Create polydata with the curve points
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(curvePoints)
        
        for i in range(curvePoints.GetNumberOfPoints()):
            polyline.GetPointIds().SetId(i, i)
            
        # Create cell array and add the polyline
        cells = vtk.vtkCellArray()
        cells.InsertNextCell(polyline)
        polyData.SetLines(cells)
        
        # Use vtkTubeFilter to create the tube body without caps
        tubeFilter = vtk.vtkTubeFilter()
        tubeFilter.SetInputData(polyData)
        tubeFilter.SetRadius(radius)
        tubeFilter.SetNumberOfSides(actualResolution)
        tubeFilter.SetCapping(False)  # Don't use VTK's angled caps
        tubeFilter.SetVaryRadiusToVaryRadiusOff()  # Uniform radius
        tubeFilter.SetGenerateTCoords(False)  # Don't generate texture coordinates
        tubeFilter.Update()
        
        # Now create proper rigid end caps
        tubeWithCaps = self._addRigidEndCaps(tubeFilter.GetOutput(), curvePoints, radius, actualResolution)
        
        # Clean up the geometry
        cleanFilter = vtk.vtkCleanPolyData()
        cleanFilter.SetInputData(tubeWithCaps)
        cleanFilter.SetTolerance(0.0001)
        cleanFilter.Update()
        
        # Generate proper normals for smooth shading
        normalGenerator = vtk.vtkPolyDataNormals()
        normalGenerator.SetInputData(cleanFilter.GetOutput())
        normalGenerator.ComputePointNormalsOn()
        normalGenerator.ComputeCellNormalsOn()
        normalGenerator.SplittingOff()  # Keep vertices shared for smooth appearance
        normalGenerator.ConsistencyOn()
        normalGenerator.AutoOrientNormalsOn()
        normalGenerator.Update()
        
        return normalGenerator.GetOutput()
    
    def _addRigidEndCaps(self, tubePolyData: vtk.vtkPolyData, curvePoints: vtk.vtkPoints, 
                        radius: float, resolution: int) -> vtk.vtkPolyData:
        # Add rigid, perpendicular end caps to the tube like real stents. 
        # TODO: I have to rethink this step
        
        import numpy as np
        
        # Create a copy of the tube to modify
        appendFilter = vtk.vtkAppendPolyData()
        appendFilter.AddInputData(tubePolyData)
        
        # Get the first and last points of the centerline
        firstPoint = np.array(curvePoints.GetPoint(0))
        lastPoint = np.array(curvePoints.GetPoint(curvePoints.GetNumberOfPoints() - 1))
        
        # Calculate direction vectors for the ends
        if curvePoints.GetNumberOfPoints() > 1:
            # Direction at start (from first to second point)
            secondPoint = np.array(curvePoints.GetPoint(1))
            startDirection = secondPoint - firstPoint
            startDirection = startDirection / np.linalg.norm(startDirection)
            
            # Direction at end (from second-to-last to last point)
            secondLastPoint = np.array(curvePoints.GetPoint(curvePoints.GetNumberOfPoints() - 2))
            endDirection = lastPoint - secondLastPoint
            endDirection = endDirection / np.linalg.norm(endDirection)
        else:
            # Fallback for single segment
            direction = lastPoint - firstPoint
            direction = direction / np.linalg.norm(direction)
            startDirection = direction
            endDirection = direction
        
        # Create rigid circular end caps
        startCap = self._createCircularCap(firstPoint, -startDirection, radius, resolution)
        endCap = self._createCircularCap(lastPoint, endDirection, radius, resolution)
        
        # Append the caps to the tube
        appendFilter.AddInputData(startCap)
        appendFilter.AddInputData(endCap)
        appendFilter.Update()
        
        return appendFilter.GetOutput()
    
    def _createCircularCap(self, center, normal, radius: float, resolution: int) -> vtk.vtkPolyData:
        # Create a rigid circular cap perpendicular to the given normal direction.
        # TODO: See above
        
        import numpy as np
        
        # Normalize the normal vector
        normal = normal / np.linalg.norm(normal)
        
        # Create two perpendicular vectors to the normal
        if abs(normal[2]) < 0.9:
            up = np.array([0, 0, 1])
        else:
            up = np.array([1, 0, 0])
        
        # Create orthogonal basis vectors
        u = np.cross(normal, up)
        u = u / np.linalg.norm(u)
        v = np.cross(normal, u)
        v = v / np.linalg.norm(v)
        
        # Create points for the circular cap
        points = vtk.vtkPoints()
        
        # Center point
        points.InsertNextPoint(center)
        
        # Circle points
        for i in range(resolution):
            angle = 2.0 * np.pi * i / resolution
            x = radius * (np.cos(angle) * u + np.sin(angle) * v)
            point = center + x
            points.InsertNextPoint(point)
        
        # Create triangular faces for the cap
        cells = vtk.vtkCellArray()
        
        for i in range(resolution):
            triangle = vtk.vtkTriangle()
            triangle.GetPointIds().SetId(0, 0)  # Center
            triangle.GetPointIds().SetId(1, i + 1)  # Current point
            triangle.GetPointIds().SetId(2, ((i + 1) % resolution) + 1)  # Next point
            cells.InsertNextCell(triangle)
        
        # Create the polydata
        capPolyData = vtk.vtkPolyData()
        capPolyData.SetPoints(points)
        capPolyData.SetPolys(cells)
        
        return capPolyData


    def _createMultipleTubes(self, curvePoints: vtk.vtkPoints, radius: float, length: float, 
                           basePosition: float, numberOfTubes: int, resolution: int) -> vtk.vtkPolyData:
        # Create multiple tubes along the centerline with automatic spacing.

        import numpy as np
        
        # Calculate total centerline length
        totalLength = 0.0
        prevPoint = np.array([0, 0, 0])
        curvePoints.GetPoint(0, prevPoint)
        
        for i in range(1, curvePoints.GetNumberOfPoints()):
            currentPoint = np.array([0, 0, 0])
            curvePoints.GetPoint(i, currentPoint)
            segmentLength = np.linalg.norm(currentPoint - prevPoint)
            totalLength += segmentLength
            prevPoint = currentPoint
        
        # Calculate tube positions
        if numberOfTubes == 1:
            positions = [basePosition]
        else:
            # Distribute tubes evenly along the centerline
            # Base position determines the center of the distribution
            totalSpanNeeded = (numberOfTubes - 1) * length * 0.8  # 20% overlap between tubes
            maxSpan = min(totalSpanNeeded, totalLength - length)  # Don't exceed centerline
            
            if maxSpan <= 0:
                # If tubes don't fit, just place them at the base position
                positions = [basePosition] * numberOfTubes
            else:
                # Calculate span based on base position
                spanCenter = basePosition
                spanStart = max(0.0, spanCenter - maxSpan / (2 * totalLength))
                spanEnd = min(1.0, spanCenter + maxSpan / (2 * totalLength))
                
                # Distribute positions evenly within the span
                if numberOfTubes == 2:
                    positions = [spanStart, spanEnd]
                else:
                    positions = []
                    for i in range(numberOfTubes):
                        t = i / (numberOfTubes - 1)
                        pos = spanStart + t * (spanEnd - spanStart)
                        positions.append(pos)
        
        # Create individual tubes
        tubePolyDataList = []
        for i, pos in enumerate(positions):
            positionedPoints = self._positionTubeAlongCenterline(curvePoints, length, pos)
            if positionedPoints.GetNumberOfPoints() >= 2:
                tubePolyData = self._createTubeAlongCurve(positionedPoints, radius, resolution)
                tubePolyDataList.append(tubePolyData)
        
        if len(tubePolyDataList) == 0:
            raise ValueError("Could not create any tubes")
        elif len(tubePolyDataList) == 1:
            return tubePolyDataList[0]
        else:
            # Combine multiple tubes into one polydata
            return self._combineTubes(tubePolyDataList)

    def _combineTubes(self, tubePolyDataList) -> vtk.vtkPolyData:
        """
        Combine multiple tube polydata objects into a single polydata.
        """
        # Use vtkAppendPolyData to combine all tubes
        appendFilter = vtk.vtkAppendPolyData()
        
        for tubePolyData in tubePolyDataList:
            appendFilter.AddInputData(tubePolyData)
        
        appendFilter.Update()
        return appendFilter.GetOutput()

    def _createSeparateTubes(self, curvePoints: vtk.vtkPoints, radius: float, length: float,
                           basePosition: float, numberOfTubes: int, resolution: int, outputModel: vtkMRMLModelNode):
                           
        # Create multiple tubes as separate models that can be controlled individually.

        import numpy as np
        
        # Calculate evenly distributed positions
        positions = []
        if numberOfTubes == 1:
            positions = [basePosition]
        else:
            # Distribute tubes evenly from 0.1 to 0.9 to avoid edges
            for i in range(numberOfTubes):
                if numberOfTubes == 2:
                    pos = 0.2 + i * 0.6  # 0.2, 0.8
                else:
                    pos = 0.1 + i * (0.8 / (numberOfTubes - 1))  # Spread from 0.1 to 0.9
                positions.append(pos)
        
        # Clear any existing models with tube names
        self._clearExistingTubes(numberOfTubes)
        
        # Create individual tube models
        for i, pos in enumerate(positions):
            # Create a new model for each tube
            tubeName = f"EVARSim_Tube_{i+1}"
            tubeModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
            tubeModel.SetName(tubeName)
            
            # Create the tube geometry
            positionedPoints = self._positionTubeAlongCenterline(curvePoints, length, pos)
            if positionedPoints.GetNumberOfPoints() >= 2:
                tubePolyData = self._createTubeAlongCurve(positionedPoints, radius, resolution)
                tubeModel.SetAndObservePolyData(tubePolyData)
                
                # Create display node
                if not tubeModel.GetDisplayNode():
                    tubeModel.CreateDefaultDisplayNodes()
                
                # Set different colors for each tube
                displayNode = tubeModel.GetDisplayNode()
                colors = [
                    [0.8, 0.2, 0.2],  # Red
                    [0.2, 0.8, 0.2],  # Green
                    [0.2, 0.2, 0.8],  # Blue
                    [0.8, 0.8, 0.2],  # Yellow
                    [0.8, 0.2, 0.8],  # Magenta
                    [0.2, 0.8, 0.8],  # Cyan
                    [0.8, 0.5, 0.2],  # Orange
                    [0.5, 0.8, 0.2],  # Lime
                    [0.8, 0.2, 0.5],  # Pink
                    [0.5, 0.2, 0.8],  # Purple
                ]
                color = colors[i % len(colors)]
                displayNode.SetColor(color[0], color[1], color[2])
                displayNode.SetOpacity(0.8)
        
        # Set the output model to be empty (since we created separate models)
        emptyPolyData = vtk.vtkPolyData()
        outputModel.SetAndObservePolyData(emptyPolyData)
        
        print(f"Created {numberOfTubes} separate tube models")

    def _createAdditionalTubes(self, curvePoints: vtk.vtkPoints, radius: float, length: float,
                              numberOfTubes: int, resolution: int):
        """
        Create additional tubes as separate models.
        """
        # Clear existing additional tubes first
        self._clearExistingTubes()
        
        # Create additional tubes (tube 2, 3, etc.)
        for i in range(1, numberOfTubes):  # Start from 1 since tube 1 is the main output
            # Calculate position for this additional tube
            position = 0.2 + (i * 0.6 / (numberOfTubes - 1))  # Distribute from 0.2 to 0.8
            
            # Create the tube model
            tubeName = f"EVARSim_Tube_{i+1}"
            tubeModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
            tubeModel.SetName(tubeName)
            
            # Create the tube geometry
            positionedPoints = self._positionTubeAlongCenterline(curvePoints, length, position)
            
            print(f"Debug: Creating tube {i+1} at position {position}, points: {positionedPoints.GetNumberOfPoints()}")
            
            if positionedPoints.GetNumberOfPoints() >= 2:
                tubePolyData = self._createTubeAlongCurve(positionedPoints, radius, resolution)
                tubeModel.SetAndObservePolyData(tubePolyData)
                
                # Create display node
                if not tubeModel.GetDisplayNode():
                    tubeModel.CreateDefaultDisplayNodes()
                
                # Set different colors for each tube
                displayNode = tubeModel.GetDisplayNode()
                colors = [
                    [0.2, 0.8, 0.2],  # Green
                    [0.2, 0.2, 0.8],  # Blue
                    [0.8, 0.8, 0.2],  # Yellow
                    [0.8, 0.2, 0.8],  # Magenta
                    [0.2, 0.8, 0.8],  # Cyan
                    [0.8, 0.5, 0.2],  # Orange
                    [0.5, 0.8, 0.2],  # Lime
                    [0.8, 0.2, 0.5],  # Pink
                    [0.5, 0.2, 0.8],  # Purple
                ]
                color = colors[(i-1) % len(colors)]
                displayNode.SetColor(color[0], color[1], color[2])
                displayNode.SetOpacity(0.8)
                
                print(f"Debug: Successfully created tube {i+1}")
            else:
                print(f"Debug: Failed to create tube {i+1} - not enough points")

    def _clearExistingTubes(self):
        """
        Remove any existing additional tube models from previous runs.
        """
        # Remove old tube models
        for i in range(2, 11):  # Start from 2 since tube 1 is the main output
            tubeName = f"EVARSim_Tube_{i}"
            existingNode = slicer.mrmlScene.GetFirstNodeByName(tubeName)
            if existingNode:
                slicer.mrmlScene.RemoveNode(existingNode)
                print(f"Debug: Removed existing tube {i}")

    def _extractBranchCenterline(self, inputModel: vtkMRMLModelNode, branchIndex: int) -> vtk.vtkPoints:
        """Extract centerline points for a specific branch."""
        try:
            polyData = inputModel.GetPolyData()
            if not polyData:
                return vtk.vtkPoints()
            
            # Get line segments
            lines = polyData.GetLines()
            if not lines:
                return vtk.vtkPoints()
            
            lines.InitTraversal()
            line_segments = []
            
            while True:
                idList = vtk.vtkIdList()
                if lines.GetNextCell(idList) == 0:
                    break
                    
                line_points = []
                for j in range(idList.GetNumberOfIds()):
                    point_id = idList.GetId(j)
                    line_points.append(point_id)
                
                if len(line_points) > 2:  # Only consider meaningful segments
                    line_segments.append(line_points)
            
            # Get the requested branch
            if branchIndex < 0 or branchIndex >= len(line_segments):
                print(f"Branch index {branchIndex} out of range (0-{len(line_segments)-1})")
                return vtk.vtkPoints()
            
            selectedSegment = line_segments[branchIndex]
            
            # Extract points from the selected segment
            points = vtk.vtkPoints()
            for pointId in selectedSegment:
                point = polyData.GetPoint(pointId)
                points.InsertNextPoint(point)
            
            print(f"Extracted {points.GetNumberOfPoints()} points from branch {branchIndex}")
            return points
            
        except Exception as e:
            print(f"Error extracting branch centerline: {e}")
            return vtk.vtkPoints()

    def _smoothCenterline(self, points: vtk.vtkPoints, smoothingFactor: float = 0.5) -> vtk.vtkPoints:
        """
        Smooth the centerline points using conservative moving average.
        This keeps the tube on the centerline while reducing sharp angles.
        :param points: Input centerline points
        :param smoothingFactor: Smoothing factor (0.0 = no smoothing, 1.0 = maximum smoothing)
        :return: Smoothed centerline points
        """
        try:
            import numpy as np
            
            if not points or points.GetNumberOfPoints() < 3 or smoothingFactor <= 0:
                return points
            
            # Convert VTK points to numpy array
            numPoints = points.GetNumberOfPoints()
            pointsArray = np.zeros((numPoints, 3))
            
            for i in range(numPoints):
                point = points.GetPoint(i)
                pointsArray[i] = [point[0], point[1], point[2]]
            
            # Apply conservative smoothing using moving average
            # Window size based on smoothing factor (smaller window = less deviation)
            windowSize = max(3, int(3 + smoothingFactor * 4))  # Range: 3 to 7 points
            if windowSize % 2 == 0:
                windowSize += 1  # Make it odd
            
            print(f"Applying smoothing with window size: {windowSize}")
            
            # Create smoothed points array
            smoothedArray = np.copy(pointsArray)
            
            # Apply moving average smoothing, but preserve endpoints
            for coord in range(3):
                for i in range(windowSize//2, numPoints - windowSize//2):
                    # Calculate weighted average with emphasis on center point
                    weights = np.ones(windowSize)
                    weights[windowSize//2] = 2.0  # Give more weight to center point
                    
                    # Extract window of points
                    window = pointsArray[i-windowSize//2:i+windowSize//2+1, coord]
                    
                    # Calculate weighted average
                    smoothedArray[i, coord] = np.average(window, weights=weights)
            
            # Blend original and smoothed points based on smoothing factor
            blendedArray = (1.0 - smoothingFactor) * pointsArray + smoothingFactor * smoothedArray
            
            # Create output points
            smoothedPoints = vtk.vtkPoints()
            for i in range(numPoints):
                smoothedPoints.InsertNextPoint(blendedArray[i, 0], blendedArray[i, 1], blendedArray[i, 2])
            
            print(f"Applied conservative smoothing to {numPoints} points")
            return smoothedPoints
            
        except Exception as e:
            print(f"Error smoothing centerline: {e}")
            print("Falling back to original points")
            return points

    def _reduceCenterlinePoints(self, points: vtk.vtkPoints) -> vtk.vtkPoints:
        """
        Reduce centerline to only 4 key points: first, last, and 2 evenly spaced intermediate points.
        This creates smoother tubes by using fewer control points.
        :param points: Input centerline points
        :return: Reduced centerline with only 4 points
        """
        try:
            if not points or points.GetNumberOfPoints() < 2:
                return points
            
            numPoints = points.GetNumberOfPoints()
            
            # If we already have 4 or fewer points, return as is
            if numPoints <= 4:
                return points
            
            # Create reduced points
            reducedPoints = vtk.vtkPoints()
            
            # Always include first point
            reducedPoints.InsertNextPoint(points.GetPoint(0))
            
            # Add two intermediate points at 1/3 and 2/3 positions
            oneThirdIndex = numPoints // 3
            twoThirdIndex = (2 * numPoints) // 3
            
            reducedPoints.InsertNextPoint(points.GetPoint(oneThirdIndex))
            reducedPoints.InsertNextPoint(points.GetPoint(twoThirdIndex))
            
            # Always include last point
            reducedPoints.InsertNextPoint(points.GetPoint(numPoints - 1))
            
            # Apply spline smoothing to the 4 control points
            smoothedPoints = self._applySplineSmoothing(reducedPoints)
            
            print(f"Reduced centerline from {numPoints} to {smoothedPoints.GetNumberOfPoints()} points with spline smoothing")
            return smoothedPoints
            
        except Exception as e:
            print(f"Error reducing centerline points: {e}")
            print("Falling back to original points")
            return points

    def _applySplineSmoothing(self, points: vtk.vtkPoints, numOutputPoints: int = 20) -> vtk.vtkPoints:
        """
        Apply spline smoothing to the control points to create a smooth curve.
        Uses VTK spline interpolation to generate more points along a smooth curve.
        :param points: Input control points (typically 4 points)
        :param numOutputPoints: Number of points to generate along the smooth curve
        :return: Smoothed points along spline curve
        """
        try:
            if not points or points.GetNumberOfPoints() < 2:
                return points
            
            numControlPoints = points.GetNumberOfPoints()
            
            # If we have only 2 points, just do linear interpolation
            if numControlPoints == 2:
                outputPoints = vtk.vtkPoints()
                for i in range(numOutputPoints):
                    t = i / (numOutputPoints - 1.0)
                    p1 = points.GetPoint(0)
                    p2 = points.GetPoint(1)
                    interpPoint = [
                        p1[0] + t * (p2[0] - p1[0]),
                        p1[1] + t * (p2[1] - p1[1]),
                        p1[2] + t * (p2[2] - p1[2])
                    ]
                    outputPoints.InsertNextPoint(interpPoint)
                return outputPoints
            
            # For 3 or more points, use spline interpolation
            # Create parametric splines for each coordinate
            xSpline = vtk.vtkCardinalSpline()
            ySpline = vtk.vtkCardinalSpline()
            zSpline = vtk.vtkCardinalSpline()
            
            # Add control points to splines
            for i in range(numControlPoints):
                point = points.GetPoint(i)
                t = float(i)  # Parameter value
                xSpline.AddPoint(t, point[0])
                ySpline.AddPoint(t, point[1])
                zSpline.AddPoint(t, point[2])
            
            # Generate smooth curve points
            outputPoints = vtk.vtkPoints()
            maxT = float(numControlPoints - 1)
            
            for i in range(numOutputPoints):
                # Parameter from 0 to maxT
                t = (i / (numOutputPoints - 1.0)) * maxT
                
                # Evaluate splines at this parameter
                x = xSpline.Evaluate(t)
                y = ySpline.Evaluate(t)
                z = zSpline.Evaluate(t)
                
                outputPoints.InsertNextPoint(x, y, z)
            
            print(f"Applied spline smoothing: {numControlPoints} control points -> {numOutputPoints} smooth points")
            return outputPoints
            
        except Exception as e:
            print(f"Error applying spline smoothing: {e}")
            print("Falling back to original points")
            return points

    def process(self,
                centerlineCurve: vtkMRMLMarkupsCurveNode,
                inputModel: vtkMRMLModelNode,
                outputModel: vtkMRMLModelNode,
                radius: float,
                length: float,
                position: float,
                numberOfTubes: int,
                resolution: int,
                showResult: bool = True) -> None:
        """
        Create tubes along a centerline curve or extracted from input model.
        Can be used without GUI widget.
        :param centerlineCurve: curve that defines the centerline for cylinder placement (optional)
        :param inputModel: model from which to extract centerline (optional, alternative to centerlineCurve)
        :param outputModel: output model that will contain the cylindrical objects
        :param radius: radius of the cylindrical objects
        :param length: length of each cylindrical object
        :param position: base position along centerline (0.0 = start, 1.0 = end)
        :param numberOfTubes: number of tubes to create
        :param resolution: resolution (number of sides) of the cylinders
        :param showResult: show output model in 3D view
        """

        if not outputModel:
            raise ValueError("Output model is invalid")
            
        if not centerlineCurve and not inputModel:
            raise ValueError("Either centerline curve or input model must be provided")

        import time
        import numpy as np

        startTime = time.time()
        logging.info("Creating cylindrical object started")

        # Get curve points from either centerline curve or extract from model
        if centerlineCurve:
            curvePoints = centerlineCurve.GetCurvePointsWorld()
            if not curvePoints or curvePoints.GetNumberOfPoints() < 2:
                raise ValueError("Centerline curve must have at least 2 points")
        else:
            # For VTK polyline models, extract the actual polyline data instead of synthesizing
            polyData = inputModel.GetPolyData()
            if polyData and polyData.GetLines() and polyData.GetLines().GetNumberOfCells() > 0:
                # This is a VTK polyline file - extract the actual polyline
                curvePoints = vtk.vtkPoints()
                
                # Get the first line segment (or could be modified to use branch selection)
                lines = polyData.GetLines()
                lines.InitTraversal()
                idList = vtk.vtkIdList()
                if lines.GetNextCell(idList):
                    for i in range(idList.GetNumberOfIds()):
                        pointId = idList.GetId(i)
                        point = polyData.GetPoint(pointId)
                        curvePoints.InsertNextPoint(point)
                
                if curvePoints.GetNumberOfPoints() < 2:
                    raise ValueError("Could not extract valid polyline from input model")
            else:
                # Fallback to synthetic centerline extraction for non-polyline models
                curvePoints = self._extractCenterlineFromModel(inputModel)
                if not curvePoints or curvePoints.GetNumberOfPoints() < 2:
                    raise ValueError("Could not extract valid centerline from input model")

        # Apply smoothing to the centerline
        smoothingFactor = 0.3  # Default smoothing factor for the process method
        if smoothingFactor > 0:
            curvePoints = self._smoothCenterline(curvePoints, smoothingFactor)
        
        # First position the tube segment, then reduce to 4 points
        positionedPoints = self._positionTubeAlongCenterline(curvePoints, length, position)
        
        # Always reduce the positioned segment to 4 points for smooth tubes
        reducedPoints = self._reduceCenterlinePoints(positionedPoints)
        tubePolyData = self._createTubeAlongCurve(reducedPoints, radius, resolution)
        
        # If multiple tubes requested, create additional separate models
        if numberOfTubes > 1:
            self._createAdditionalTubes(reducedPoints, radius, length, numberOfTubes, resolution)
        
        # Debug output
        print(f"Debug: Original points: {curvePoints.GetNumberOfPoints()}")
        print(f"Debug: Number of tubes: {numberOfTubes}")
        print(f"Debug: Position: {position}, Length: {length}")

        # Set the polydata to the output model
        outputModel.SetAndObservePolyData(tubePolyData)
        
        # Create display node if it doesn't exist
        if not outputModel.GetDisplayNode():
            outputModel.CreateDefaultDisplayNodes()
        
        # Set appearance properties
        displayNode = outputModel.GetDisplayNode()
        if displayNode:
            displayNode.SetColor(0.8, 0.2, 0.2)  # Set red color
            displayNode.SetOpacity(0.8)
        else:
            print("Warning: Could not create display node for main tube")

        if showResult:
            # Center the view on the created model
            layoutManager = slicer.app.layoutManager()
            threeDWidget = layoutManager.threeDWidget(0)
            threeDView = threeDWidget.threeDView()
            threeDView.resetFocalPoint()
            
            # Also reset slice views to show the model
            slicer.util.resetSliceViews()

        stopTime = time.time()
        logging.info(f"Cylindrical object creation completed in {stopTime-startTime:.2f} seconds")


#
# EVARSimTest
#


class EVARSimTest(ScriptedLoadableModuleTest):
    """
    This is the test case for the scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_EVARSim1()

    def test_EVARSim1(self):
        """Test the cylindrical object creation functionality."""

        self.delayDisplay("Starting the cylindrical object creation test")

        # Create test centerline curve
        centerlineCurve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        centerlineCurve.SetName("Test Centerline")
        
        # Add control points to create a simple straight line
        centerlineCurve.AddControlPoint([0, 0, 0])
        centerlineCurve.AddControlPoint([0, 0, 10])
        
        self.delayDisplay("Created test centerline curve")

        # Create output model
        outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        outputModel.SetName("Test Cylinder")

        # Test the module logic
        logic = EVARSimLogic()

        # Test cylinder creation with default parameters
        radius = 2.0
        length = 10.0
        resolution = 16
        
        logic.process(centerlineCurve, outputModel, radius, length, resolution)
        
        # Verify that the model has polydata
        self.assertIsNotNone(outputModel.GetPolyData())
        self.assertGreater(outputModel.GetPolyData().GetNumberOfPoints(), 0)
        self.assertGreater(outputModel.GetPolyData().GetNumberOfCells(), 0)

        self.delayDisplay("Test passed: Cylindrical object created successfully")
