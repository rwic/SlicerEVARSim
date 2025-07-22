# Branch selection implementation for EVARSim
# Generated from CL_model.vtk analysis

import numpy as np
import math

class CenterlineBranchSelector:
    def __init__(self):
        self.central_point = [25.127674102783203, -145.54673767089844, -913.3970336914062]
        self.branches = {
            1: {
                'length': 536.0,
                'classification': 'left_iliac_main',
                'direction': [-0.26077170746463846, -0.12913838534065655, -0.9567243040801174],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-84.64893341064453, -199.90989685058594, -1316.1475830078125],
                'num_points': 710
            },
            2: {
                'length': 341.9,
                'classification': 'main_trunk_continuation',
                'direction': [-0.19144379514171803, -0.006683173096931042, -0.9814808243155301],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-28.695241928100586, -147.4256591796875, -1189.3326416015625],
                'num_points': 308
            },
            3: {
                'length': 371.1,
                'classification': 'main_trunk_continuation',
                'direction': [-0.17498416479910536, 0.05115150507829313, -0.98324161099792],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-24.285158157348633, -131.1023406982422, -1191.04931640625],
                'num_points': 376
            },
            4: {
                'length': 390.9,
                'classification': 'main_trunk_continuation',
                'direction': [0.0676361494955677, 0.010550236735708339, -0.9976542706700723],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [46.338134765625, -142.23822021484375, -1226.2579345703125],
                'num_points': 406
            },
            5: {
                'length': 185.5,
                'classification': 'left_branch',
                'direction': [-0.33018504163555795, -0.10947125347074886, -0.9375467364050007],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-25.720157623291016, -162.40509033203125, -1057.77734375],
                'num_points': 277
            },
            7: {
                'length': 396.0,
                'classification': 'main_trunk_continuation',
                'direction': [0.07045390449263231, 0.0187457492680779, -0.9973388813367908],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [47.48155975341797, -139.59901428222656, -1229.8365478515625],
                'num_points': 418
            },
            9: {
                'length': 545.2,
                'classification': 'left_iliac_main',
                'direction': [-0.2594307183886218, -0.12117376148075291, -0.9581297521134439],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-86.2173843383789, -197.5532989501953, -1324.61669921875],
                'num_points': 730
            },
            10: {
                'length': 549.9,
                'classification': 'left_iliac_main',
                'direction': [-0.2576407326892185, -0.1186370909735771, -0.9589298689188328],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-86.39241790771484, -196.89894104003906, -1328.470947265625],
                'num_points': 743
            },
            11: {
                'length': 543.6,
                'classification': 'left_iliac_main',
                'direction': [-0.25657934324045956, -0.1246492706932172, -0.958451668023977],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-84.65068054199219, -198.87835693359375, -1323.473876953125],
                'num_points': 729
            },
            12: {
                'length': 553.4,
                'classification': 'left_iliac_main',
                'direction': [-0.2569024214837605, -0.11884867799111226, -0.9591017347370118],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-86.96598815917969, -197.40371704101562, -1331.8797607421875],
                'num_points': 751
            },
            13: {
                'length': 551.2,
                'classification': 'left_iliac_main',
                'direction': [-0.2577242537195839, -0.11716336310114828, -0.9590886066425313],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [-86.7281265258789, -196.397216796875, -1329.6544189453125],
                'num_points': 747
            },
            14: {
                'length': 138.3,
                'classification': 'central_branch',
                'direction': [-0.12593124295749739, -0.48839240724503963, -0.8634895358906065],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [9.581195831298828, -205.83981323242188, -1019.9966430664062],
                'num_points': 154
            },
            15: {
                'length': 142.6,
                'classification': 'central_branch',
                'direction': [-0.1848751207867353, -0.46798020368540183, -0.8641850025733262],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [2.1614291667938232, -203.68191528320312, -1020.7510375976562],
                'num_points': 175
            },
            16: {
                'length': 196.3,
                'classification': 'central_branch',
                'direction': [0.22997463115102848, -0.15859561587269586, -0.9601870128536987],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [61.725948333740234, -170.7857208251953, -1066.20166015625],
                'num_points': 268
            },
            17: {
                'length': 404.0,
                'classification': 'main_trunk_continuation',
                'direction': [0.08151028511758848, 0.044402623813114016, -0.9956829216264385],
                'start_point': [25.127674102783203, -145.54673767089844, -913.3970336914062],
                'end_point': [49.89164733886719, -132.0565948486328, -1215.8995361328125],
                'num_points': 437
            },
        }
    
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
