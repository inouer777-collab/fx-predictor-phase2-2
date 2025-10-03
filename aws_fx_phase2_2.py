#!/usr/bin/env python3
"""
Phase 2.2 Live API Edition: FX予測アプリ - Live API確実取得版
- より確実なAPI接続戦略
- AWS App Runner環境最適化
- 複数エンドポイント + 改善されたエラーハンドリング
"""

import http.server
import socketserver
import json
import datetime
import random
import math
import os
import time
from typing import Dict, List, Tuple, Any, Optional

# Phase 2.1: requestsライブラリ
try:
    import requests
    REQUESTS_AVAILABLE = True
    print("✅ requests ライブラリ利用可能")
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests ライブラリなし - 標準ライブラリモードで動作")
    import urllib.request
    import urllib.parse
    import urllib.error

# Phase 2.2: python-dateutilライブラリ
try:
    from dateutil import tz, relativedelta, parser
    from dateutil.relativedelta import relativedelta
    from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
    DATEUTIL_AVAILABLE = True
    print("✅ python-dateutil ライブラリ利用可能")
except ImportError:
    DATEUTIL_AVAILABLE = False
    print("⚠️ python-dateutil ライブラリなし - 基本日付処理で動作")

class BusinessDayCalculator:
    """営業日計算クラス（Phase 2.2機能）"""
    
    def __init__(self):
        self.major_holidays = {
            "JP": [(1, 1), (2, 11), (4, 29), (5, 3), (5, 4), (5, 5), (12, 31)],
            "US": [(1, 1), (7, 4), (12, 25)],
            "UK": [(1, 1), (12, 25), (12, 26)]
        }
    
    def is_business_day(self, date: datetime.date, country: str = "JP") -> bool:
        if not DATEUTIL_AVAILABLE:
            return date.weekday() < 5
        
        if date.weekday() >= 5:
            return False
        
        holidays = self.major_holidays.get(country, [])
        month_day = (date.month, date.day)
        return month_day not in holidays
    
    def get_next_business_day(self, date: datetime.date, country: str = "JP") -> datetime.date:
        next_date = date + datetime.timedelta(days=1)
        while not self.is_business_day(next_date, country):
            next_date += datetime.timedelta(days=1)
        return next_date
    
    def add_business_days(self, start_date: datetime.date, business_days: int, country: str = "JP") -> datetime.date:
        if not DATEUTIL_AVAILABLE or business_days <= 0:
            return start_date + datetime.timedelta(days=business_days)
        
        current_date = start_date
        added_days = 0
        
        while added_days < business_days:
            current_date = self.get_next_business_day(current_date, country)
            added_days += 1
        
        return current_date

class TimezoneManager:
    """タイムゾーン管理クラス（Phase 2.2機能）"""
    
    def __init__(self):
        self.market_timezones = {
            "Tokyo": "Asia/Tokyo", "London": "Europe/London", 
            "New_York": "America/New_York", "UTC": "UTC"
        }
        self.market_hours = {
            "Tokyo": {"open": 9, "close": 15},
            "London": {"open": 8, "close": 16.5},
            "New_York": {"open": 9.5, "close": 16}
        }
    
    def get_timezone(self, timezone_name: str):
        if not DATEUTIL_AVAILABLE:
            return None
        try:
            if timezone_name in self.market_timezones:
                return tz.gettz(self.market_timezones[timezone_name])
            return tz.gettz(timezone_name)
        except Exception:
            return None
    
    def convert_to_timezone(self, dt: datetime.datetime, target_timezone: str) -> Optional[datetime.datetime]:
        if not DATEUTIL_AVAILABLE:
            return dt
        try:
            target_tz = self.get_timezone(target_timezone)
            if target_tz is None:
                return dt
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.UTC)
            return dt.astimezone(target_tz)
        except Exception:
            return dt
    
    def is_market_open(self, market: str, dt: Optional[datetime.datetime] = None) -> bool:
        if not DATEUTIL_AVAILABLE or market not in self.market_hours:
            return True
        
        if dt is None:
            dt = datetime.datetime.now()
        
        market_time = self.convert_to_timezone(dt, market)
        if market_time is None:
            return True
        
        business_calc = BusinessDayCalculator()
        if not business_calc.is_business_day(market_time.date()):
            return False
        
        hours = self.market_hours[market]
        current_hour = market_time.hour + market_time.minute / 60.0
        return hours["open"] <= current_hour <= hours["close"]

class EnhancedFXDataProvider:
    """強化されたFXデータプロバイダー（Live API確実取得版）"""
    
    def __init__(self):
        # より確実なAPI戦略
        self.api_configs = [
            {
                "name": "exchangerate-api",
                "url": "https://api.exchangerate-api.com/v4/latest/USD",
                "timeout": 15,
                "retries": 3,
                "headers": {
                    'User-Agent': 'Mozilla/5.0 (compatible; FX-Predictor/2.2)',
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            },
            {
                "name": "exchangerate-host",
                "url": "https://api.exchangerate.host/latest?base=USD",
                "timeout": 12,
                "retries": 2,
                "headers": {
                    'User-Agent': 'Mozilla/5.0 (compatible; FX-Predictor/2.2)',
                    'Accept': 'application/json'
                }
            },
            {
                "name": "fxratesapi",
                "url": "https://api.fxratesapi.com/latest?base=USD",
                "timeout": 10,
                "retries": 2,
                "headers": {
                    'User-Agent': 'curl/7.64.1',
                    'Accept': 'application/json'
                }
            },
            {
                "name": "vatcomply",
                "url": "https://api.vatcomply.com/rates?base=USD",
                "timeout": 8,
                "retries": 1,
                "headers": {
                    'User-Agent': 'FX-Predictor-Bot/2.2',
                    'Accept': 'application/json'
                }
            }
        ]
        
        # 現実的なフォールバックレート
        self.fallback_rates = {
            "USD/JPY": 147.49,
            "EUR/JPY": 173.16,
            "EUR/USD": 1.174
        }
        
        self.timezone_manager = TimezoneManager()
        
        # API成功ログ
        self.last_successful_api = None
        self.api_success_count = {}
    
    def get_real_fx_rate(self, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """Live FXレート取得（強化版）"""
        
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests不可 - 標準ライブラリでAPI試行")
            return self._try_urllib_apis(pair, timezone)
        
        print(f"🔄 Live API取得開始: {pair}")
        
        # 各APIを順番に試行（リトライ付き）
        for api_idx, api_config in enumerate(self.api_configs):
            api_name = api_config['name']
            retries = api_config.get('retries', 1)
            
            for attempt in range(retries + 1):
                try:
                    print(f"🔄 [{api_idx+1}/{len(self.api_configs)}] {api_name} 試行 {attempt+1}/{retries+1}")
                    
                    # セッション作成（接続再利用）
                    session = requests.Session()
                    session.headers.update(api_config['headers'])
                    
                    response = session.get(
                        api_config['url'],
                        timeout=api_config['timeout'],
                        allow_redirects=True,
                        verify=True  # SSL検証有効
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = self._parse_api_data(data, pair, timezone, api_name)
                        
                        if result and result.get('rate', 0) > 0:
                            print(f"✅ {api_name} API成功! {pair} = {result['rate']}")
                            
                            # 成功統計更新
                            self.last_successful_api = api_name
                            self.api_success_count[api_name] = self.api_success_count.get(api_name, 0) + 1
                            
                            return result
                    else:
                        print(f"⚠️ {api_name} HTTP {response.status_code}: {response.reason}")
                        
                except requests.exceptions.Timeout:
                    print(f"⏰ {api_name} タイムアウト (試行 {attempt+1})")
                    time.sleep(0.5)  # 短時間待機
                    continue
                    
                except requests.exceptions.ConnectionError:
                    print(f"🔌 {api_name} 接続エラー (試行 {attempt+1})")
                    time.sleep(0.5)
                    continue
                    
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ {api_name} リクエストエラー: {str(e)[:100]}")
                    continue
                    
                except json.JSONDecodeError:
                    print(f"⚠️ {api_name} JSON解析エラー")
                    continue
                    
                except Exception as e:
                    print(f"⚠️ {api_name} 予期しないエラー: {str(e)[:100]}")
                    continue
        
        print("⚠️ 全API失敗 - 高品質フォールバック使用")
        return self._get_high_quality_fallback(pair, timezone)
    
    def _try_urllib_apis(self, pair: str, timezone: str) -> Dict[str, Any]:
        """標準ライブラリでのAPI試行"""
        simple_apis = [
            "https://api.exchangerate-api.com/v4/latest/USD",
            "https://api.exchangerate.host/latest?base=USD"
        ]
        
        for api_url in simple_apis:
            try:
                print(f"🔄 urllib試行: {api_url}")
                
                req = urllib.request.Request(
                    api_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; FX-Predictor/2.2)',
                        'Accept': 'application/json'
                    }
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.getcode() == 200:
                        data = json.loads(response.read().decode())
                        result = self._parse_api_data(data, pair, timezone, "urllib")
                        
                        if result and result.get('rate', 0) > 0:
                            print(f"✅ urllib API成功! {pair} = {result['rate']}")
                            return result
                            
            except Exception as e:
                print(f"⚠️ urllib API失敗: {str(e)[:100]}")
                continue
        
        return self._get_high_quality_fallback(pair, timezone)
    
    def _parse_api_data(self, data: Dict, pair: str, timezone: str, api_name: str) -> Optional[Dict[str, Any]]:
        """統一API データ解析"""
        try:
            # exchangerate-api形式
            if 'rates' in data and 'base' in data:
                rates = data['rates']
                
                if pair == "USD/JPY":
                    rate = rates.get("JPY")
                elif pair == "EUR/JPY":
                    eur_rate = rates.get("EUR", 0)
                    jpy_rate = rates.get("JPY", 0)
                    rate = jpy_rate / eur_rate if eur_rate > 0 else None
                elif pair == "EUR/USD":
                    eur_rate = rates.get("EUR", 0)
                    rate = 1 / eur_rate if eur_rate > 0 else None
                else:
                    rate = None
            
            # exchangerate.host形式
            elif 'rates' in data:
                rates = data['rates']
                if pair == "USD/JPY":
                    rate = rates.get("JPY")
                elif pair == "EUR/JPY":
                    eur_rate = rates.get("EUR", 0)
                    jpy_rate = rates.get("JPY", 0)
                    rate = jpy_rate / eur_rate if eur_rate > 0 else None
                elif pair == "EUR/USD":
                    rate = rates.get("EUR")
                else:
                    rate = None
            
            # その他の形式
            else:
                print(f"⚠️ {api_name} 未知のデータ形式")
                return None
            
            # レート検証
            if rate and self._validate_rate(pair, rate):
                current_time = datetime.datetime.now()
                localized_time = self.timezone_manager.convert_to_timezone(current_time, timezone)
                
                return {
                    "rate": round(float(rate), 4),
                    "source": "Live API",
                    "timestamp": current_time.isoformat(),
                    "localized_timestamp": localized_time.isoformat() if localized_time else current_time.isoformat(),
                    "timezone": timezone,
                    "base_currency": data.get("base", "USD"),
                    "api_provider": api_name,
                    "data_quality": "Live"
                }
            else:
                print(f"⚠️ {api_name} 無効なレート: {rate}")
                return None
                
        except Exception as e:
            print(f"⚠️ {api_name} データ解析エラー: {e}")
            return None
    
    def _validate_rate(self, pair: str, rate: float) -> bool:
        """レート妥当性検証"""
        try:
            rate = float(rate)
            
            ranges = {
                "USD/JPY": (80.0, 250.0),
                "EUR/JPY": (100.0, 300.0),
                "EUR/USD": (0.5, 2.0)
            }
            
            if pair in ranges:
                min_rate, max_rate = ranges[pair]
                return min_rate <= rate <= max_rate
            
            return rate > 0
            
        except (ValueError, TypeError):
            return False
    
    def _get_high_quality_fallback(self, pair: str, timezone: str) -> Dict[str, Any]:
        """高品質フォールバックレート"""
        base_rate = self.fallback_rates.get(pair, 100.0)
        
        # 時間ベースの微小変動
        current_hour = datetime.datetime.now().hour
        time_variation = math.sin(current_hour * math.pi / 12) * 0.002
        
        # ランダム変動
        random_variation = random.uniform(-0.003, 0.003)
        
        rate = base_rate * (1 + time_variation + random_variation)
        
        current_time = datetime.datetime.now()
        localized_time = self.timezone_manager.convert_to_timezone(current_time, timezone)
        
        return {
            "rate": round(rate, 4),
            "source": "High-Quality Simulation",
            "timestamp": current_time.isoformat(),
            "localized_timestamp": localized_time.isoformat() if localized_time else current_time.isoformat(),
            "timezone": timezone,
            "base_currency": "USD",
            "api_provider": "fallback-enhanced",
            "data_quality": "Simulated",
            "note": f"Last successful API: {self.last_successful_api or 'None'}"
        }

class FXPredictor:
    """FX予測エンジン（Live API強化版）"""
    
    def __init__(self):
        self.currency_pairs = ["USD/JPY", "EUR/JPY", "EUR/USD"]
        self.data_provider = EnhancedFXDataProvider()
        self.business_calc = BusinessDayCalculator()
        self.timezone_manager = TimezoneManager()
        
        self.base_rates = {
            "USD/JPY": 147.49,
            "EUR/JPY": 173.16,
            "EUR/USD": 1.174
        }
    
    def get_current_rate(self, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """現在レート取得（強化版）"""
        return self.data_provider.get_real_fx_rate(pair, timezone)
    
    def calculate_technical_indicators(self, rates: List[float]) -> Dict[str, float]:
        """テクニカル指標計算"""
        if len(rates) < 5:
            rates = [self.base_rates["USD/JPY"]] * 5
            
        ma5 = sum(rates[-5:]) / 5
        ma10 = sum(rates[-10:]) / min(10, len(rates))
        
        gains = []
        losses = []
        for i in range(1, len(rates)):
            change = rates[i] - rates[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-14:]) / min(14, len(gains)) if gains else 0.01
        avg_loss = sum(losses[-14:]) / min(14, len(losses)) if losses else 0.01
        rs = avg_gain / avg_loss if avg_loss != 0 else 1
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "ma5": round(ma5, 4),
            "ma10": round(ma10, 4),
            "rsi": round(rsi, 2)
        }
    
    def predict_rate(self, pair: str, days_ahead: int = 1, use_business_days: bool = False, 
                    timezone: str = "UTC", country: str = "JP") -> Dict[str, Any]:
        """レート予測（強化版）"""
        
        # 現在レート取得
        current_data = self.get_current_rate(pair, timezone)
        current_rate = current_data["rate"]
        
        # 営業日計算
        current_date = datetime.date.today()
        if use_business_days and DATEUTIL_AVAILABLE:
            target_date = self.business_calc.add_business_days(current_date, days_ahead, country)
            actual_days = (target_date - current_date).days
        else:
            target_date = current_date + datetime.timedelta(days=days_ahead)
            actual_days = days_ahead
        
        # 過去データシミュレーション
        historical_rates = []
        base_rate = current_rate
        for i in range(30, 0, -1):
            variation = random.uniform(-0.008, 0.008)
            rate = base_rate * (1 + variation)
            historical_rates.append(rate)
            base_rate = rate * 0.999
        
        historical_rates[-1] = current_rate
        
        # テクニカル指標計算
        indicators = self.calculate_technical_indicators(historical_rates)
        
        # 予測計算
        trend_factor = 1.0
        if indicators["ma5"] > indicators["ma10"]:
            trend_factor = 1.0005
        elif indicators["ma5"] < indicators["ma10"]:
            trend_factor = 0.9995
            
        if indicators["rsi"] > 70:
            trend_factor *= 0.9995
        elif indicators["rsi"] < 30:
            trend_factor *= 1.0005
        
        uncertainty_factor = 1 + (actual_days * 0.001)
        if use_business_days:
            uncertainty_factor *= 0.95
        
        volatility = random.uniform(-0.003, 0.003) * uncertainty_factor
        predicted_rate = current_rate * (trend_factor ** actual_days) * (1 + volatility)
        
        # 信頼度計算
        base_confidence = max(70, 90 - (actual_days * 2))
        if use_business_days:
            base_confidence += 5
        if current_data["source"] == "Live API":
            base_confidence += 10  # Live APIデータは大幅信頼度向上
        confidence = min(95, base_confidence)
        
        return {
            "current_rate": current_rate,
            "current_data_source": current_data["source"],
            "predicted_rate": round(predicted_rate, 4),
            "change": round(predicted_rate - current_rate, 4),
            "change_percent": round((predicted_rate - current_rate) / current_rate * 100, 2),
            "confidence": confidence,
            "indicators": indicators,
            "days_ahead": days_ahead,
            "actual_days": actual_days,
            "target_date": target_date.isoformat(),
            "use_business_days": use_business_days,
            "timezone": timezone,
            "data_timestamp": current_data["timestamp"],
            "localized_timestamp": current_data.get("localized_timestamp"),
            "market_info": self._get_market_info(pair, timezone),
            "api_provider": current_data.get("api_provider", "unknown"),
            "data_quality": current_data.get("data_quality", "unknown")
        }
    
    def _get_market_info(self, pair: str, timezone: str) -> Dict[str, Any]:
        """市場情報取得"""
        if not DATEUTIL_AVAILABLE:
            return {"status": "unavailable"}
        
        try:
            if "JPY" in pair:
                primary_market = "Tokyo"
            elif "EUR" in pair:
                primary_market = "London"
            elif "USD" in pair:
                primary_market = "New_York"
            else:
                primary_market = "London"
            
            is_open = self.timezone_manager.is_market_open(primary_market)
            
            return {
                "primary_market": primary_market,
                "is_market_open": is_open,
                "market_status": "Open" if is_open else "Closed"
            }
        except Exception:
            return {"status": "error"}
    
    def predict_multi_day(self, pair: str, days: int = 10, use_business_days: bool = False,
                         timezone: str = "UTC", country: str = "JP") -> List[Dict[str, Any]]:
        """複数日予測"""
        predictions = []
        for day in range(1, days + 1):
            prediction = self.predict_rate(pair, day, use_business_days, timezone, country)
            predictions.append(prediction)
        return predictions

# WebサーバーとHTMLテンプレートは同じ構造を維持
class FXWebServer:
    """FXWebサーバー（Live API版）"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.predictor = FXPredictor()
        
    def get_html_template(self) -> str:
        """HTMLテンプレート（Live API強化版）"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX予測システム - Phase 2.2 Live API Edition</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #2196F3, #21CBF3);
            color: white;
            text-align: center;
            padding: 30px;
            position: relative;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .phase-badge {
            position: absolute;
            top: 15px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .feature-badges {
            margin: 20px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
        }
        
        .feature-badge {
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .feature-badge.live-api { background: rgba(76, 175, 80, 0.3); }
        .feature-badge.business-days { background: rgba(255, 152, 0, 0.3); }
        .feature-badge.timezone { background: rgba(156, 39, 176, 0.3); }
        .feature-badge.enhanced { background: rgba(255, 87, 34, 0.3); }
        
        .content { padding: 30px; }
        
        .live-api-notice {
            background: linear-gradient(135deg, #e8f5e8, #f0f8f0);
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 25px;
        }
        
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .control-group {
            display: flex;
            flex-direction: column;
        }
        
        .control-group label {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }
        
        select, input {
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #2196F3;
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
        }
        
        .checkbox-group input[type="checkbox"] { width: auto; }
        
        button {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .loading.show { display: block; }
        
        .results { margin-top: 30px; }
        
        .prediction-card {
            background: #f8f9fa;
            border-left: 5px solid #2196F3;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        
        .prediction-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .currency-pair {
            font-size: 1.5em;
            font-weight: bold;
            color: #2196F3;
        }
        
        .confidence {
            background: #4CAF50;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        .phase2-2-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .feature-info {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .feature-info h4 {
            color: #2196F3;
            margin-bottom: 8px;
        }
        
        .rate-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .rate-item {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .rate-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .rate-value {
            font-size: 1.4em;
            font-weight: bold;
            color: #333;
        }
        
        .rate-change {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .rate-change.positive { color: #4CAF50; }
        .rate-change.negative { color: #f44336; }
        
        .indicators {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
        }
        
        .indicator {
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .indicator-label {
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .indicator-value {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }
        
        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }
        
        .disclaimer {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        @media (max-width: 768px) {
            .controls { grid-template-columns: 1fr; }
            .phase2-2-features { grid-template-columns: 1fr; }
            .rate-info { grid-template-columns: 1fr; }
            .indicators { grid-template-columns: repeat(3, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="phase-badge">Live API 2.2</div>
            <h1>🚀 FX予測システム</h1>
            <p>Live API統合・営業日計算・タイムゾーン対応・次世代為替予測</p>
            <div class="feature-badges">
                <span class="feature-badge live-api">📡 Live API強化</span>
                <span class="feature-badge business-days">📅 営業日計算</span>
                <span class="feature-badge timezone">🌍 タイムゾーン対応</span>
                <span class="feature-badge enhanced">⚡ 接続強化</span>
            </div>
        </div>
        
        <div class="content">
            <div class="live-api-notice">
                <h3>📡 Live API強化版の特徴</h3>
                <ul>
                    <li><strong>🔄 4つのAPI統合:</strong> exchangerate-api, exchangerate.host, fxratesapi, vatcomply</li>
                    <li><strong>⚡ 自動リトライ:</strong> タイムアウト・接続エラー時の自動再試行</li>
                    <li><strong>🎯 確実なデータ取得:</strong> AWS App Runner環境で最適化</li>
                    <li><strong>✅ データ品質保証:</strong> リアルタイム検証とフォールバック</li>
                </ul>
            </div>
            
            <div class="disclaimer">
                <strong>⚠️ 重要な免責事項：</strong> この予測システムは教育・デモンストレーション目的で作成されています。
                実際の投資判断には使用しないでください。為替取引にはリスクが伴います。
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label for="currencyPair">通貨ペア</label>
                    <select id="currencyPair">
                        <option value="USD/JPY">USD/JPY (米ドル/円)</option>
                        <option value="EUR/JPY">EUR/JPY (ユーロ/円)</option>
                        <option value="EUR/USD">EUR/USD (ユーロ/米ドル)</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="predictionDays">予測日数</label>
                    <select id="predictionDays">
                        <option value="1">翌日予測</option>
                        <option value="3">3日間予測</option>
                        <option value="5">5日間予測</option>
                        <option value="7">1週間予測</option>
                        <option value="10">10日間予測</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label for="timezone">タイムゾーン</label>
                    <select id="timezone">
                        <option value="UTC">UTC (協定世界時)</option>
                        <option value="Tokyo">Tokyo (JST)</option>
                        <option value="London">London (GMT)</option>
                        <option value="New_York">New York (EST)</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label>予測オプション</label>
                    <div class="checkbox-group">
                        <input type="checkbox" id="useBusinessDays">
                        <label for="useBusinessDays">営業日のみで計算</label>
                    </div>
                </div>
                
                <div class="control-group">
                    <label>&nbsp;</label>
                    <button onclick="makePrediction()" id="predictBtn">
                        📈 Live API予測実行
                    </button>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <h3>🔄 Live API取得中...</h3>
                <p>複数APIから最新データを取得・分析しています</p>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <div class="footer">
            <p>© 2024 FX Prediction System - Phase 2.2 Live API Edition | Real-time Data Integration</p>
        </div>
    </div>

    <script>
        async function makePrediction() {
            const currencyPair = document.getElementById('currencyPair').value;
            const predictionDays = parseInt(document.getElementById('predictionDays').value);
            const timezone = document.getElementById('timezone').value;
            const useBusinessDays = document.getElementById('useBusinessDays').checked;
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const predictBtn = document.getElementById('predictBtn');
            
            loading.classList.add('show');
            results.innerHTML = '';
            predictBtn.disabled = true;
            predictBtn.textContent = 'Live API取得中...';
            
            try {
                let url;
                if (predictionDays === 1) {
                    url = `/api/predict?pair=${encodeURIComponent(currencyPair)}&days=${predictionDays}&timezone=${timezone}&use_business_days=${useBusinessDays}`;
                } else {
                    url = `/api/predict_multi?pair=${encodeURIComponent(currencyPair)}&days=${predictionDays}&timezone=${timezone}&use_business_days=${useBusinessDays}`;
                }
                
                const response = await fetch(url);
                
                if (!response.ok) {
                    throw new Error('予測の取得に失敗しました');
                }
                
                const data = await response.json();
                
                if (predictionDays === 1) {
                    displaySinglePrediction(data);
                } else {
                    displayMultiDayPrediction(data);
                }
                
            } catch (error) {
                results.innerHTML = `
                    <div class="prediction-card" style="border-left-color: #f44336;">
                        <h3 style="color: #f44336;">❌ エラーが発生しました</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            } finally {
                loading.classList.remove('show');
                predictBtn.disabled = false;
                predictBtn.textContent = '📈 Live API予測実行';
            }
        }
        
        function displaySinglePrediction(data) {
            const results = document.getElementById('results');
            const changeClass = data.change >= 0 ? 'positive' : 'negative';
            const changeSymbol = data.change >= 0 ? '+' : '';
            
            const dataSourceIcon = data.current_data_source === 'Live API' ? '📡' : 
                                   data.current_data_source === 'High-Quality Simulation' ? '🔄' : '🔄';
            const dataSourceText = data.current_data_source || 'Unknown';
            
            results.innerHTML = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${document.getElementById('currencyPair').value}</div>
                        <div class="confidence">信頼度: ${data.confidence}%</div>
                    </div>
                    
                    <div class="phase2-2-features">
                        <div class="feature-info">
                            <h4>📡 データソース</h4>
                            <p>${dataSourceIcon} ${dataSourceText}</p>
                            ${data.api_provider ? `<small>API: ${data.api_provider}</small><br>` : ''}
                            ${data.data_quality ? `<small>品質: ${data.data_quality}</small><br>` : ''}
                            <small>取得時刻: ${data.localized_timestamp ? new Date(data.localized_timestamp).toLocaleString('ja-JP') : new Date(data.data_timestamp).toLocaleString('ja-JP')}</small>
                        </div>
                        
                        <div class="feature-info">
                            <h4>📅 予測日程</h4>
                            <p>目標日: ${data.target_date}</p>
                            <p>${data.use_business_days ? '営業日ベース' : '暦日ベース'}: ${data.days_ahead}日後</p>
                        </div>
                        
                        <div class="feature-info">
                            <h4>🌍 タイムゾーン</h4>
                            <p>${data.timezone}</p>
                        </div>
                    </div>
                    
                    <div class="rate-info">
                        <div class="rate-item">
                            <div class="rate-label">現在レート</div>
                            <div class="rate-value">${data.current_rate}</div>
                        </div>
                        
                        <div class="rate-item">
                            <div class="rate-label">予測レート</div>
                            <div class="rate-value">${data.predicted_rate}</div>
                        </div>
                        
                        <div class="rate-item">
                            <div class="rate-label">予想変動</div>
                            <div class="rate-change ${changeClass}">
                                ${changeSymbol}${data.change} (${changeSymbol}${data.change_percent}%)
                            </div>
                        </div>
                    </div>
                    
                    <div class="indicators">
                        <div class="indicator">
                            <div class="indicator-label">移動平均線(5日)</div>
                            <div class="indicator-value">${data.indicators.ma5}</div>
                        </div>
                        
                        <div class="indicator">
                            <div class="indicator-label">移動平均線(10日)</div>
                            <div class="indicator-value">${data.indicators.ma10}</div>
                        </div>
                        
                        <div class="indicator">
                            <div class="indicator-label">RSI</div>
                            <div class="indicator-value">${data.indicators.rsi}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function displayMultiDayPrediction(data) {
            // 複数日予測の表示（同様の構造）
            const results = document.getElementById('results');
            const currencyPair = document.getElementById('currencyPair').value;
            
            let html = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${currencyPair} - Live API複数日予測</div>
                        <div class="confidence">予測期間: ${data.length}日間</div>
                    </div>
                </div>
            `;
            
            results.innerHTML = html;
        }
        
        // 自動実行
        window.addEventListener('load', function() {
            setTimeout(makePrediction, 1000);
        });
    </script>
</body>
</html>
        """

class FXRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTPリクエストハンドラー（Live API版）"""
    
    def __init__(self, predictor, *args, **kwargs):
        self.predictor = predictor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            server = FXWebServer()
            html = server.get_html_template()
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path.startswith('/api/predict?'):
            self.handle_single_prediction()
        elif self.path.startswith('/api/predict_multi?'):
            self.handle_multi_prediction()
        else:
            self.send_error(404, "File not found")
    
    def handle_single_prediction(self):
        try:
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['1'])[0])
            timezone = params.get('timezone', ['UTC'])[0]
            use_business_days = params.get('use_business_days', ['false'])[0].lower() == 'true'
            country = params.get('country', ['JP'])[0]
            
            prediction = self.predictor.predict_rate(pair, days, use_business_days, timezone, country)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(prediction, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ API エラー: {e}")
            self.send_error(500, f"Prediction error: {str(e)}")
    
    def handle_multi_prediction(self):
        try:
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['10'])[0])
            timezone = params.get('timezone', ['UTC'])[0]
            use_business_days = params.get('use_business_days', ['false'])[0].lower() == 'true'
            country = params.get('country', ['JP'])[0]
            
            predictions = self.predictor.predict_multi_day(pair, days, use_business_days, timezone, country)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(predictions, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ 複数日予測エラー: {e}")
            self.send_error(500, f"Multi-prediction error: {str(e)}")
    
    def log_message(self, format, *args):
        message = f"{datetime.datetime.now().isoformat()} - {format % args}"
        print(message)

def create_handler(predictor):
    def handler(*args, **kwargs):
        return FXRequestHandler(predictor, *args, **kwargs)
    return handler

def main():
    """メイン実行関数（Live API強化版）"""
    try:
        port = int(os.environ.get('PORT', 8080))
        
        print(f"🚀 FX予測システム - Phase 2.2 Live API Edition 起動中...")
        print(f"📡 ポート: {port}")
        print(f"⏰ 起動時刻: {datetime.datetime.now().isoformat()}")
        
        if REQUESTS_AVAILABLE:
            print("✅ requests利用可能 - Live API機能フル稼働")
        else:
            print("⚠️ requests不可 - urllib fallback mode")
            
        if DATEUTIL_AVAILABLE:
            print("✅ python-dateutil利用可能 - 営業日・タイムゾーン機能フル稼働")
        else:
            print("⚠️ python-dateutil不可 - 基本日付処理モード")
        
        predictor = FXPredictor()
        print("✅ Live API統合予測エンジン初期化完了")
        
        # Live API機能テスト
        print("🧪 Live API統合テスト実行中...")
        test_prediction = predictor.predict_rate("USD/JPY", 1, timezone="Tokyo")
        print(f"🧪 テスト結果: USD/JPY = {test_prediction['predicted_rate']}")
        print(f"📊 データソース: {test_prediction['current_data_source']}")
        print(f"🔗 API プロバイダー: {test_prediction.get('api_provider', 'N/A')}")
        print(f"🏆 データ品質: {test_prediction.get('data_quality', 'N/A')}")
        print("=" * 50)
        
        handler = create_handler(predictor)
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 Live API サーバー起動完了: http://0.0.0.0:{port}")
            print("📡 複数API統合 - リアルタイムデータ取得準備完了")
            print("🔄 リクエスト待機中...")
            print("=" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Live API サーバー停止中...")
    except Exception as e:
        print(f"❌ Live API サーバーエラー: {e}")
        raise

if __name__ == "__main__":
    main()
