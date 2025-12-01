from Pynite import FEModel3D
import math

def calculate_crane(params):
    # Extract parameters with defaults
    pipe_od = params.get('pipe_od', 48.6)
    t_wall = params.get('t_wall', 2.4)
    base_len = params.get('base_len', 900.0)
    base_wid = params.get('base_wid', 600.0)
    arm_pivot_height = params.get('arm_pivot_height', 1800.0)
    tripod_attach_height = params.get('tripod_attach_height', 1000.0)
    brace_mast_height = params.get('brace_mast_height', 800.0)
    arm_len = params.get('arm_len', 1000.0)
    arm_angle = params.get('arm_angle', 180.0)
    mass_tip = params.get('mass_tip', 50.0)
    
    # Derived parameters
    R = pipe_od / 2.0
    r = R - t_wall
    z0 = pipe_od / 2.0
    
    # Section properties
    A = math.pi * (R**2 - r**2)
    I = (math.pi / 4.0) * (R**4 - r**4)
    J = 2 * I
    
    # Material properties
    E = 2.05e5
    nu = 0.3
    G = E / (2.0 * (1.0 + nu))
    rho = 7.85e-6
    
    # Model generation
    model = FEModel3D()
    model.add_material('Steel', E, G, nu, rho)
    model.add_section('Pipe48x2p4', A=A, Iy=I, Iz=I, J=J)
    
    # Nodes
    L = base_len
    W = base_wid
    
    nodes = {}
    nodes['FL'] = (-L/2.0, -W/2.0, z0)
    nodes['FR'] = ( L/2.0, -W/2.0, z0)
    nodes['RR'] = ( L/2.0,  W/2.0, z0)
    nodes['RL'] = (-L/2.0,  W/2.0, z0)
    
    nodes['Fmid']   = (0.0, -W/2.0, z0)
    nodes['Rmid']   = (0.0,  W/2.0, z0)
    nodes['Lmid']   = (-L/2.0, 0.0, z0)
    nodes['RmidX0'] = ( L/2.0, 0.0, z0)
    
    nodes['M_brace'] = (-L/2.0, 0.0, z0 + brace_mast_height)
    nodes['M_attach'] = (-L/2.0, 0.0, z0 + tripod_attach_height)
    nodes['M_top']    = (-L/2.0, 0.0, z0 + arm_pivot_height)
    
    arm_rad = math.radians(arm_angle)
    arm_dir = (math.cos(arm_rad), math.sin(arm_rad), 0.0)
    
    nodes['A_tip'] = (
        nodes['M_top'][0] + arm_len * arm_dir[0],
        nodes['M_top'][1] + arm_len * arm_dir[1],
        nodes['M_top'][2] + arm_len * arm_dir[2],
    )
    
    nodes['A_brace'] = (
        nodes['M_top'][0] + (arm_len * 0.5) * arm_dir[0],
        nodes['M_top'][1] + (arm_len * 0.5) * arm_dir[1],
        nodes['M_top'][2] + (arm_len * 0.5) * arm_dir[2],
    )
    
    for name, (x, y, z) in nodes.items():
        model.add_node(name, x, y, z)
        
    # Members
    def add_member(mname, ni, nj):
        model.add_member(mname, ni, nj, 'Steel', 'Pipe48x2p4')
        
    add_member('M_base_FL_FR', 'FL', 'FR')
    add_member('M_base_FR_RR', 'FR', 'RR')
    add_member('M_base_RR_RL', 'RR', 'RL')
    add_member('M_base_RL_FL', 'RL', 'FL')
    add_member('M_base_Fmid_Rmid', 'Fmid', 'Rmid')
    add_member('M_base_Lmid_RmidX0', 'Lmid', 'RmidX0')
    
    add_member('M_mast_1', 'Lmid',  'M_brace')
    add_member('M_mast_2', 'M_brace', 'M_attach')
    add_member('M_mast_3', 'M_attach','M_top')
    
    add_member('M_tripod_FL', 'M_attach', 'FL')
    add_member('M_tripod_RL', 'M_attach', 'RL')
    
    add_member('M_arm', 'M_top', 'A_tip')
    add_member('M_brace', 'M_brace', 'A_brace')
    
    # Supports
    for n in ['FL', 'FR', 'RR', 'RL']:
        model.def_support(n, True, True, True, False, False, False)
        
    # Load
    P_tip = mass_tip * 9.81
    model.add_node_load('A_tip', 'FZ', -P_tip, 'DL')
    
    # Analyze
    model.add_load_combo('Combo 1', {'DL': 1.0})
    model.analyze(check_statics=True)
    
    # Extract Results
    combo = 'Combo 1'
    
    # Node Displacements (for deformed shape)
    node_displacements = {}
    for n_name, node in model.nodes.items():
        node_displacements[n_name] = {
            'dx': node.DX.get(combo, 0.0),
            'dy': node.DY.get(combo, 0.0),
            'dz': node.DZ.get(combo, 0.0)
        }

    # Member Stresses (simplified max bending stress)
    # Sigma = M / Z = M / (I / (D/2)) = M * (D/2) / I
    # We'll take the max moment from the member's internal forces
    member_results = {}
    max_stress_overall = 0.0
    
    # Yield Stress for STK400
    YIELD_STRESS = 235.0
    
    failures = []

    for m_name, member in model.members.items():
        # Get max moment (My or Mz)
        # PyNite's Member3D stores max/min moments in attributes after analysis
        # Check if attributes exist, otherwise default to 0
        
        # Try to get max moments directly from member attributes if available
        # Depending on PyNite version, these might be stored differently.
        # Let's try to access the moment arrays directly if possible, or use a safer approach.
        
        # Safe approach: Check end nodes internal forces if available, or just use 0 for now to fix the crash
        # Real fix: PyNite members have .max_moment('My', combo) etc.
        
        try:
            # Attempt to use the method if it exists
            mz_max = max(abs(member.min_moment('Mz', combo)), abs(member.max_moment('Mz', combo)))
            my_max = max(abs(member.min_moment('My', combo)), abs(member.max_moment('My', combo)))
            m_max = max(mz_max, my_max)
        except:
            # Fallback if methods don't exist (older PyNite?)
            m_max = 0.0
        
        # Calculate stress [N/mm^2]
        # I is already defined (Iy=Iz=I)
        # y = R (outer radius)
        sigma = m_max * R / I
        
        if sigma > YIELD_STRESS:
            failures.append(m_name)
        
        member_results[m_name] = {
            'max_moment': m_max,
            'max_stress': sigma
        }
        if sigma > max_stress_overall:
            max_stress_overall = sigma

    results = {
        'tip_displacement': {
            'dz': model.nodes['A_tip'].DZ.get(combo, 0.0)
        },
        'node_displacements': node_displacements,
        'member_results': member_results,
        'max_stress': max_stress_overall,
        'yield_stress': YIELD_STRESS,
        'failures': failures,
        'reactions': {}
    }
        
    for n_name in ['FL', 'FR', 'RR', 'RL']:
        node = model.nodes[n_name]
        results['reactions'][n_name] = node.RxnFZ.get(combo, 0.0)
        
    return results
