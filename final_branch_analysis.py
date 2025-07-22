#!/usr/bin/env python3
"""
Final analysis to identify the true branch structure.
"""

import vtk
import numpy as np
from collections import defaultdict

def final_branch_analysis(filename):
    """Final analysis to identify the true branch structure."""
    print(f"Analyzing VTK file: {filename}")
    
    # Read the VTK file
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    
    polydata = reader.GetOutput()
    
    # Get line segments
    lines = polydata.GetLines()
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
        
        line_segments.append(line_points)
        all_points.extend(line_points)
    
    # Find the most frequently used point - this is likely the branch point
    point_counts = defaultdict(int)
    for point_id in all_points:
        point_counts[point_id] += 1
    
    # Sort by frequency
    sorted_points = sorted(point_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nMost frequently used points:")
    for i, (point_id, count) in enumerate(sorted_points[:5]):
        coords = polydata.GetPoint(point_id)
        print(f"  {i+1}. Point {point_id}: used {count} times, coords: {coords}")
    
    # The most frequent point should be the branch point
    branch_point_id = sorted_points[0][0]
    branch_point_coords = polydata.GetPoint(branch_point_id)
    
    print(f"\nIdentified branch point: {branch_point_id} at {branch_point_coords}")
    
    # Classify segments based on their relationship to the branch point
    main_trunk = []
    branches = []
    other_segments = []
    
    for i, segment in enumerate(line_segments):
        if branch_point_id in segment:
            if segment[0] == branch_point_id:
                # Segment starts at branch point - this is a branch
                branches.append({
                    'segment_id': i,
                    'points': segment,
                    'direction': 'from_branch',
                    'length': len(segment),
                    'start_coords': polydata.GetPoint(segment[0]),
                    'end_coords': polydata.GetPoint(segment[-1])
                })
            elif segment[-1] == branch_point_id:
                # Segment ends at branch point - this is the main trunk
                main_trunk.append({
                    'segment_id': i,
                    'points': segment,
                    'direction': 'to_branch',
                    'length': len(segment),
                    'start_coords': polydata.GetPoint(segment[0]),
                    'end_coords': polydata.GetPoint(segment[-1])
                })
            else:
                # Branch point is in the middle - unusual case
                other_segments.append({
                    'segment_id': i,
                    'points': segment,
                    'direction': 'contains_branch',
                    'length': len(segment),
                    'start_coords': polydata.GetPoint(segment[0]),
                    'end_coords': polydata.GetPoint(segment[-1])
                })
        else:
            other_segments.append({
                'segment_id': i,
                'points': segment,
                'direction': 'disconnected',
                'length': len(segment),
                'start_coords': polydata.GetPoint(segment[0]),
                'end_coords': polydata.GetPoint(segment[-1])
            })
    
    print(f"\nMain trunk segments (ending at branch): {len(main_trunk)}")
    for trunk in main_trunk:
        print(f"  Segment {trunk['segment_id']}: {trunk['length']} points")
        print(f"    From: {trunk['start_coords']}")
        print(f"    To: {trunk['end_coords']}")
    
    print(f"\nBranch segments (starting from branch): {len(branches)}")
    for i, branch in enumerate(branches):
        print(f"  Branch {i+1} (Segment {branch['segment_id']}): {branch['length']} points")
        print(f"    From: {branch['start_coords']}")
        print(f"    To: {branch['end_coords']}")
    
    print(f"\nOther segments: {len(other_segments)}")
    for seg in other_segments:
        print(f"  Segment {seg['segment_id']} ({seg['direction']}): {seg['length']} points")
        print(f"    From: {seg['start_coords']}")
        print(f"    To: {seg['end_coords']}")
    
    # Determine the structure
    print(f"\nStructure Analysis:")
    print(f"- Branch point: {branch_point_coords}")
    print(f"- Main trunk segments: {len(main_trunk)}")
    print(f"- Branch segments: {len(branches)}")
    print(f"- Total segments: {len(line_segments)}")
    
    # Create a simplified representation
    centerline_branches = {
        'branch_point': {
            'id': branch_point_id,
            'coords': branch_point_coords
        },
        'main_trunk': main_trunk,
        'branches': branches,
        'other_segments': other_segments
    }
    
    return centerline_branches

if __name__ == "__main__":
    vtk_file = "/Users/ralph/PycharmProjects/EVARSim/EVARSim/CL_model.vtk"
    analysis = final_branch_analysis(vtk_file)