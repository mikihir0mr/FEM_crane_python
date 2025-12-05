import { useState, Suspense, useMemo, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, Environment } from '@react-three/drei';
import { Box, Slider, Typography, Paper, Stack, CircularProgress, ToggleButton, ToggleButtonGroup, useMediaQuery, useTheme, IconButton, Select, MenuItem, FormControl, InputLabel, Button } from '@mui/material';
import { ExpandLess, ExpandMore } from '@mui/icons-material';
import axios from 'axios';
import * as THREE from 'three';

// Types
interface CraneParams {
  pipe_od: number;
  t_wall: number;
  base_len: number;
  base_wid: number;
  arm_pivot_height: number;
  tripod_attach_height: number;
  brace_mast_height: number;
  arm_len: number;
  arm_angle: number;
  mass_tip: number;
  yield_stress: number;
}

interface Results {
  tip_displacement: { dz: number };
  node_displacements: Record<string, { dx: number; dy: number; dz: number }>;
  member_results: Record<string, { max_moment: number; max_stress: number }>;
  max_stress: number;
  yield_stress: number;
  failures: string[];
  reactions: Record<string, number>;
}

// Helper to map value to color (Blue -> Green -> Red -> Magenta)
const getStressColor = (value: number) => {
  // Use fixed yield stress for normalization if available, otherwise max
  // But here 'max' argument in the component is passed as results.max_stress.
  // We want to use yield stress (235) as the reference for Red.

  const YIELD = 235.0;

  if (value > YIELD) {
    return new THREE.Color(1, 0, 1); // Magenta for failure
  }

  const t = Math.min(value / YIELD, 1.0);
  // 0=Blue (0.66), 0.5=Green (0.33), 1=Red (0.0)
  const color = new THREE.Color();
  color.setHSL((1.0 - t) * 0.66, 1.0, 0.5);
  return color;
};

// Geometry Helper
const PipeSegment = ({ p1, p2, od, color }: { p1: [number, number, number]; p2: [number, number, number]; od: number; color: THREE.Color | string }) => {
  const { position, quaternion, len } = useMemo(() => {
    const start = new THREE.Vector3(...p1);
    const end = new THREE.Vector3(...p2);
    const len = start.distanceTo(end);

    if (len === 0) return { position: new THREE.Vector3(), quaternion: new THREE.Quaternion(), len: 0 };

    const mid = start.clone().add(end).multiplyScalar(0.5);

    const obj = new THREE.Object3D();
    obj.position.copy(mid);
    obj.lookAt(end);
    obj.rotateX(Math.PI / 2);

    return { position: mid, quaternion: obj.quaternion, len };
  }, [p1, p2]);

  if (len === 0) return null;

  return (
    <mesh position={position} quaternion={quaternion}>
      <cylinderGeometry args={[od / 2, od / 2, len, 16]} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
};

// Crane Model Component
const CraneModel = ({ params, results, scale, viewMode }: { params: CraneParams; results: Results | null; scale: number; viewMode: 'geometry' | 'stress' }) => {
  const {
    pipe_od, base_len, base_wid, arm_pivot_height, tripod_attach_height, brace_mast_height, arm_len, arm_angle
  } = params;

  const z0 = pipe_od / 2;
  const L = base_len;
  const W = base_wid;

  // Base Nodes (Undeformed)
  const baseNodes: Record<string, [number, number, number]> = useMemo(() => {
    const nodes: Record<string, [number, number, number]> = {
      FL: [-L / 2, -W / 2, z0],
      FR: [L / 2, -W / 2, z0],
      RR: [L / 2, W / 2, z0],
      RL: [-L / 2, W / 2, z0],
      Fmid: [0, -W / 2, z0],
      Rmid: [0, W / 2, z0],
      Lmid: [-L / 2, 0, z0],
      RmidX0: [L / 2, 0, z0],
      M_brace: [-L / 2, 0, z0 + brace_mast_height],
      M_attach: [-L / 2, 0, z0 + tripod_attach_height],
      M_top: [-L / 2, 0, z0 + arm_pivot_height],
    };

    const arm_rad = (arm_angle * Math.PI) / 180;
    const arm_dir = [Math.cos(arm_rad), Math.sin(arm_rad), 0];

    nodes.A_tip = [
      nodes.M_top[0] + arm_len * arm_dir[0],
      nodes.M_top[1] + arm_len * arm_dir[1],
      nodes.M_top[2] + arm_len * arm_dir[2],
    ] as [number, number, number];

    nodes.A_brace = [
      nodes.M_top[0] + (arm_len * 0.5) * arm_dir[0],
      nodes.M_top[1] + (arm_len * 0.5) * arm_dir[1],
      nodes.M_top[2] + (arm_len * 0.5) * arm_dir[2],
    ] as [number, number, number];

    return nodes;
  }, [L, W, z0, brace_mast_height, tripod_attach_height, arm_pivot_height, arm_len, arm_angle]);

  // Calculate Deformed Nodes
  const nodes = useMemo(() => {
    if (!results || scale === 0) return baseNodes;

    const deformed: Record<string, [number, number, number]> = {};
    for (const [name, pos] of Object.entries(baseNodes)) {
      const disp = results.node_displacements[name];
      if (disp) {
        deformed[name] = [
          pos[0] + disp.dx * scale,
          pos[1] + disp.dy * scale,
          pos[2] + disp.dz * scale
        ];
      } else {
        deformed[name] = pos;
      }
    }
    return deformed;
  }, [baseNodes, results, scale]);

  // Members Definition
  const members = [
    ['M_base_FL_FR', 'FL', 'FR'], ['M_base_FR_RR', 'FR', 'RR'],
    ['M_base_RR_RL', 'RR', 'RL'], ['M_base_RL_FL', 'RL', 'FL'],
    ['M_base_Fmid_Rmid', 'Fmid', 'Rmid'], ['M_base_Lmid_RmidX0', 'Lmid', 'RmidX0'],
    ['M_mast_1', 'Lmid', 'M_brace'], ['M_mast_2', 'M_brace', 'M_attach'], ['M_mast_3', 'M_attach', 'M_top'],
    ['M_tripod_FL', 'M_attach', 'FL'], ['M_tripod_RL', 'M_attach', 'RL'],
    ['M_arm', 'M_top', 'A_tip'],
    ['M_brace', 'M_brace', 'A_brace'],
  ];

  return (
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {members.map(([id, n1, n2]) => {
        let color: THREE.Color | string = "#888";
        if (viewMode === 'stress' && results) {
          const res = results.member_results[id];
          if (res) {
            // Pass yield stress if needed, but getStressColor now uses constant 235
            color = getStressColor(res.max_stress);
          }
        }

        return <PipeSegment key={id} p1={nodes[n1]} p2={nodes[n2]} od={pipe_od} color={color} />;
      })}
    </group>
  );
};

export default function App() {
  const [params, setParams] = useState<CraneParams>({
    pipe_od: 48.6,
    t_wall: 2.4,
    base_len: 900.0,
    base_wid: 600.0,
    arm_pivot_height: 1800.0,
    tripod_attach_height: 1000.0,
    brace_mast_height: 800.0,
    arm_len: 1000.0,
    arm_angle: 180.0,
    mass_tip: 50.0,
    yield_stress: 235.0,
  });

  const [pipeType, setPipeType] = useState('STK400');

  const handlePipeChange = (event: any) => {
    const type = event.target.value;
    setPipeType(type);
    if (type === 'STK400') {
      setParams(prev => ({ ...prev, yield_stress: 235.0, t_wall: 2.4 }));
    } else if (type === 'STK500') {
      setParams(prev => ({ ...prev, yield_stress: 355.0, t_wall: 2.4 }));
    } else if (type === 'SuperLight700') {
      setParams(prev => ({ ...prev, yield_stress: 700.0, t_wall: 1.8 }));
    }
  };
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const [deformationScale, setDeformationScale] = useState(1);
  const [viewMode, setViewMode] = useState<'geometry' | 'stress'>('stress');

  // Mobile Responsive State
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleCalculate = async () => {
    setLoading(true);
    try {
      // Use relative path for deployment. 
      // The backend will serve the frontend, so /calculate will hit the same origin.
      const res = await axios.post('/calculate', params);
      setResults(res.data);
    } catch (err) {
      console.error(err);
      // alert('Calculation failed'); // Suppress alert for auto-calc
    } finally {
      setLoading(false);
    }
  };

  // Real-time calculation with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      handleCalculate();
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [params]);

  const handleChange = (key: keyof CraneParams) => (_: Event, value: number | number[]) => {
    setParams(prev => ({ ...prev, [key]: value as number }));
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>

      {/* 3D Viewer - Takes available space */}
      <div style={{ flex: 1, position: 'relative' }}>
        <Canvas camera={{ position: [2000, 2000, 2000], fov: 50, near: 1, far: 10000 }}>
          <color attach="background" args={['#f0f0f0']} />
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <OrbitControls makeDefault />
          <Grid infiniteGrid sectionColor="#666" cellColor="#ccc" fadeDistance={5000} />
          <Environment preset="city" />

          <Suspense fallback={null}>
            <CraneModel
              params={params}
              results={results}
              scale={deformationScale}
              viewMode={viewMode}
            />
          </Suspense>
        </Canvas>

        {/* Mobile Overlay Toggle Button */}
        {isMobile && (
          <Box position="absolute" bottom={0} left={0} right={0} zIndex={1000} bgcolor="rgba(255,255,255,0.9)">
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              p={1}
              onClick={() => setMobileOpen(!mobileOpen)}
              sx={{ cursor: 'pointer', borderBottom: 1, borderColor: 'divider' }}
            >
              <IconButton size="small" onClick={(e) => { e.stopPropagation(); setMobileOpen(!mobileOpen); }}>
                {mobileOpen ? <ExpandMore /> : <ExpandLess />}
              </IconButton>
              <Typography variant="subtitle2" color="textSecondary">
                {mobileOpen ? '設定を閉じる' : '設定を開く'}
              </Typography>
            </Box>
          </Box>
        )}
      </div>

      {/* Control Panel - Sidebar for Desktop / Overlay for Mobile */}
      <Paper
        elevation={3}
        style={isMobile ? {
          position: 'absolute',
          bottom: mobileOpen ? 40 : -1000, // Hide when closed, show above toggle when open
          left: 0,
          right: 0,
          maxHeight: '60vh',
          zIndex: 999,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          display: mobileOpen ? 'flex' : 'none', // Truly hide when closed on mobile
          flexDirection: 'column',
          backgroundColor: 'rgba(255, 255, 255, 0.95)'
        } : {
          width: 350,
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#fff',
          borderLeft: '1px solid #ccc',
          height: '100%',
          zIndex: 10
        }}
      >
        <Box p={2} sx={{ overflowY: 'auto', height: '100%' }}>
          <Typography variant="h5" gutterBottom>単管クレーンシミュレーター</Typography>

          <Stack spacing={2}>
            <FormControl fullWidth size="small">
              <InputLabel>単管パイプ種類</InputLabel>
              <Select
                value={pipeType}
                label="単管パイプ種類"
                onChange={handlePipeChange}
              >
                <MenuItem value="STK400">STK400 (標準, t=2.4mm, σy=235)</MenuItem>
                <MenuItem value="STK500">STK500 (高張力, t=2.4mm, σy=355)</MenuItem>
                <MenuItem value="SuperLight700">SuperLight700 (軽量, t=1.8mm, σy=700)</MenuItem>
              </Select>
            </FormControl>

            <Box>
              <Typography>台座 長さ: {params.base_len} mm</Typography>
              <Slider value={params.base_len} min={500} max={2000} onChange={handleChange('base_len')} />
            </Box>
            <Box>
              <Typography>台座 幅: {params.base_wid} mm</Typography>
              <Slider value={params.base_wid} min={300} max={1500} onChange={handleChange('base_wid')} />
            </Box>
            <Box>
              <Typography>三脚取付高さ: {params.tripod_attach_height} mm</Typography>
              <Slider value={params.tripod_attach_height} min={500} max={params.arm_pivot_height} onChange={handleChange('tripod_attach_height')} />
            </Box>
            <Box>
              <Typography>ブレース取付高さ: {params.brace_mast_height} mm</Typography>
              <Slider value={params.brace_mast_height} min={300} max={params.tripod_attach_height} onChange={handleChange('brace_mast_height')} />
            </Box>
            <Box>
              <Typography>アーム長さ: {params.arm_len} mm</Typography>
              <Slider value={params.arm_len} min={500} max={2000} onChange={handleChange('arm_len')} />
            </Box>
            <Box>
              <Typography>アーム角度: {params.arm_angle} deg</Typography>
              <Slider value={params.arm_angle} min={0} max={360} onChange={handleChange('arm_angle')} />
            </Box>
            <Box>
              <Typography>先端荷重: {params.mass_tip} kg</Typography>
              <Slider value={params.mass_tip} min={0} max={200} onChange={handleChange('mass_tip')} />
            </Box>
            <Box>
              <Typography>アーム取付高さ: {params.arm_pivot_height} mm</Typography>
              <Slider value={params.arm_pivot_height} min={1000} max={3000} onChange={handleChange('arm_pivot_height')} />
            </Box>

            <Button
              variant="contained"
              color="primary"
              onClick={handleCalculate}
              disabled={loading}
              fullWidth
            >
              FEM実行 (解析)
            </Button>
            {
              loading && (
                <Box display="flex" justifyContent="center" p={1}>
                  <CircularProgress size={24} />
                  <Typography variant="caption" ml={1}>計算中...</Typography>
                </Box>
              )
            }

            {
              results && (
                <>
                  <Box mt={2} borderTop={1} borderColor="divider" pt={2}>
                    <Typography variant="subtitle1" gutterBottom>可視化設定</Typography>

                    <ToggleButtonGroup
                      value={viewMode}
                      exclusive
                      onChange={(_, val) => val && setViewMode(val)}
                      fullWidth
                      size="small"
                    >
                      <ToggleButton value="geometry">形状</ToggleButton>
                      <ToggleButton value="stress">応力</ToggleButton>
                    </ToggleButtonGroup>

                    <Box mt={2}>
                      <Typography>変形倍率: x{deformationScale}</Typography>
                      <Slider
                        value={deformationScale}
                        min={0}
                        max={100}
                        onChange={(_, v) => setDeformationScale(v as number)}
                      />
                    </Box>
                  </Box>

                  <Box mt={2} borderTop={1} borderColor="divider" pt={2}>
                    <Typography variant="h6">計算結果</Typography>
                    <Typography>先端たわみ (DZ): {results.tip_displacement.dz.toFixed(3)} mm</Typography>
                    <Typography>最大応力: {results.max_stress.toFixed(1)} N/mm²</Typography>

                    {results.failures && results.failures.length > 0 ? (
                      <Box mt={1} p={1} bgcolor="#ffebee" border={1} borderColor="error.main" borderRadius={1}>
                        <Typography variant="subtitle2" color="error" fontWeight="bold">
                          ⚠️ 判定: 破断 (NG)
                        </Typography>
                        <Typography variant="caption" color="error">
                          {results.failures.length} 箇所の部材が降伏応力(235 N/mm²)を超過
                        </Typography>
                      </Box>
                    ) : (
                      <Box mt={1} p={1} bgcolor="#e8f5e9" border={1} borderColor="success.main" borderRadius={1}>
                        <Typography variant="subtitle2" color="success.main" fontWeight="bold">
                          ✅ 判定: 安全 (OK)
                        </Typography>
                      </Box>
                    )}

                    <Typography variant="subtitle2" mt={1}>マスト頂部変位:</Typography>
                    <Typography>DX: {results.node_displacements.M_top.dx.toFixed(3)}</Typography>
                    <Typography>DZ: {results.node_displacements.M_top.dz.toFixed(3)}</Typography>
                  </Box>
                </>
              )
            }
          </Stack >
        </Box>
      </Paper>
    </div>
  );
}
