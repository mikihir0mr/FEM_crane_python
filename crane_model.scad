// Generated from crane_pynite.py
pipe_od = 48.6;
$fn = 32;


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
union() {
    // Member: M_base_FL_FR
    pipe_segment([-450.0, -300.0, 24.3], [450.0, -300.0, 24.3]);
    // Member: M_base_FR_RR
    pipe_segment([450.0, -300.0, 24.3], [450.0, 300.0, 24.3]);
    // Member: M_base_RR_RL
    pipe_segment([450.0, 300.0, 24.3], [-450.0, 300.0, 24.3]);
    // Member: M_base_RL_FL
    pipe_segment([-450.0, 300.0, 24.3], [-450.0, -300.0, 24.3]);
    // Member: M_base_Fmid_Rmid
    pipe_segment([0.0, -300.0, 24.3], [0.0, 300.0, 24.3]);
    // Member: M_base_Lmid_RmidX0
    pipe_segment([-450.0, 0.0, 24.3], [450.0, 0.0, 24.3]);
    // Member: M_mast_1
    pipe_segment([-450.0, 0.0, 24.3], [-450.0, 0.0, 824.3]);
    // Member: M_mast_2
    pipe_segment([-450.0, 0.0, 824.3], [-450.0, 0.0, 1024.3]);
    // Member: M_mast_3
    pipe_segment([-450.0, 0.0, 1024.3], [-450.0, 0.0, 1824.3]);
    // Member: M_tripod_FL
    pipe_segment([-450.0, 0.0, 1024.3], [-450.0, -300.0, 24.3]);
    // Member: M_tripod_RL
    pipe_segment([-450.0, 0.0, 1024.3], [-450.0, 300.0, 24.3]);
    // Member: M_arm
    pipe_segment([-450.0, 0.0, 1824.3], [-1450.0, 1.2246467991473532e-13, 1824.3]);
    // Member: M_brace
    pipe_segment([-450.0, 0.0, 824.3], [-950.0, 6.123233995736766e-14, 1824.3]);
}
