import sys
import math

# Import the model from the existing script
# This will run the analysis, but that's acceptable
try:
    from crane_pynite import model, pipe_od
except ImportError:
    # Fallback if run from a different context, though we expect to run in the same dir
    sys.path.append('.')
    from crane_pynite import model, pipe_od

def generate_scad(model, filename="crane_model.scad"):
    with open(filename, 'w') as f:
        f.write("// Generated from crane_pynite.py\n")
        f.write(f"pipe_od = {pipe_od};\n")
        f.write("$fn = 32;\n\n")
        
        # Helper module for pipes (using user's logic)
        f.write("""
function vadd(a,b) = [a[0]+b[0], a[1]+b[1], a[2]+b[2]];
function vsub(a,b) = [a[0]-b[0], a[1]-b[1], a[2]-b[2]];
function vlen(v)   = sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);

module pipe_segment(p1, p2, od=pipe_od) {
    v   = vsub(p2, p1);
    len = vlen(v);

    if (len > 0) {
        axis  = [-v[1], v[0], 0]; 
        angle = acos(v[2]/len);

        r = od/2;

        translate(p1)
            rotate(a = angle, v = axis)
                cylinder(h = len, r = r);
    }
}

// Model Geometry
""")
        
        f.write("union() {\n")
        
        for m_name, member in model.members.items():
            # Get node coordinates
            ni = member.i_node
            nj = member.j_node
            
            p1 = f"[{ni.X}, {ni.Y}, {ni.Z}]"
            p2 = f"[{nj.X}, {nj.Y}, {nj.Z}]"
            
            f.write(f"    // Member: {m_name}\n")
            f.write(f"    pipe_segment({p1}, {p2});\n")
            
        f.write("}\n")

if __name__ == "__main__":
    generate_scad(model)
    print("OpenSCAD file generated: crane_model.scad")
