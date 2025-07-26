<img src="Resources/Icons/1.jpeg" width="300" height="600">

# EVARSim - Endovascular Aneurysm Repair Simulation Extension

A 3D Slicer extension for simulating endovascular stent placement along vessel centerlines, specifically designed for EVAR (Endovascular Aneurysm Repair) procedures.

## Overview

EVARSim enables medical professionals and researchers to visualize and simulate stent placement along complex vessel geometries. The extension creates cylindrical stents that follow vessel centerlines.

## Key Features

- **Multiple Stent Support**: Place up to multiple independent stents with individual parameter control
- **Branch Selection**: Support for branched vessel structures (e.g., inverted Y configurations)
- **Real-time Parameter Adjustment**: Live updates of stent radius, length, position, and resolution
- **Smooth Curve Following**: Advanced spline interpolation for natural stent curvature
- **Professional Appearance**: Rigid end caps and smooth surfaces mimicking real stents
- **3D Branch Labeling**: Visual branch numbering for easy identification
- **Centerline Smoothing**: Conservative smoothing to reduce sharp angles while maintaining accuracy

## Installation

1. **Download**: Clone or download this repository
2. **3D Slicer**: Ensure you have 3D Slicer 5.0+ installed
3. **Load Extension**: 
   - Open 3D Slicer
   - Go to `Edit` → `Application Settings` → `Modules`
   - Add the EVARSim directory to the module paths
   - Restart 3D Slicer
4. **Access Module**: Find "EVARSim" in the module dropdown under the "Examples" category

## Usage

### Basic Workflow

1. **Load Centerline Data**:
   - Use the "Input Model" selector to load a VTK polydata file containing vessel centerlines
   - Alternatively, use the "Centerline" selector for markup curve nodes

2. **Select Output Model**:
   - Choose or create an output model node where the stent will be displayed

3. **Configure Stent Parameters**:
   - **Radius**: Control stent diameter (0.1 - 10.0 units)
   - **Length**: Set stent length (1.0 - 200.0 units)  
   - **Position**: Place stent along centerline (0.0 = start, 1.0 = end)
   - **Resolution**: Adjust surface smoothness (4-32 sides)

4. **Multiple Stents** (Optional):
   - Use "Number of Tubes" slider to create multiple stents
   - Select individual stents from the "Tube Selector" dropdown
   - Each stent has independent parameters

5. **Branch Selection** (For Branched Vessels):
   - Branched centerlines automatically show branch selector
   - Choose specific branch for each stent
   - Branch numbers are displayed in 3D view

6. **Advanced Options**:
   - **Smoothing Factor**: Apply conservative centerline smoothing (0.0 - 1.0)
   - Real-time parameter updates as you adjust sliders

### File Format Requirements

**Supported Input Formats**:
- **VTK Polydata (.vtk)**: Containing polyline data representing vessel centerlines
- **3D Slicer Markup Curves**: Created using Slicer's markup tools

**VTK Polydata Structure**:
- Must contain `LINES` data representing centerline segments
- Points should be ordered sequentially along vessel paths
- Branched structures supported (multiple line segments)

### Branch Support

For branched vessel structures (e.g., aortic bifurcations):

1. **Automatic Detection**: EVARSim automatically detects multiple branches in VTK files
2. **Visual Labels**: Branch numbers appear as yellow labels at branch endpoints
3. **Individual Selection**: Each stent can be assigned to a specific branch
4. **Independent Control**: All parameters can be set independently per stent

### Tips for Best Results

- **Centerline Quality**: Use high-quality, properly oriented centerlines for best results
- **Length Settings**: For full-length stents, use length values ≥100 units
- **Multiple Stents**: Use different colors automatically assigned to distinguish multiple stents
- **Smoothing**: Start with smoothing factor 0.3, adjust based on centerline complexity
- **Resolution**: Higher resolution (16-32) for final visualization, lower (8-16) for real-time adjustment

## Technical Details

### Algorithm Overview

1. **Centerline Processing**:
   - Load and analyze input centerline data
   - Apply optional conservative smoothing
   - Extract specific segments based on length/position parameters

2. **Control Point Reduction**:
   - Reduce segment to 4 strategic control points
   - Ensures smooth curves while maintaining shape fidelity

3. **Spline Interpolation**:
   - Apply VTK Cardinal Spline smoothing to control points
   - Generate 20 smooth interpolated points along curve

4. **Stent Generation**:
   - Create cylindrical geometry using VTK TubeFilter
   - Add rigid, perpendicular end caps
   - Apply proper surface normals for smooth appearance

### Dependencies

- **3D Slicer 5.0+**
- **VTK 9.0+** (included with Slicer)
- **NumPy** (included with Slicer)
- **Python 3.9+** (included with Slicer)

## Example Data

The extension includes `CL_model.vtk` - a sample branched centerline file of the aorta and the aortic bifurcation.

## Troubleshooting

**Common Issues**:

- **No stent appears**: Check that input model contains valid polyline data
- **Stent in wrong position**: Verify centerline orientation and adjust position parameter
- **Rough surface**: Increase resolution parameter or check centerline quality
- **Branch labels missing**: Ensure VTK file contains multiple line segments for branches

**Performance**:
- For large datasets, start with lower resolution during adjustment
- Increase resolution for final visualization
- Multiple stents may require more processing time

## Development

### File Structure
```
EVARSim/
├── EVARSim.py              # Main module implementation
├── Resources/
│   ├── UI/EVARSim.ui      # User interface definition
│   └── Icons/EVARSim.png  # Module icon
└── CL_model.vtk           # Sample centerline data
```

### Key Methods
- `_reduceCenterlinePoints()`: Strategic point reduction
- `_applySplineSmoothing()`: Spline interpolation
- `_createTubeAlongCurve()`: Stent geometry generation

## License

See License.txt. This extension is developed for medical research and educational purposes. Please ensure compliance with your institution's software usage policies.

## Contributing

Contributions welcome! Please ensure all changes maintain compatibility with 3D Slicer's scripted loadable module framework.

## Citation

If you use EVARSim in your research, please cite appropriately and acknowledge the 3D Slicer platform.

---

**Version**: 1.0  
**3D Slicer Compatibility**: 5.0+  
**Last Updated**: 2024
