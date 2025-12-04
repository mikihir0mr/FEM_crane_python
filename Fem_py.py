from PyNite import FEModel3D

model = FEModel3D()

# 節点を定義（座標は mm でも m でもOK、単位を揃えればいい）
model.AddNode("N1", 0,   0, 0)
model.AddNode("N2", 0,   0, 1.15)  # マスト上端（例）
model.AddNode("N3", 0.7, 0, 1.15)  # アーム先端（例）

# 材料
E  = 2.05e11      # Pa (鋼)
nu = 0.3
rho = 7850        # kg/m^3
G  = E / (2*(1+nu))

# 単管パイプ断面（外径48.6, t=2.4）→ 断面積A, Iy, Iz, J を計算して入れる
# ここは俺が計算コードを書く係になれる

# model.AddMember("M_mast", "N1", "N2", E, G, Iy, Iz, J, A)
# model.AddMember("M_arm",  "N2", "N3", E, G, Iy, Iz, J, A)
# model.AddMember("M_brace", ..., ..., E, G, Iy, Iz, J, A)

# 支持条件（台座固定）
# model.DefineSupport("N1", True, True, True, True, True, True)

# 荷重（アーム先端に下向き）
# model.AddNodeLoad("N3", "FZ", -P)  # P = 50kg×9.81 など

# 解析
# model.Analyze()

# 結果取得
# print(model.GetNodeDisplacement("N3", "DZ"))
# model.GetMember("M_arm").PlotDeflection("dz")
