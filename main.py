import scipy.io
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 系统使用黑体 (Mac 用户请改为 'Arial Unicode MS')
plt.rcParams['axes.unicode_minus'] = False    # 确保正常显示
from scipy.interpolate import interp1d
import os

# =======================================================
# 模块 1：NASA 电池数据读取与解析
# =======================================================
def load_nasa_battery_data(file_path):
    print(f"正在加载数据文件: {file_path} ...")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"无法找到文件，请检查路径是否正确: {file_path}")
        
    mat_data = scipy.io.loadmat(file_path)
    # 动态获取变量名（针对 B0005.mat）
    battery_name = os.path.basename(file_path).split('.')[0] 
    battery_data = mat_data[battery_name][0][0]
    cycles = battery_data['cycle'][0]
    
    discharge_data_list = []
    
    for i, cycle in enumerate(cycles):
        if cycle['type'][0] == 'discharge':
            data = cycle['data'][0][0]
            cycle_info = {
                'cycle_index': i,
                'ambient_temperature': cycle['ambient_temperature'][0][0],
                'Voltage_measured': data['Voltage_measured'][0],
                'Current_measured': data['Current_measured'][0],
                'Temperature_measured': data['Temperature_measured'][0],
                'Time': data['Time'][0]
            }
            # 记录电池实验给出的参考容量
            if 'Capacity' in data.dtype.names:
                cycle_info['Capacity'] = data['Capacity'][0][0]
            discharge_data_list.append(cycle_info)
            
    print(f"数据加载完成！共提取到 {len(discharge_data_list)} 次放电循环。")
    return discharge_data_list

# =======================================================
# 模块 2：物理建模 (基于真实数据提取 OCV 曲线与 Ra 阻抗表)
# =======================================================
def build_battery_models(time, voltage, current):
    print("正在构建电池物理模型 (OCV & Resistance)...")
    
    # 1. 计算 Qmax (最大化学容量) [引用文档公式 4]
    dt_array = np.diff(time)
    # PassedCharge = 电流对时间的积分 [引用文档 3.1.2]
    passed_charge_array = -current[:-1] * dt_array
    total_qmax = np.sum(passed_charge_array)

    # 2. 建立放电深度数组 (DOD 0% - 100%)
    cumulative_charge = np.concatenate(([0], np.cumsum(passed_charge_array)))
    DOD_ref = cumulative_charge / total_qmax

    # 3. 提取内阻 R (简化模拟：包含基础内阻与末端极化激增)
    # 初始压降法获取 R0
    idx_start = np.argmax(current < -1.0)
    R_initial = (voltage[idx_start-1] - voltage[idx_start]) / abs(current[idx_start])
    R_array = R_initial + 0.05 * (DOD_ref ** 3) 

    # 4. 逆推开路电压 OCV = V - I*R [引用文档 3.1.1(2)]
    OCV_array = voltage - current * R_array

    # 生成查表插值函数
    get_OCV = interp1d(DOD_ref, OCV_array, kind='linear', fill_value='extrapolate')
    get_R = interp1d(DOD_ref, R_array, kind='linear', fill_value='extrapolate')
    
    return total_qmax, get_OCV, get_R

# =======================================================
# 模块 3：核心算法 (严格遵循 TI 指南图 3.8 流程)
# =======================================================
def run_impedance_track_simulation(time, current, T, Terminate_Voltage, Qmax, get_OCV, get_R):
    print("正在运行阻抗跟踪法实时估算...")
    
    # 初始参数设定 [引用文档 3.1.4]
    DOD0 = 0.0          # 假设初始完全充满
    DODatEOC = 0.0      # 充满电时的放电深度
    Qstart = (DOD0 - DODatEOC) * Qmax # [引用文档公式 8]
    
    passed_charge = 0.0
    results = {'soc': [], 'fcc': [], 'rm': []}

    for k in range(1, len(time)):
        dt = time[k] - time[k-1]
        I_now = current[k] # 真实放电电流 (负数)

        # 1. 累计已放出容量 [引用文档 3.1.2]
        passed_charge += -I_now * dt
        
        # 2. 计算当前放电深度 DOD_Present [引用文档公式 10]
        DOD_Present = min(max(DOD0 + (passed_charge / Qmax), 0.0), 1.0)

        # 3. 右侧预测流程：推演未来关机深度 DOD_Final [引用文档 3.1.4 右侧图]
        DOD_temp = DOD_Present
        dDOD = 0.005 # 步进 0.5%
        I_sim = I_now if I_now < -0.1 else -1.0 # 仿真负载

        while DOD_temp < 1.0:
            DOD_temp += dDOD
            # V_sim = OCV + I*R [引用文档 3.1.1(2)]
            V_sim = float(get_OCV(DOD_temp)) + I_sim * float(get_R(DOD_temp))
            if V_sim < Terminate_Voltage: # 撞击关机电压
                break
        
        DOD_Final = min(DOD_temp, 1.0)

        # 4. 计算剩余容量 RM [引用文档公式 9]
        RM = max((DOD_Final - DOD_Present) * Qmax, 0.0)
        
        # 5. 计算动态满充容量 FCC [引用文档公式 7]
        FCC = Qstart + passed_charge + RM
        
        # 6. 计算电量百分比 RSOC [引用文档 3.1.1(1)]
        RSOC = (RM / FCC) * 100.0 if FCC > 0 else 0.0

        results['soc'].append(RSOC)
        results['fcc'].append(FCC)
        results['rm'].append(RM)
        
    return results

# =======================================================
# 主程序入口
# =======================================================
if __name__ == "__main__":
    # --- 路径配置 (已改为你的指定路径) ---
    FILE_PATH = 'D:/桌面文件夹/大学课业/battery_project/battery_soc/data/B0005.mat'
    
    # 1. 提取数据
    discharge_list = load_nasa_battery_data(FILE_PATH)
    first_cycle = discharge_list[0] # 使用首次放电数据作为基准
    
    time = first_cycle['Time']
    voltage = first_cycle['Voltage_measured']
    current = first_cycle['Current_measured']
    
    # 2. 离线建模 (获取字典)
    Qmax, get_OCV, get_R = build_battery_models(time, voltage, current)
    
    # 3. 执行阻抗跟踪法
    # NASA B0005 放电截止电压设为 2.7V [参考 README.txt]
    sim_data = run_impedance_track_simulation(time, current, 25.0, 2.7, Qmax, get_OCV, get_R)
    
    # 4. 绘图显示
    print("生成结果图表中...")
    plt.figure(figsize=(10, 8))

    plt.subplot(2, 1, 1)
    plt.plot(time[1:], sim_data['soc'], color='blue', label='RSOC (%)')
    plt.title(f"Impedance Track SOC Estimation\nFile: {os.path.basename(FILE_PATH)}")
    plt.ylabel("SOC (%)")
    plt.grid(True)
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(time[1:], np.array(sim_data['fcc'])/3600, color='green', label='FCC (Ah)')
    plt.plot(time[1:], np.array(sim_data['rm'])/3600, color='red', label='RM (Ah)')
    plt.xlabel("Time (s)")
    plt.ylabel("Capacity (Ah)")
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.show()

# =======================================================
# 进阶分析：多次循环的电池老化 (Aging) 可视化
# =======================================================
if __name__ == "__main__":
    # 请确保路径正确
    FILE_PATH = 'D:/桌面文件夹/大学课业/battery_project/battery_soc/data/B0005.mat' 
    discharge_list = load_nasa_battery_data(FILE_PATH)
    
    print("正在生成多次循环老化分析图表...")
    
    # ---------------------------------------------------
    # 图 1：电池容量衰减曲线 (Capacity Fade)
    # ---------------------------------------------------
    cycles = []
    capacities = []
    
    # 遍历所有 168 次放电，提取真实容量
    for d in discharge_list:
        if 'Capacity' in d:
            cycles.append(d['cycle_index'])
            capacities.append(d['Capacity'])
            
    plt.figure(figsize=(12, 10))
    
    plt.subplot(2, 1, 1)
    plt.plot(cycles, capacities, marker='o', markersize=4, linestyle='-', color='#1f77b4')
    # NASA 定义的寿命终点 EOL (End of Life) = 1.4Ah
    plt.axhline(y=1.4, color='red', linestyle='--', linewidth=2, label='EOL 寿命终点 (1.4 Ah)')
    plt.title("NASA B0005 电池容量衰减曲线 (SOH)", fontsize=14, fontweight='bold')
    plt.xlabel("测试操作序号 (Cycle Index)", fontsize=12)
    plt.ylabel("真实放电容量 (Ah)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12)

    # ---------------------------------------------------
    # 图 2：不同寿命阶段的端电压坍塌对比
    # ---------------------------------------------------
    plt.subplot(2, 1, 2)
    
    # 我们挑选极具代表性的 4 个时期：全新、轻度老化、中度老化、报废边缘
    target_indices = [0, 50, 100, 160] 
    colors = ['#2ca02c', '#ff7f0e', '#9467bd', '#d62728']
    
    for i, idx in enumerate(target_indices):
        if idx < len(discharge_list):
            cycle_data = discharge_list[idx]
            plt.plot(cycle_data['Time'], cycle_data['Voltage_measured'], 
                     label=f'第 {idx+1} 次放电 (容量: {cycle_data.get("Capacity", 0):.2f} Ah)', 
                     color=colors[i], linewidth=2)

    plt.axhline(y=2.7, color='black', linestyle=':', linewidth=2, label='关机截止电压 (2.7V)')
    plt.title("不同老化阶段的放电电压曲线坍塌对比", fontsize=14, fontweight='bold')
    plt.xlabel("放电时间 (秒)", fontsize=12)
    plt.ylabel("端电压 (V)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=11)

    plt.tight_layout()
    plt.show()