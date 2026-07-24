# 恢复广告积分功能 — 操作指南

## 恢复步骤

### 1. 前端：恢复 AdBanner 广告条

**文件: `webapp/src/App.jsx`**

1. 取消注释第 12 行: `import AdBanner from './components/AdBanner'`
2. 取消注释 `adLoading` 状态 (原第 40 行): `const [adLoading, setAdLoading] = useState(false)`
3. 取消注释 `handleWatchAd` 回调函数 (原第 57-73 行)
4. 取消注释 header 中的广告积分按钮 (原第 174-178 行): 看广告📺按钮
5. 取消注释 content 中的 `<AdBanner>` 组件 (原第 211 行)

### 2. 前端：恢复 BillingModal 广告积分显示

**文件: `webapp/src/components/BillingModal.jsx`**

取消注释 `ad_reward_credits` 显示 (原第 72-74 行)

### 3. 后端：恢复广告积分 API

**文件: `backend/app/api/billing.py`**

恢复 `POST /api/v1/billing/ad-reward` 原函数体 (原第 178-228 行)，替换当前的 501 stub

### 4. 后端：恢复广告日志 API

**文件: `backend/app/api/ads.py`**

1. 恢复 `POST /api/v1/ads/log` 原函数体 (原第 19-43 行)
2. 恢复 `GET /api/v1/ads/stats` 原函数体 (原第 46-68 行)

### 5. 快速回滚命令

```bash
# 如果使用 git，切回原分支即可
git checkout rename/maneki-to-ai-workflow
# 或使用 patch 恢复（需在项目根目录执行）
git apply scripts/restore_ad_rewards.patch
```

## 改动文件清单

| 文件 | 修改类型 |
|---|---|
| `backend/app/api/ads.py` | 3 个端点改为 501 stub |
| `backend/app/api/billing.py` | ad-reward 端点改为 501 stub |
| `backend/app/main.py` | CORS 增加 localhost:5174 |
| `webapp/src/App.jsx` | 移除 AdBanner 导入/使用、广告积分按钮、handleWatchAd |
| `webapp/src/components/BillingModal.jsx` | 注释 ad_reward_credits 显示 |
| `webapp/src/components/LoginButtons.jsx` | 注释 Facebook handler |
| `webapp/src/pages/Login.jsx` | 注释 Facebook 按钮 |
