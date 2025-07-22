#!/usr/bin/env python3
"""
Script to analyze the VTK file structure and understand the branching topology.
"""

import vtk
import numpy as np

def analyze_vtk_file(filename):
    """Analyze the VTK file structure to understand branching."""
    print(f"Analyzing VTK file: {filename}")
    
    # Read the VTK file
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    
    polydata = reader.GetOutput()
    
    # Get basic information
    num_points = polydata.GetNumberOfPoints()
    num_lines = polydata.GetNumberOfLines()
    num_cells = polydata.GetNumberOfCells()
    
    print(f"Number of points: {num_points}")
    print(f"Number of lines: {num_lines}")
    print(f"Number of cells: {num_cells}")
    
    # Analyze connectivity
    lines = polydata.GetLines()
    lines.InitTraversal()
    
    # Store all line segments
    line_segments = []
    point_connectivity = {}  # point_id -> list of connected points
    
    # Initialize connectivity dictionary
    for i in range(num_points):
        point_connectivity[i] = []
    
    # Process each line
    line_id = 0
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
        
        # Update connectivity
        for k in range(len(line_points) - 1):
            p1, p2 = line_points[k], line_points[k + 1]
            if p2 not in point_connectivity[p1]:
                point_connectivity[p1].append(p2)
            if p1 not in point_connectivity[p2]:
                point_connectivity[p2].append(p1)
        
        line_id += 1
    
    print(f"Number of line segments: {len(line_segments)}")
    
    # Find branch points (points with more than 2 connections)
    branch_points = []
    endpoint_points = []
    
    for point_id, connections in point_connectivity.items():
        if len(connections) > 2:
            branch_points.append(point_id)
        elif len(connections) == 1:
            endpoint_points.append(point_id)
    
    print(f"Number of branch points: {len(branch_points)}")
    print(f"Number of endpoints: {len(endpoint_points)}")
    
    if branch_points:
        print("Branch points:")
        for bp in branch_points:
            coords = polydata.GetPoint(bp)
            print(f"  Point {bp}: {coords}, connections: {len(point_connectivity[bp])}")
    
    if endpoint_points:
        print("Endpoints:")
        for ep in endpoint_points:
            coords = polydata.GetPoint(ep)
            print(f"  Point {ep}: {coords}")
    
    # Analyze the structure - try to identify branches
    print("\nAnalyzing branch structure...")
    
    # For each branch point, trace the branches
    branches = []
    if branch_points:
        for bp in branch_points:
            print(f"\nBranch point {bp} analysis:")
            connected_points = point_connectivity[bp]
            
            # For each connection from the branch point, trace the path
            for connection in connected_points:
                branch_path = trace_branch_path(bp, connection, point_connectivity, endpoint_points)
                if branch_path:
                    branches.append(branch_path)
                    print(f"  Branch to point {connection}: {len(branch_path)} points")
    
    print(f"\nTotal branches identified: {len(branches)}")
    
    # Analyze line segments to understand the overall structure
    print("\nLine segment analysis:")
    for i, segment in enumerate(line_segments):
        print(f"  Segment {i}: {len(segment)} points (from {segment[0]} to {segment[-1]})")
        
        # Check if this segment contains branch points
        segment_branch_points = [p for p in segment if p in branch_points]
        if segment_branch_points:
            print(f"    Contains branch points: {segment_branch_points}")
    
    return {
        'num_points': num_points,
        'num_lines': num_lines,
        'branch_points': branch_points,
        'endpoint_points': endpoint_points,
        'line_segments': line_segments,
        'branches': branches,
        'point_connectivity': point_connectivity
    }

def trace_branch_path(start_point, next_point, connectivity, endpoints):
    """Trace a branch path from start_point through next_point until endpoint."""
    path = [start_point, next_point]
    current = next_point
    
    # Follow the path until we reach an endpoint or another branch point
    while current not in endpoints:
        connections = connectivity[current]
        # Remove the point we came from
        next_candidates = [p for p in connections if p != path[-2]]
        
        if len(next_candidates) == 1:
            # Continue along the path
            current = next_candidates[0]
            path.append(current)
        elif len(next_candidates) > 1:
            # Hit another branch point - stop here
            break
        else:
            # Dead end
            break
    
    return path

if __name__ == "__main__":
    vtk_file = "/Users/ralph/PycharmProjects/EVARSim/EVARSim/CL_model.vtk"
    analysis = analyze_vtk_file(vtk_file)