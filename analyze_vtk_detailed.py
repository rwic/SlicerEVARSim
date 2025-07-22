#!/usr/bin/env python3
"""
Detailed analysis of the VTK file structure.
"""

import vtk
import numpy as np
from collections import defaultdict

def analyze_vtk_detailed(filename):
    """Detailed analysis of the VTK file structure."""
    print(f"Analyzing VTK file: {filename}")
    
    # Read the VTK file
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    
    polydata = reader.GetOutput()
    
    # Get basic information
    num_points = polydata.GetNumberOfPoints()
    num_lines = polydata.GetNumberOfLines()
    
    print(f"Number of points: {num_points}")
    print(f"Number of lines: {num_lines}")
    
    # Analyze lines and find repeated endpoints
    lines = polydata.GetLines()
    lines.InitTraversal()
    
    line_segments = []
    all_endpoints = []
    
    # Process each line
    while True:
        idList = vtk.vtkIdList()
        if lines.GetNextCell(idList) == 0:
            break
            
        # Get the points in this line
        line_points = []
        for j in range(idList.GetNumberOfIds()):
            point_id = idList.GetId(j)
            line_points.append(point_id)
        
        line_segments.append(line_points)
        
        # Store endpoints
        if len(line_points) > 0:
            all_endpoints.extend([line_points[0], line_points[-1]])
    
    # Find the most common endpoint - this should be the branch point
    endpoint_counts = defaultdict(int)
    for ep in all_endpoints:
        endpoint_counts[ep] += 1
    
    print("\nEndpoint frequency analysis:")
    sorted_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)
    for point_id, count in sorted_endpoints[:10]:  # Show top 10
        coords = polydata.GetPoint(point_id)
        print(f"  Point {point_id}: used {count} times, coords: {coords}")
    
    # Find the branch point (most frequently used endpoint)
    branch_point_id = sorted_endpoints[0][0]
    branch_point_coords = polydata.GetPoint(branch_point_id)
    
    print(f"\nIdentified branch point: {branch_point_id} at {branch_point_coords}")
    print(f"This point is used in {sorted_endpoints[0][1]} line segments")
    
    # Classify segments based on their relationship to the branch point
    trunk_segments = []
    branch_segments = []
    
    for i, segment in enumerate(line_segments):
        if branch_point_id in segment:
            if segment[0] == branch_point_id:
                branch_segments.append((i, segment, "starts_at_branch"))
            elif segment[-1] == branch_point_id:
                branch_segments.append((i, segment, "ends_at_branch"))
            else:
                # Branch point is in the middle
                branch_segments.append((i, segment, "contains_branch"))
        else:
            trunk_segments.append((i, segment))
    
    print(f"\nSegments connected to branch point: {len(branch_segments)}")
    print(f"Segments not connected to branch point: {len(trunk_segments)}")
    
    # Analyze branch segments
    print("\nBranch segments analysis:")
    for i, (seg_idx, segment, relation) in enumerate(branch_segments):
        start_coords = polydata.GetPoint(segment[0])
        end_coords = polydata.GetPoint(segment[-1])
        print(f"  Branch {i}: Segment {seg_idx} ({relation})")
        print(f"    Length: {len(segment)} points")
        print(f"    Start: {start_coords}")
        print(f"    End: {end_coords}")
        print(f"    Points: {segment[0]} -> {segment[-1]}")
    
    # Try to identify main trunk vs branches based on segment lengths and positions
    print("\nTrunk segments analysis:")
    for i, (seg_idx, segment) in enumerate(trunk_segments):
        start_coords = polydata.GetPoint(segment[0])
        end_coords = polydata.GetPoint(segment[-1])
        print(f"  Trunk {i}: Segment {seg_idx}")
        print(f"    Length: {len(segment)} points")
        print(f"    Start: {start_coords}")
        print(f"    End: {end_coords}")
        print(f"    Points: {segment[0]} -> {segment[-1]}")
    
    # Group segments into potential branches
    print("\nPotential branch identification:")
    
    # Look for segments that share endpoints (other than the branch point)
    endpoint_to_segments = defaultdict(list)
    for i, segment in enumerate(line_segments):
        for endpoint in [segment[0], segment[-1]]:
            if endpoint != branch_point_id:  # Exclude the main branch point
                endpoint_to_segments[endpoint].append(i)
    
    # Find endpoints that are shared by multiple segments
    shared_endpoints = {ep: segments for ep, segments in endpoint_to_segments.items() 
                       if len(segments) > 1}
    
    print(f"Found {len(shared_endpoints)} shared endpoints (excluding main branch point):")
    for ep, segments in shared_endpoints.items():
        coords = polydata.GetPoint(ep)
        print(f"  Point {ep}: shared by segments {segments}, coords: {coords}")
    
    return {
        'branch_point_id': branch_point_id,
        'branch_point_coords': branch_point_coords,
        'branch_segments': branch_segments,
        'trunk_segments': trunk_segments,
        'line_segments': line_segments,
        'shared_endpoints': shared_endpoints
    }

if __name__ == "__main__":
    vtk_file = "/Users/ralph/PycharmProjects/EVARSim/EVARSim/CL_model.vtk"
    analysis = analyze_vtk_detailed(vtk_file)