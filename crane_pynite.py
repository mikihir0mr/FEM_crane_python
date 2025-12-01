# crane_pynite.py
# 単管クレーンフレームを PyNiteFEA で 3Dフレーム解析するスクリプト
# 単位系：長さ mm, 力 N, 応力 N/mm^2(MPa)

from Pynite import FEModel3D
import math

# ----------------------------
# 1. ジオメトリ & 荷重パラメータ
# ----------------------------

# 単管
pipe_od = 48.6        # [mm] 外径
t_wall  = 2.4         # [mm] 肉厚
R = pipe_od / 2.0     # 外半径
r = R - t_wall        # 内半径

# 台座
base_len = 900.0      # [mm] X方向
base_wid = 600.0      # [mm] Y方向

# 垂直の棒
arm_pivot_height     = 1800.0  # [mm] アーム取り付き高さ
tripod_attach_height = 1000.0  # [mm] 三脚脚取り付き高さ
brace_mast_height    = 800.0   # [mm] ブレース取り付き高さ

# アーム
arm_len   = 1000.0    # [mm]
arm_angle = 180.0     # [deg] 0=+X, 180 で -X 方向

# 荷重（アーム先端に 50kg）
mass_tip = 100       # [kg]
g = 9.81              # [m/s^2]
P_tip = mass_tip * g  # [N] 下向き

# 座標のZオフセット（パイプ中心が z0）
z0 = pipe_od / 2.0

# ----------------------------
# 2. 断面・材料プロパティ
# ----------------------------

# 断面積 A [mm^2]
A = math.pi * (R**2 - r**2)

# 断面二次モーメント Iy, Iz [mm^4]（円環）
I = (math.pi / 4.0) * (R**4 - r**4)
Iy = I
Iz = I

# ねじり定数 J [mm^4]（円断面: J = Iy + Iz）
J = Iy + Iz

# 材料：鋼（N/mm^2 ベース）
E = 2.05e5           # [N/mm^2] ヤング率 ≒ 205 GPa
nu = 0.3
G = E / (2.0 * (1.0 + nu))
rho = 7.85e-6        # [ton/mm^3] 相当（自重は今回は使わないので適当でOK）

# ----------------------------
# 3. モデル生成
# ----------------------------

model = FEModel3D()

# 材料を追加
model.add_material('Steel', E, G, nu, rho)

# 断面を追加（円環断面）
model.add_section('Pipe48x2p4', A=A, Iy=Iy, Iz=Iz, J=J)

# ----------------------------
# 4. 節点座標（OpenSCAD と同じ幾何）
# ----------------------------

L = base_len
W = base_wid

# 台座四隅
nodes = {}

nodes['FL'] = (-L/2.0, -W/2.0, z0)   # front-left
nodes['FR'] = ( L/2.0, -W/2.0, z0)   # front-right
nodes['RR'] = ( L/2.0,  W/2.0, z0)   # rear-right
nodes['RL'] = (-L/2.0,  W/2.0, z0)   # rear-left

# 台座中間
nodes['Fmid']   = (0.0, -W/2.0, z0)  # 前側中央
nodes['Rmid']   = (0.0,  W/2.0, z0)  # 後側中央
nodes['Lmid']   = (-L/2.0, 0.0, z0)  # 左中央（＝垂直の棒根元）
nodes['RmidX0'] = ( L/2.0, 0.0, z0)  # 右中央

# 垂直の棒関連
# nodes['M_base']  = nodes['Lmid']                       # (-450, 0, z0) -> Use Lmid directly
nodes['M_brace'] = (-L/2.0, 0.0, z0 + brace_mast_height)    # ブレース取り付き
nodes['M_attach'] = (-L/2.0, 0.0, z0 + tripod_attach_height) # 三脚脚取り付き
nodes['M_top']    = (-L/2.0, 0.0, z0 + arm_pivot_height)     # アーム接続点

# アーム関連
arm_dir = (
    math.cos(math.radians(arm_angle)),
    math.sin(math.radians(arm_angle)),
    0.0
)

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

# ----------------------------
# 5. PyNite に節点を追加
# ----------------------------

for name, (x, y, z) in nodes.items():
    model.add_node(name, x, y, z)

# ----------------------------
# 6. 部材（単管）を追加
# ----------------------------

# ヘルパー：部材追加
def add_member(mname, ni, nj):
    model.add_member(
        name=mname,
        i_node=ni,
        j_node=nj,
        material_name='Steel',
        section_name='Pipe48x2p4'
    )

# 台座外周
add_member('M_base_FL_FR', 'FL', 'FR')
add_member('M_base_FR_RR', 'FR', 'RR')
add_member('M_base_RR_RL', 'RR', 'RL')
add_member('M_base_RL_FL', 'RL', 'FL')

# 台座中桟
add_member('M_base_Fmid_Rmid', 'Fmid', 'Rmid')
add_member('M_base_Lmid_RmidX0', 'Lmid', 'RmidX0')

# 垂直の棒：途中で節点を切っておく（ブレース・三脚接続点）
add_member('M_mast_1', 'Lmid',  'M_brace')
add_member('M_mast_2', 'M_brace', 'M_attach')
add_member('M_mast_3', 'M_attach','M_top')

# 三脚脚
add_member('M_tripod_FL', 'M_attach', 'FL')
add_member('M_tripod_RL', 'M_attach', 'RL')

# アーム
add_member('M_arm', 'M_top', 'A_tip')

# ブレース（垂直の棒〜アーム）
add_member('M_brace', 'M_brace', 'A_brace')

# ----------------------------
# 7. 支持条件（台座四隅を固定）
# ----------------------------

# ここでは簡易的に、台座四隅の平行移動を全部固定、回転は自由とする
# def_support(node, DX, DY, DZ, RX, RY, RZ)
for n in ['FL', 'FR', 'RR', 'RL']:
    model.def_support(n, True, True, True, False, False, False)

# ----------------------------
# 8. 荷重（アーム先端に下向き 50kg）
# ----------------------------

# FZ 方向の荷重（グローバル Z マイナス）
# load case name を 'DL'（Dead Load）としておく
model.add_node_load('A_tip', 'FZ', -P_tip, 'DL')

# ----------------------------
# 9. 解析実行
# ----------------------------

# 線形静解析を実行（デフォルトで 'Combo 1' を作ってくれる）
model.add_load_combo('Combo 1', {'DL': 1.0})
model.analyze(check_statics=True)

combo = 'Combo 1'

# ----------------------------
# 10. 結果の例（アーム先端のたわみなど）
# ----------------------------

tip_node = model.nodes['A_tip']

# ノード変位は DX, DY, DZ にロードコンボごとの辞書として入っている想定
dz_tip = tip_node.DZ[combo]  # [mm] 下向きがマイナスのはず

print('=== PyNite 単管クレーン解析結果 ===')
print(f'アーム先端ノード A_tip 座標: {nodes["A_tip"]} [mm]')
print(f'アーム先端の鉛直変位 DZ: {dz_tip:.3f} mm  (負なら下向き)')

print('\n--- 垂直の棒の変位 (DX, DY, DZ) ---')
mast_nodes = ['Lmid', 'M_brace', 'M_attach', 'M_top']
for n_name in mast_nodes:
    node = model.nodes[n_name]
    dx = node.DX.get(combo, 0.0)
    dy = node.DY.get(combo, 0.0)
    dz = node.DZ.get(combo, 0.0)
    print(f'Node {n_name:10s}: DX={dx:6.3f}, DY={dy:6.3f}, DZ={dz:6.3f} [mm]')
print('---------------------------------')

# 台座四隅の反力も見てみる
for n in ['FL', 'FR', 'RR', 'RL']:
    node = model.nodes[n]
    # 反力もロードコンボごとの辞書
    rz = node.RxnFZ.get(combo, 0.0)
    print(f'支点 {n} の鉛直反力 FZ: {rz:.3f} N')
