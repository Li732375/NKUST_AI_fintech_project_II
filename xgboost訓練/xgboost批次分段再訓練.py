# =============================================================================
# 同一模型多批次再訓練
# =============================================================================

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
import math
from xgboost import XGBClassifier
import time
import os
import Plot

# 讀取資料
df = pd.read_excel("../data.xlsx")
print(f"總資料數：{len(df)}")

df_Latest = pd.read_excel("../data_Latest.xlsx")
print(f"最新數據測試集總資料數：{len(df_Latest)}")

# =============================================================================
# feature_names = ['Gold_Close', 'Gold_High', 'CPIAUCNS', 'Gold_Open', 'UNRATE', 
#                  'MA_20', 'MA_10', 'USD_Index_Growth_Rate', 'TW_CPI_Rate', 
#                  'WILLR', 'Open', 'K', 'RSI_14', 'Gold_Volume', 
#                  'Gold_Growth_Rate', 'FEDFUNDS', 'Bollinger Bands lower', 
#                  'Bollinger Bands Upper', 'USA_GDP_Rate']
# =============================================================================

feature_names = ['CPI_Delta', 'UNRATE', 'Gold_High', 'FEDFUNDS', 'USA_CPI_Rate', 'WILLR', 'USD_Index_Growth_Rate', 'WMA', 'Close', 'Gold_Volume', 'MACD', 'Low', 'LINEARREG_ANGLE', 'CCI', 'TW_CPI_Rate']


X = df[feature_names].values
y = df['LABEL'].values

X_Latest = df_Latest[feature_names].values
y_Latest = df_Latest['LABEL'].values


n_splits = 9 # 設定分割數量
overlap_rate = 3 * 0.1 + 1 # 設定每批訓練集之間的，最低重疊率
max_train_size = math.ceil(len(df) // n_splits * overlap_rate) if \
    len(df) % n_splits == 0 else math.ceil(len(df) / n_splits * overlap_rate) # 計算最大訓練集大小
print(f"最大資料長度 {max_train_size}")

# 初始化 TimeSeriesSplit
TSS = TimeSeriesSplit(n_splits = n_splits, max_train_size = max_train_size)
# 不可指定訓練與測試集的占比

# 儲存每個折的訓練集索引
split_indices = [None for _ in range(n_splits)]
batch_test_scores = []
latest_test_scores = []

Xgboost = XGBClassifier()

# 逐步分割資料
for i, (train_index, test_index) in enumerate(TSS.split(X, y)):
    split_indices[i] = train_index
    sub_train_index = df.iloc[train_index]
    sub_test_index = df.iloc[test_index]
    train_len = len(sub_train_index)
    test_len = len(sub_test_index)
    all_len = train_len + test_len
    
    # print('--------------')
    # print(f"第 {i+1} 份")
    # print(f"子訓練集資料數：{train_len}")
    # print(f"子測試集資料數：{test_len} (佔批次 {test_len / all_len * 100:.1f} %)")
    # print(f"子訓練集索引（頭尾 5 個）：{sub_train_index.index.tolist()[:5]}...{sub_train_index.index.tolist()[-5:]}")
    # print(f"子測試集索引（頭尾 5 個）：{sub_test_index.index.tolist()[:5]}...{sub_test_index.index.tolist()[-5:]}")
    
    # 提取訓練集和測試集
    sub_trainX, sub_testX = X[train_index], X[test_index]
    sub_trainY, sub_testY = y[train_index], y[test_index]
    
    # 如果模型檔案存在，載入模型；否則初始化一個新模型
    if os.path.exists(f'xgboost_model_{i}.json'):
        Xgboost.load_model(f'xgboost_model_{i}.json')
        print(f'載入模型：xgboost_model_{i}.json')
    else:
        print(f'初始化新模型：xgboost_model_{i}.json')
        
    # 訓練 XGBoost 模型
    start_time = time.time()
    Xgboost.fit(sub_trainX, sub_trainY)
    training_time = time.time() - start_time
    
    # 批次測試集預測結果和模型準確率
    test_acc = Xgboost.score(sub_testX, sub_testY)
    batch_test_scores.append(test_acc)
    
    print('Xgboost測試集準確率 %.3f' % test_acc)
    print(f"訓練時間: {training_time // 60:.0f} 分 {training_time % 60:.2f} 秒")
    
    # 最新資料測試
    latest_data_test_acc = Xgboost.score(X_Latest, y_Latest)
    latest_test_scores.append(latest_data_test_acc)
    
    # 儲存當前訓練後的模型
    Xgboost.save_model(f'xgboost_model_{i + 1}.json')


# 計算重疊率
def calculate_overlap_rate(indices_list):
    total_overlap = 0
    total_count = len(df)
    
    for i in range(len(indices_list)):
        for j in range(i + 1, len(indices_list)):
            overlap_count = len(set(indices_list[i]).intersection(
                set(indices_list[j])))
            total_overlap += overlap_count

    overlap_rate = total_overlap / total_count
    return overlap_rate

overlap_rate = calculate_overlap_rate(split_indices)
print(f"資料彼此重疊率：{overlap_rate * 100:.2f} %")


# 繪製圖形
Plot.AccLineAndDataArea_Draw('批次分段再訓練', batch_test_scores, latest_test_scores, 
                             TSS.split(X, y), len(df), n_splits)