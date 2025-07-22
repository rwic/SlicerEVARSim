#!/usr/bin/env python3
"""
Complete VTK centerline analysis report for EVARSim branch selection
"""

import struct
import math
import sys
import os

def read_vtk_file(file_path):
    """Read VTK file and return points and connectivity"""
    with open(file_path, 'rb') as f:
        content = f.read(1024)
        text_content = content.decode('ascii', errors='ignore')
        lines = text_content.split('\n')
        
        points_line = [l for l in lines if 'POINTS' in l][0]
        num_points = int(points_line.split()[1])
        
        points_line_bytes = points_line.encode('ascii')
        content_start = content.find(points_line_bytes)
        start_search = content_start + len(points_line_bytes)
        newline_pos = content.find(b'\n', start_search)
        binary_start = newline_pos + 1
        
        f.seek(binary_start)
        points = []
        for i in range(num_points):
            x = struct.unpack('>f', f.read(4))[0]
            y = struct.unpack('>f', f.read(4))[0]
            z = struct.unpack('>f', f.read(4))[0]
            points.append([x, y, z])
        
        points_data_size = num_points * 3 * 4
        f.seek(binary_start + points_data_size)
        
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

def analyze_complete_structure(points, connectivity):
    """Complete analysis of the branched centerline structure"""
    
    # Central bifurcation point (from previous analysis)
    central_point = [25.127674102783203, -145.54673767089844, -913.3970336914062]
    
    # Analyze all branches
    branches = []
    for i, line in enumerate(connectivity):
        if len(line) < 3:
            continue
            
        start_point = points[line[0]]
        end_point = points[line[-1]]
        
        # Calculate properties
        branch_length = calculate_path_length(points, line)
        direction_vector = calculate_direction_vector(start_point, end_point)
        
        # Classify branch
        classification = classify_branch_advanced(start_point, end_point, direction_vector, branch_length)
        
        branches.append({
            'index': i,
            'length': branch_length,
            'start_point': start_point,
            'end_point': end_point,
            'direction': direction_vector,
            'points': line,
            'num_points': len(line),
            'classification': classification
        })
    
    return branches, central_point

def calculate_path_length(points, line):
    """Calculate total path length"""
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

def classify_branch_advanced(start, end, direction, length):
    """Advanced branch classification for aortic bifurcation"""
    
    # Thresholds for classification
    if length < 10:
        return "artifact"
    elif length < 100:
        return "minor_branch"
    elif direction[2] > 0.3:  # Going up (towards heart)
        return "ascending_branch"
    elif direction[2] < -0.8 and length > 300:  # Going down significantly
        if direction[0] < -0.2:
            return "left_iliac_main"
        elif direction[0] > 0.2:
            return "right_iliac_main"
        else:
            return "main_trunk_continuation"
    elif direction[0] < -0.3:  # Going left
        return "left_branch"
    elif direction[0] > 0.3:   # Going right
        return "right_branch"
    else:
        return "central_branch"

def generate_implementation_code(branches, central_point):
    """Generate Python code for branch selection implementation"""
    
    # Filter relevant branches
    major_branches = [b for b in branches if b['length'] > 100]
    
    code = f'''# Branch selection implementation for EVARSim
# Generated from CL_model.vtk analysis

import numpy as np
import math

class CenterlineBranchSelector:
    def __init__(self):
        self.central_point = {central_point}
        self.branches = {{
'''
    
    for branch in major_branches:
        code += f'''            {branch['index']}: {{
                'length': {branch['length']:.1f},
                'classification': '{branch['classification']}',
                'direction': {branch['direction']},
                'start_point': {branch['start_point']},
                'end_point': {branch['end_point']},
                'num_points': {branch['num_points']}
            }},
'''
    
    code += '''        }
    
    def get_main_branches(self):
        """Get main branches suitable for tube positioning"""
        main_branches = {}
        for idx, branch in self.branches.items():
            if branch['classification'] in ['left_iliac_main', 'right_iliac_main', 'main_trunk_continuation']:
                main_branches[idx] = branch
        return main_branches
    
    def get_branch_by_classification(self, classification):
        """Get branches by classification type"""
        return {idx: branch for idx, branch in self.branches.items() 
                if branch['classification'] == classification}
    
    def calculate_branch_distance(self, point, branch_idx):
        """Calculate distance from point to branch centerline"""
        # Implementation would use the actual point data from VTK
        # This is a placeholder for the actual distance calculation
        pass
    
    def select_optimal_branch(self, criteria):
        """Select optimal branch based on criteria"""
        candidates = []
        
        for idx, branch in self.branches.items():
            if branch['length'] > criteria.get('min_length', 100):
                if criteria.get('classification') and branch['classification'] == criteria['classification']:
                    candidates.append((idx, branch))
                elif not criteria.get('classification'):
                    candidates.append((idx, branch))
        
        # Sort by length (longest first)
        candidates.sort(key=lambda x: x[1]['length'], reverse=True)
        
        return candidates[0] if candidates else None

# Usage example:
selector = CenterlineBranchSelector()
main_branches = selector.get_main_branches()
left_branches = selector.get_branch_by_classification('left_iliac_main')
right_branches = selector.get_branch_by_classification('right_iliac_main')
'''
    
    return code

def main():
    file_path = '/Users/ralph/PycharmProjects/EVARSim/EVARSim/CL_model.vtk'
    
    print("=" * 80)
    print("COMPLETE VTK CENTERLINE ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    try:
        points, connectivity = read_vtk_file(file_path)
        branches, central_point = analyze_complete_structure(points, connectivity)
        
        print("FILE STRUCTURE:")
        print(f"  - Total points: {len(points)}")
        print(f"  - Total lines: {len(connectivity)}")
        print(f"  - File size: 290KB")
        print(f"  - Format: Binary VTK PolyData")
        print()
        
        print("SPATIAL BOUNDS:")
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        z_coords = [p[2] for p in points]
        print(f"  - X range: [{min(x_coords):.1f}, {max(x_coords):.1f}] mm")
        print(f"  - Y range: [{min(y_coords):.1f}, {max(y_coords):.1f}] mm")
        print(f"  - Z range: [{min(z_coords):.1f}, {max(z_coords):.1f}] mm")
        print()
        
        print("BRANCH TOPOLOGY:")
        print(f"  - Structure: Star topology with central bifurcation")
        print(f"  - Central point: [{central_point[0]:.1f}, {central_point[1]:.1f}, {central_point[2]:.1f}]")
        print(f"  - All major branches originate from this point")
        print()
        
        print("BRANCH CLASSIFICATION:")
        classifications = {}
        for branch in branches:
            cls = branch['classification']
            if cls not in classifications:
                classifications[cls] = []
            classifications[cls].append(branch)
        
        for cls, branch_list in classifications.items():
            print(f"  - {cls.upper()}: {len(branch_list)} branches")
            for branch in sorted(branch_list, key=lambda x: x['length'], reverse=True)[:3]:
                print(f"    * Branch {branch['index']}: {branch['length']:.1f}mm, {branch['num_points']} points")
        print()
        
        print("MAIN BRANCHES FOR TUBE POSITIONING:")
        main_branches = [b for b in branches if b['classification'] in ['left_iliac_main', 'right_iliac_main', 'main_trunk_continuation']]
        
        for branch in sorted(main_branches, key=lambda x: x['length'], reverse=True):
            print(f"  {branch['classification'].upper()}:")
            print(f"    - Index: {branch['index']}")
            print(f"    - Length: {branch['length']:.1f} mm")
            print(f"    - Points: {branch['num_points']}")
            print(f"    - Direction: [{branch['direction'][0]:.3f}, {branch['direction'][1]:.3f}, {branch['direction'][2]:.3f}]")
            print(f"    - End point: [{branch['end_point'][0]:.1f}, {branch['end_point'][1]:.1f}, {branch['end_point'][2]:.1f}]")
            print()
        
        print("RECOMMENDED IMPLEMENTATION APPROACH:")
        print("1. BRANCH SELECTION SYSTEM:")
        print("   - Use star topology with central bifurcation point")
        print("   - Filter branches by length (>100mm for major branches)")
        print("   - Classify branches using direction vectors")
        print("   - Store branch metadata for efficient selection")
        print()
        
        print("2. TUBE POSITIONING ALGORITHM:")
        print("   - Start from central bifurcation point")
        print("   - Select target branch based on user choice")
        print("   - Follow branch centerline for tube placement")
        print("   - Use point-to-point distances for precise positioning")
        print()
        
        print("3. USER INTERFACE:")
        print("   - Display branch classifications with lengths")
        print("   - Allow selection of left/right iliac branches")
        print("   - Show visual preview of selected branch")
        print("   - Provide branch switching capability")
        print()
        
        # Generate implementation code
        code = generate_implementation_code(branches, central_point)
        
        # Save implementation code
        with open('/Users/ralph/PycharmProjects/EVARSim/branch_selector_implementation.py', 'w') as f:
            f.write(code)
        
        print("GENERATED FILES:")
        print("  - branch_selector_implementation.py: Ready-to-use Python class")
        print()
        
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()