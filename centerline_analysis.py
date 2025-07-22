#!/usr/bin/env python3
"""
Detailed centerline analysis for branch selection in EVARSim
"""

import struct
import math
import sys
import os

def read_vtk_file(file_path):
    """Read VTK file and return points and connectivity"""
    with open(file_path, 'rb') as f:
        # Read header
        content = f.read(1024)
        text_content = content.decode('ascii', errors='ignore')
        lines = text_content.split('\n')
        
        points_line = [l for l in lines if 'POINTS' in l][0]
        num_points = int(points_line.split()[1])
        
        # Find binary data start
        points_line_bytes = points_line.encode('ascii')
        content_start = content.find(points_line_bytes)
        start_search = content_start + len(points_line_bytes)
        newline_pos = content.find(b'\n', start_search)
        binary_start = newline_pos + 1
        
        # Read points
        f.seek(binary_start)
        points = []
        for i in range(num_points):
            x = struct.unpack('>f', f.read(4))[0]
            y = struct.unpack('>f', f.read(4))[0]
            z = struct.unpack('>f', f.read(4))[0]
            points.append([x, y, z])
        
        # Read connectivity - skip to after points data
        points_data_size = num_points * 3 * 4  # 3 floats per point, 4 bytes per float
        f.seek(binary_start + points_data_size)
        
        # Find LINES keyword
        while True:
            char = f.read(1)
            if not char:
                break
            if char == b'L':
                f.seek(f.tell() - 1)
                break
        
        line = f.readline().decode('ascii', errors='ignore').strip()
        parts = line.split()
        num_lines = int(parts[1])
        
        connectivity = []
        for i in range(num_lines):
            n_points = struct.unpack('>I', f.read(4))[0]
            indices = []
            for j in range(n_points):
                idx = struct.unpack('>I', f.read(4))[0]
                indices.append(idx)
            connectivity.append(indices)
        
        return points, connectivity

def analyze_centerline_structure(points, connectivity):
    """Analyze the centerline structure for branch selection"""
    
    # Find the central bifurcation point
    central_point = [25.127674102783203, -145.54673767089844, -913.3970336914062]
    
    # Classify branches
    branches = []
    main_trunk = None
    
    for i, line in enumerate(connectivity):
        if len(line) < 3:  # Skip very short segments
            continue
            
        start_point = points[line[0]]
        end_point = points[line[-1]]
        
        # Calculate branch properties
        branch_length = calculate_path_length(points, line)
        direction_vector = calculate_direction_vector(start_point, end_point)
        
        # Determine if this is main trunk or branch
        # Main trunk typically extends in the superior direction (positive Z)
        # and has significant length
        is_main_trunk = (direction_vector[2] > 0.5 and branch_length > 200)
        
        branch_info = {
            'index': i,
            'length': branch_length,
            'start_point': start_point,
            'end_point': end_point,
            'direction': direction_vector,
            'points': line,
            'is_main_trunk': is_main_trunk,
            'classification': classify_branch(start_point, end_point, direction_vector, branch_length)
        }
        
        branches.append(branch_info)
        
        if is_main_trunk:
            main_trunk = branch_info
    
    return branches, main_trunk, central_point

def calculate_path_length(points, line):
    """Calculate the total path length along a line"""
    total_length = 0
    for i in range(len(line) - 1):
        p1 = points[line[i]]
        p2 = points[line[i + 1]]
        dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)
        total_length += dist
    return total_length

def calculate_direction_vector(start, end):
    """Calculate normalized direction vector"""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    
    length = math.sqrt(dx**2 + dy**2 + dz**2)
    if length == 0:
        return [0, 0, 0]
    
    return [dx/length, dy/length, dz/length]

def classify_branch(start, end, direction, length):
    """Classify branch based on anatomical expectations"""
    
    # For aortic bifurcation (inverted Y):
    # - Main trunk: extends superiorly (positive Z)
    # - Left iliac: extends left and slightly posterior
    # - Right iliac: extends right and slightly posterior
    
    if direction[2] > 0.5 and length > 200:
        return "main_trunk"
    elif direction[0] < -0.3 and direction[2] < 0:  # Left and down
        return "left_iliac"
    elif direction[0] > 0.3 and direction[2] < 0:   # Right and down
        return "right_iliac"
    elif length > 100:
        return "major_branch"
    else:
        return "minor_branch"

def generate_branch_selection_recommendations(branches, main_trunk, central_point):
    """Generate recommendations for branch selection implementation"""
    
    print("=== BRANCH SELECTION RECOMMENDATIONS ===")
    print()
    
    # Sort branches by length (longest first)
    sorted_branches = sorted(branches, key=lambda x: x['length'], reverse=True)
    
    print("1. BRANCH CLASSIFICATION:")
    for i, branch in enumerate(sorted_branches[:10]):  # Show top 10
        print(f"   Branch {branch['index']}: {branch['classification']}")
        print(f"     Length: {branch['length']:.1f} mm")
        print(f"     Direction: [{branch['direction'][0]:.3f}, {branch['direction'][1]:.3f}, {branch['direction'][2]:.3f}]")
        print(f"     End point: [{branch['end_point'][0]:.1f}, {branch['end_point'][1]:.1f}, {branch['end_point'][2]:.1f}]")
        print()
    
    print("2. IMPLEMENTATION APPROACH:")
    print("   a) Branch Selection Logic:")
    print("      - Use branch length as primary filter (>100mm for major branches)")
    print("      - Use direction vectors to identify left/right iliac branches")
    print("      - Implement spatial proximity checks for branch endpoints")
    print()
    
    print("   b) Suggested Branch Selection Algorithm:")
    print("      1. Find branches originating from central point")
    print("      2. Filter by minimum length threshold")
    print("      3. Classify using direction vectors:")
    print("         - Main trunk: direction_z > 0.5, length > 200mm")
    print("         - Left iliac: direction_x < -0.3, direction_z < 0")
    print("         - Right iliac: direction_x > 0.3, direction_z < 0")
    print("      4. Allow user selection from classified branches")
    print()
    
    print("   c) Data Structure for Branch Selection:")
    print("      - Store branch index, classification, length, direction")
    print("      - Maintain mapping from branch to point indices")
    print("      - Enable efficient spatial queries for tube positioning")
    print()
    
    # Find specific branches for tube positioning
    main_branches = [b for b in branches if b['classification'] in ['main_trunk', 'left_iliac', 'right_iliac']]
    
    print("3. MAIN BRANCHES FOR TUBE POSITIONING:")
    for branch in main_branches:
        print(f"   {branch['classification'].upper()}:")
        print(f"     Index: {branch['index']}")
        print(f"     Length: {branch['length']:.1f} mm")
        print(f"     Points: {len(branch['points'])}")
        print(f"     Start: [{branch['start_point'][0]:.1f}, {branch['start_point'][1]:.1f}, {branch['start_point'][2]:.1f}]")
        print(f"     End: [{branch['end_point'][0]:.1f}, {branch['end_point'][1]:.1f}, {branch['end_point'][2]:.1f}]")
        print()

def main():
    file_path = '/Users/ralph/PycharmProjects/EVARSim/EVARSim/CL_model.vtk'
    
    print("=== CENTERLINE ANALYSIS FOR BRANCH SELECTION ===")
    print()
    
    try:
        points, connectivity = read_vtk_file(file_path)
        branches, main_trunk, central_point = analyze_centerline_structure(points, connectivity)
        
        print(f"Total points: {len(points)}")
        print(f"Total lines: {len(connectivity)}")
        print(f"Analyzed branches: {len(branches)}")
        print(f"Central bifurcation point: [{central_point[0]:.1f}, {central_point[1]:.1f}, {central_point[2]:.1f}]")
        print()
        
        generate_branch_selection_recommendations(branches, main_trunk, central_point)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()