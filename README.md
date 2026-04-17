# 🔋 Lithium-ion Battery SOC & SOH Estimation System
### Based on NASA B0005 Dataset & Impedance Track Algorithm

[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📌 Project Introduction
This project implements a comprehensive battery state estimation system using the **Impedance Track** method. By parsing the **NASA Ames Prognostics Dataset**, the model extracts physical electrochemical features to perform high-precision State of Charge (SOC) and State of Health (SOH) estimation. 

Compared to traditional Coulomb counting, this implementation utilizes **dynamic physical modeling** to eliminate capacity jumps and cumulative errors during discharge.

## ✨ Key Features
* **Raw Data Parsing**: Automated extraction of time, voltage, and current from complex MATLAB `.mat` structures (616 total cycles).
* **Physical Parameter Identification**: Reverse-engineered the **Open Circuit Voltage (OCV)** curve and **Dynamic Resistance (R)** table based on real-world steady-state discharge data.
* **Real-time SOC Simulation**: Implemented a "future-prediction" loop using a 0.5% dDOD step to identify the **DOD_Final** point, ensuring a stable Full Charge Capacity (FCC) estimation.
* **Aging (SOH) Analysis**: Quantitative tracking of **Capacity Fade** (from 1.85Ah to 1.4Ah EOL) and discharge voltage collapse across the battery lifecycle.

## 🛠️ Technical Stack
* **Programming**: Python 3.x
* **Data Processing**: `NumPy`, `SciPy` (for MATLAB I/O and 1D interpolation)
* **Visualization**: `Matplotlib`
* **Algorithm**: TI Impedance Track Logic, Physical Modeling

## 📂 Project Structure
```text
.
├── main.py                   # Core simulation & visualization script
├── B0005.mat                 # NASA raw experimental data (Cycle 1-616)
└── NASA_Dataset_README.txt   # Original experimental setup documentation
```

## 🚀 How to Run
Clone the repo:

Bash
git clone [https://github.com/TeslaCui/Battery_SOC_SOH_Simulation_v1_20260414.git](https://github.com/TeslaCui/Battery_SOC_SOH_Simulation_v1_20260414.git)
Install dependencies:

Bash
pip install numpy scipy matplotlib
Run the simulation:

Bash
python main.py

## 📊 Results & Analysis
1. Single Cycle SOC Estimation
The algorithm provides a smooth RSOC (%) curve and maintains a flat FCC (Full Charge Capacity) near 1.85Ah, effectively solving the "tail-up" error seen in basic models.
<img width="917" height="721" alt="SOC" src="https://github.com/user-attachments/assets/94ebefff-6184-4c43-aa94-a7bc7b093c92" />
<br>

3. Lifecycle Aging (SOH)
Visualized the degradation of cell B0005, demonstrating how internal resistance surge leads to voltage collapse and shortened discharge duration.
<img width="936" height="672" alt="SOH" src="https://github.com/user-attachments/assets/7ecc89c5-f3ec-464b-b1e4-e2d1ae4b3a74" />

## 📂 Data Source & Acknowledgement
The simulation is driven by the NASA Ames Prognostics Data Repository.

Developed by: 崔裕德 (Yude Cui)

Affiliation: 上海交通大学 (SJTU)
