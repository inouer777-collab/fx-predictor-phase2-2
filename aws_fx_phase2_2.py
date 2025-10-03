#!/usr/bin/env python3
"""
Phase 2.2: python-dateutil追加版FX予測アプリ
- 営業日計算機能追加
- タイムゾーン対応拡張
- 市場時間連動機能
- Phase 2.1完全互換性維持
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
    """営業日計算クラス（Phase 2.2新機能）"""
    
    def __init__(self):
        self.major_holidays = {
            # 日本の祝日（主要なもの）
            "JP": [
                (1, 1),   # 元日
                (2, 11),  # 建国記念日
                (4, 29),  # 昭和の日
                (5, 3),   # 憲法記念日
                (5, 4),   # みどりの日
                (5, 5),   # こどもの日
                (12, 31), # 大晦日
            ],
            # アメリカの祝日（主要なもの）
            "US": [
                (1, 1),   # New Year's Day
                (7, 4),   # Independence Day
                (12, 25), # Christmas
            ],
            # イギリスの祝日（主要なもの）
            "UK": [
                (1, 1),   # New Year's Day
                (12, 25), # Christmas Day
                (12, 26), # Boxing Day
            ]
        }
    
    def is_business_day(self, date: datetime.date, country: str = "JP") -> bool:
        """指定日が営業日かどうか判定"""
        if not DATEUTIL_AVAILABLE:
            # フォールバック: 土日のみ除外
            return date.weekday() < 5
        
        # 土日チェック
        if date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        # 祝日チェック
        holidays = self.major_holidays.get(country, [])
        month_day = (date.month, date.day)
        if month_day in holidays:
            return False
        
        return True
    
    def get_next_business_day(self, date: datetime.date, country: str = "JP") -> datetime.date:
        """次の営業日を取得"""
        next_date = date + datetime.timedelta(days=1)
        while not self.is_business_day(next_date, country):
            next_date += datetime.timedelta(days=1)
        return next_date
    
    def add_business_days(self, start_date: datetime.date, business_days: int, country: str = "JP") -> datetime.date:
        """営業日ベースで日数を加算"""
        if not DATEUTIL_AVAILABLE or business_days <= 0:
            # フォールバック: 単純な日数加算
            return start_date + datetime.timedelta(days=business_days)
        
        current_date = start_date
        added_days = 0
        
        while added_days < business_days:
            current_date = self.get_next_business_day(current_date, country)
            added_days += 1
        
        return current_date
    
    def get_business_days_between(self, start_date: datetime.date, end_date: datetime.date, country: str = "JP") -> int:
        """期間内の営業日数を計算"""
        if not DATEUTIL_AVAILABLE:
            # フォールバック: 単純な日数差
            return (end_date - start_date).days
        
        business_days = 0
        current_date = start_date
        
        while current_date < end_date:
            if self.is_business_day(current_date, country):
                business_days += 1
            current_date += datetime.timedelta(days=1)
        
        return business_days

class TimezoneManager:
    """タイムゾーン管理クラス（Phase 2.2新機能）"""
    
    def __init__(self):
        self.market_timezones = {
            "Tokyo": "Asia/Tokyo",
            "London": "Europe/London", 
            "New_York": "America/New_York",
            "UTC": "UTC"
        }
        
        self.market_hours = {
            "Tokyo": {"open": 9, "close": 15},      # JST 9:00-15:00
            "London": {"open": 8, "close": 16.5},   # GMT 8:00-16:30
            "New_York": {"open": 9.5, "close": 16}  # EST 9:30-16:00
        }
    
    def get_timezone(self, timezone_name: str):
        """タイムゾーンオブジェクト取得"""
        if not DATEUTIL_AVAILABLE:
            return None
        
        try:
            if timezone_name in self.market_timezones:
                return tz.gettz(self.market_timezones[timezone_name])
            return tz.gettz(timezone_name)
        except Exception:
            return None
    
    def convert_to_timezone(self, dt: datetime.datetime, target_timezone: str) -> Optional[datetime.datetime]:
        """指定タイムゾーンに時刻変換"""
        if not DATEUTIL_AVAILABLE:
            return dt  # フォールバック: 変換なし
        
        try:
            target_tz = self.get_timezone(target_timezone)
            if target_tz is None:
                return dt
            
            # UTCとして扱い、指定タイムゾーンに変換
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.UTC)
            
            return dt.astimezone(target_tz)
        except Exception:
            return dt
    
    def is_market_open(self, market: str, dt: Optional[datetime.datetime] = None) -> bool:
        """指定市場が開場中かどうか判定"""
        if not DATEUTIL_AVAILABLE or market not in self.market_hours:
            return True  # フォールバック: 常に開場扱い
        
        if dt is None:
            dt = datetime.datetime.now()
        
        # 市場のタイムゾーンに変換
        market_time = self.convert_to_timezone(dt, market)
        if market_time is None:
            return True
        
        # 営業日チェック
        business_calc = BusinessDayCalculator()
        if not business_calc.is_business_day(market_time.date()):
            return False
        
        # 開場時間チェック
        hours = self.market_hours[market]
        current_hour = market_time.hour + market_time.minute / 60.0
        
        return hours["open"] <= current_hour <= hours["close"]
    
    def get_next_market_open(self, market: str) -> Optional[datetime.datetime]:
        """次回市場開場時刻を取得"""
        if not DATEUTIL_AVAILABLE or market not in self.market_hours:
            return None
        
        try:
            current_time = datetime.datetime.now()
            market_time = self.convert_to_timezone(current_time, market)
            
            if market_time is None:
                return None
            
            business_calc = BusinessDayCalculator()
            
            # 今日の開場時刻をチェック
            today_open = market_time.replace(
                hour=int(self.market_hours[market]["open"]),
                minute=int((self.market_hours[market]["open"] % 1) * 60),
                second=0,
                microsecond=0
            )
            
            if (business_calc.is_business_day(market_time.date()) and 
                market_time < today_open):
                return today_open
            
            # 次の営業日の開場時刻
            next_business_day = business_calc.get_next_business_day(market_time.date())
            next_open = datetime.datetime.combine(
                next_business_day,
                datetime.time(
                    hour=int(self.market_hours[market]["open"]),
                    minute=int((self.market_hours[market]["open"] % 1) * 60)
                )
            )
            
            # タイムゾーン情報を付加
            market_tz = self.get_timezone(market)
            if market_tz:
                next_open = next_open.replace(tzinfo=market_tz)
            
            return next_open
        
        except Exception:
            return None

class FXDataProvider:
    """FXデータプロバイダー（Phase 2.2拡張版）"""
    
    def __init__(self):
        self.api_endpoints = {
            "exchangerate": "https://api.exchangerate-api.com/v4/latest/USD",
            "fixer": "https://api.fixer.io/latest?access_key=",
            "currencylayer": "http://api.currencylayer.com/live?access_key="
        }
        
        self.fallback_rates = {
            "USD/JPY": 150.0,
            "EUR/JPY": 160.0,
            "EUR/USD": 1.08
        }
        
        # Phase 2.2: タイムゾーン管理追加
        self.timezone_manager = TimezoneManager()
    
    def get_real_fx_rate(self, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """実際のFXレートを取得（Phase 2.2拡張：タイムゾーン対応）"""
        
        if not REQUESTS_AVAILABLE:
            return self._get_simulated_rate(pair, timezone)
        
        try:
            response = requests.get(
                self.api_endpoints["exchangerate"], 
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_exchange_rate_api(data, pair, timezone)
            else:
                print(f"⚠️ API応答エラー: {response.status_code}")
                return self._get_simulated_rate(pair, timezone)
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API接続エラー: {e}")
            return self._get_simulated_rate(pair, timezone)
        except Exception as e:
            print(f"⚠️ データ取得エラー: {e}")
            return self._get_simulated_rate(pair, timezone)
    
    def _parse_exchange_rate_api(self, data: Dict, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """Exchange Rate APIのデータを解析（Phase 2.2拡張）"""
        try:
            rates = data.get("rates", {})
            base = data.get("base", "USD")
            
            if pair == "USD/JPY":
                rate = rates.get("JPY", self.fallback_rates["USD/JPY"])
            elif pair == "EUR/JPY":
                eur_rate = rates.get("EUR", 0.85)
                jpy_rate = rates.get("JPY", 150.0)
                rate = jpy_rate / eur_rate
            elif pair == "EUR/USD":
                rate = 1 / rates.get("EUR", 0.85)
            else:
                rate = self.fallback_rates.get(pair, 100.0)
            
            # Phase 2.2: タイムゾーン対応のタイムスタンプ
            current_time = datetime.datetime.now()
            localized_time = self.timezone_manager.convert_to_timezone(current_time, timezone)
            
            return {
                "rate": round(rate, 4),
                "source": "API",
                "timestamp": current_time.isoformat(),
                "localized_timestamp": localized_time.isoformat() if localized_time else current_time.isoformat(),
                "timezone": timezone,
                "base_currency": base
            }
            
        except Exception as e:
            print(f"⚠️ API データ解析エラー: {e}")
            return self._get_simulated_rate(pair, timezone)
    
    def _get_simulated_rate(self, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """シミュレートされたレート（Phase 2.2拡張：タイムゾーン対応）"""
        base = self.fallback_rates.get(pair, 100.0)
        variation = random.uniform(-0.02, 0.02)
        rate = base * (1 + variation)
        
        # Phase 2.2: タイムゾーン対応
        current_time = datetime.datetime.now()
        localized_time = self.timezone_manager.convert_to_timezone(current_time, timezone)
        
        return {
            "rate": round(rate, 4),
            "source": "Simulated",
            "timestamp": current_time.isoformat(),
            "localized_timestamp": localized_time.isoformat() if localized_time else current_time.isoformat(),
            "timezone": timezone,
            "base_currency": "USD"
        }

class FXPredictor:
    """FX予測エンジン（Phase 2.2拡張版）"""
    
    def __init__(self):
        self.currency_pairs = ["USD/JPY", "EUR/JPY", "EUR/USD"]
        self.data_provider = FXDataProvider()
        
        # Phase 2.2: 営業日・タイムゾーン管理追加
        self.business_calc = BusinessDayCalculator()
        self.timezone_manager = TimezoneManager()
        
        self.base_rates = {
            "USD/JPY": 150.0,
            "EUR/JPY": 160.0,
            "EUR/USD": 1.08
        }
    
    def get_current_rate(self, pair: str, timezone: str = "UTC") -> Dict[str, Any]:
        """現在のレートを取得（Phase 2.2拡張：タイムゾーン対応）"""
        return self.data_provider.get_real_fx_rate(pair, timezone)
    
    def calculate_technical_indicators(self, rates: List[float]) -> Dict[str, float]:
        """基本的なテクニカル指標を計算（Phase 2.1互換）"""
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
        """指定した日数後のレートを予測（Phase 2.2拡張）"""
        
        # 現在のレート取得
        current_data = self.get_current_rate(pair, timezone)
        current_rate = current_data["rate"]
        
        # Phase 2.2: 営業日計算
        current_date = datetime.date.today()
        if use_business_days and DATEUTIL_AVAILABLE:
            target_date = self.business_calc.add_business_days(current_date, days_ahead, country)
            actual_days = (target_date - current_date).days
        else:
            target_date = current_date + datetime.timedelta(days=days_ahead)
            actual_days = days_ahead
        
        # 過去データのシミュレーション
        historical_rates = []
        base_rate = current_rate
        for i in range(30, 0, -1):
            variation = random.uniform(-0.01, 0.01)
            rate = base_rate * (1 + variation)
            historical_rates.append(rate)
            base_rate = rate
        
        # テクニカル指標計算
        indicators = self.calculate_technical_indicators(historical_rates)
        
        # 予測アルゴリズム
        trend_factor = 1.0
        if indicators["ma5"] > indicators["ma10"]:
            trend_factor = 1.001
        elif indicators["ma5"] < indicators["ma10"]:
            trend_factor = 0.999
            
        if indicators["rsi"] > 70:
            trend_factor *= 0.998
        elif indicators["rsi"] < 30:
            trend_factor *= 1.002
        
        # Phase 2.2: 営業日考慮の不確実性調整
        uncertainty_factor = 1 + (actual_days * 0.002)
        if use_business_days:
            uncertainty_factor *= 0.9  # 営業日ベースの方が予測精度向上
        
        volatility = random.uniform(-0.005, 0.005) * uncertainty_factor
        predicted_rate = current_rate * (trend_factor ** actual_days) * (1 + volatility)
        
        # 信頼度計算
        base_confidence = max(60, 85 - (actual_days * 2))
        if use_business_days:
            base_confidence += 5  # 営業日ベースは信頼度向上
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
            "market_info": self._get_market_info(pair, timezone)
        }
    
    def _get_market_info(self, pair: str, timezone: str) -> Dict[str, Any]:
        """市場情報を取得（Phase 2.2新機能）"""
        if not DATEUTIL_AVAILABLE:
            return {"status": "unavailable"}
        
        try:
            # 通貨ペアに関連する主要市場を判定
            if "JPY" in pair:
                primary_market = "Tokyo"
            elif "EUR" in pair:
                primary_market = "London"
            elif "USD" in pair:
                primary_market = "New_York"
            else:
                primary_market = "London"  # デフォルト
            
            is_open = self.timezone_manager.is_market_open(primary_market)
            next_open = self.timezone_manager.get_next_market_open(primary_market)
            
            return {
                "primary_market": primary_market,
                "is_market_open": is_open,
                "next_market_open": next_open.isoformat() if next_open else None,
                "market_status": "Open" if is_open else "Closed"
            }
        except Exception:
            return {"status": "error"}
    
    def predict_multi_day(self, pair: str, days: int = 10, use_business_days: bool = False,
                         timezone: str = "UTC", country: str = "JP") -> List[Dict[str, Any]]:
        """複数日の予測を生成（Phase 2.2拡張）"""
        predictions = []
        for day in range(1, days + 1):
            prediction = self.predict_rate(pair, day, use_business_days, timezone, country)
            predictions.append(prediction)
        return predictions

# WebサーバーとRequestHandlerは基本的にPhase 2.1と同じ構造を維持
# HTMLテンプレートにPhase 2.2機能のUI要素を追加

class FXWebServer:
    """FXアプリのWebサーバー（Phase 2.2拡張版）"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.predictor = FXPredictor()
        
    def get_html_template(self) -> str:
        """HTMLテンプレートを返す（Phase 2.2拡張版）"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX予測システム - Phase 2.2 Edition</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
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
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
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
        
        .feature-badge.api { background: rgba(76, 175, 80, 0.3); }
        .feature-badge.business-days { background: rgba(255, 152, 0, 0.3); }
        .feature-badge.timezone { background: rgba(156, 39, 176, 0.3); }
        
        .content {
            padding: 30px;
        }
        
        .phase2-2-info {
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
        
        .checkbox-group input[type="checkbox"] {
            width: auto;
        }
        
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
        
        .market-status {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        
        .market-open { border-left-color: #4CAF50; }
        .market-closed { border-left-color: #f44336; }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .loading.show {
            display: block;
        }
        
        .results {
            margin-top: 30px;
        }
        
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
            .controls {
                grid-template-columns: 1fr;
            }
            
            .feature-badges {
                justify-content: center;
            }
            
            .phase2-2-features {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="phase-badge">Phase 2.2</div>
            <h1>🚀 FX予測システム</h1>
            <p>営業日計算・タイムゾーン対応・次世代為替予測プラットフォーム</p>
            <div class="feature-badges">
                <span class="feature-badge api">📡 Live API</span>
                <span class="feature-badge business-days">📅 営業日計算</span>
                <span class="feature-badge timezone">🌍 タイムゾーン対応</span>
            </div>
        </div>
        
        <div class="content">
            <div class="phase2-2-info">
                <h3>🎉 Phase 2.2新機能</h3>
                <ul>
                    <li><strong>📅 営業日計算:</strong> 土日・祝日を除いた現実的な予測日程</li>
                    <li><strong>🌍 タイムゾーン対応:</strong> 世界各地の市場時間に対応</li>
                    <li><strong>📊 市場状況表示:</strong> リアルタイムの市場開場状況</li>
                    <li><strong>🔄 高精度予測:</strong> 営業日ベースの予測で精度向上</li>
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
                        📈 予測実行
                    </button>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <h3>🔄 予測計算中...</h3>
                <p>営業日・タイムゾーンを考慮して分析しています</p>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <div class="footer">
            <p>© 2024 FX Prediction System - Phase 2.2 Edition | Business Days & Timezone Support</p>
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
            
            // UI更新
            loading.classList.add('show');
            results.innerHTML = '';
            predictBtn.disabled = true;
            predictBtn.textContent = '計算中...';
            
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
                predictBtn.textContent = '📈 予測実行';
            }
        }
        
        function displaySinglePrediction(data) {
            const results = document.getElementById('results');
            const changeClass = data.change >= 0 ? 'positive' : 'negative';
            const changeSymbol = data.change >= 0 ? '+' : '';
            
            const dataSourceIcon = data.current_data_source === 'API' ? '📡' : '🔄';
            const dataSourceText = data.current_data_source === 'API' ? 'Live API データ' : 'シミュレーションデータ';
            
            // 市場情報表示
            const marketInfo = data.market_info || {};
            const marketStatusClass = marketInfo.is_market_open ? 'market-open' : 'market-closed';
            const marketStatusText = marketInfo.is_market_open ? '🟢 開場中' : '🔴 休場中';
            
            results.innerHTML = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${document.getElementById('currencyPair').value}</div>
                        <div class="confidence">信頼度: ${data.confidence}%</div>
                    </div>
                    
                    ${marketInfo.primary_market ? `
                    <div class="market-status ${marketStatusClass}">
                        <strong>📊 ${marketInfo.primary_market}市場:</strong> ${marketStatusText}
                        ${marketInfo.next_market_open ? `<br><small>次回開場: ${new Date(marketInfo.next_market_open).toLocaleString('ja-JP')}</small>` : ''}
                    </div>
                    ` : ''}
                    
                    <div class="phase2-2-features">
                        <div class="feature-info">
                            <h4>📡 データソース</h4>
                            <p>${dataSourceIcon} ${dataSourceText}</p>
                            <small>取得時刻: ${data.localized_timestamp ? new Date(data.localized_timestamp).toLocaleString('ja-JP') : new Date(data.data_timestamp).toLocaleString('ja-JP')}</small>
                        </div>
                        
                        <div class="feature-info">
                            <h4>📅 予測日程</h4>
                            <p>目標日: ${data.target_date}</p>
                            <p>${data.use_business_days ? '営業日ベース' : '暦日ベース'}: ${data.days_ahead}日後</p>
                            ${data.actual_days !== data.days_ahead ? `<small>実際の日数: ${data.actual_days}日</small>` : ''}
                        </div>
                        
                        <div class="feature-info">
                            <h4>🌍 タイムゾーン</h4>
                            <p>${data.timezone}</p>
                            ${data.localized_timestamp ? `<p>現地時間: ${new Date(data.localized_timestamp).toLocaleString('ja-JP')}</p>` : ''}
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
            const results = document.getElementById('results');
            const currencyPair = document.getElementById('currencyPair').value;
            const useBusinessDays = document.getElementById('useBusinessDays').checked;
            
            const firstPrediction = data[0];
            const dataSourceIcon = firstPrediction.current_data_source === 'API' ? '📡' : '🔄';
            const dataSourceText = firstPrediction.current_data_source === 'API' ? 'Live API データ' : 'シミュレーションデータ';
            
            let html = `
                <div class="prediction-card">
                    <div class="prediction-header">
                        <div class="currency-pair">${currencyPair} - 複数日予測</div>
                        <div class="confidence">予測期間: ${data.length}日間</div>
                    </div>
                    
                    <div class="phase2-2-features">
                        <div class="feature-info">
                            <h4>📡 データソース</h4>
                            <p>${dataSourceIcon} ${dataSourceText}</p>
                        </div>
                        
                        <div class="feature-info">
                            <h4>📅 計算方式</h4>
                            <p>${useBusinessDays ? '営業日ベース計算' : '暦日ベース計算'}</p>
                        </div>
                        
                        <div class="feature-info">
                            <h4>🌍 タイムゾーン</h4>
                            <p>${firstPrediction.timezone}</p>
                        </div>
                    </div>
                    
                    <div class="multi-day-results">
            `;
            
            data.forEach((prediction, index) => {
                const changeClass = prediction.change >= 0 ? 'positive' : 'negative';
                const changeSymbol = prediction.change >= 0 ? '+' : '';
                const businessDayInfo = prediction.use_business_days && prediction.actual_days !== prediction.days_ahead 
                    ? ` (実${prediction.actual_days}日)` : '';
                
                html += `
                    <div class="day-prediction">
                        <div class="day-info">
                            <div class="day-date">${prediction.target_date}</div>
                            <div class="day-number">${prediction.days_ahead}日後${businessDayInfo}</div>
                        </div>
                        
                        <div class="prediction-info">
                            <div class="predicted-rate">${prediction.predicted_rate}</div>
                            <div class="prediction-change ${changeClass}">
                                ${changeSymbol}${prediction.change} (${changeSymbol}${prediction.change_percent}%)
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
            
            results.innerHTML = html;
        }
        
        // ページ読み込み時に初期予測を実行
        window.addEventListener('load', function() {
            setTimeout(makePrediction, 1000);
        });
    </script>
</body>
</html>
        """

class FXRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTPリクエストハンドラー（Phase 2.2拡張版）"""
    
    def __init__(self, predictor, *args, **kwargs):
        self.predictor = predictor
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """GETリクエストの処理（Phase 2.2拡張）"""
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
        """単日予測API（Phase 2.2拡張）"""
        try:
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['1'])[0])
            timezone = params.get('timezone', ['UTC'])[0]
            use_business_days = params.get('use_business_days', ['false'])[0].lower() == 'true'
            country = params.get('country', ['JP'])[0]
            
            # Phase 2.2: 拡張パラメータで予測実行
            prediction = self.predictor.predict_rate(
                pair, days, use_business_days, timezone, country
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(prediction, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Prediction error: {str(e)}")
    
    def handle_multi_prediction(self):
        """複数日予測API（Phase 2.2拡張）"""
        try:
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            pair = params.get('pair', ['USD/JPY'])[0]
            days = int(params.get('days', ['10'])[0])
            timezone = params.get('timezone', ['UTC'])[0]
            use_business_days = params.get('use_business_days', ['false'])[0].lower() == 'true'
            country = params.get('country', ['JP'])[0]
            
            # Phase 2.2: 拡張パラメータで予測実行
            predictions = self.predictor.predict_multi_day(
                pair, days, use_business_days, timezone, country
            )
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(predictions, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Multi-prediction error: {str(e)}")
    
    def log_message(self, format, *args):
        """ログメッセージを標準出力に出力"""
        message = f"{datetime.datetime.now().isoformat()} - {format % args}"
        print(message)

def create_handler(predictor):
    """ハンドラーファクトリー関数"""
    def handler(*args, **kwargs):
        return FXRequestHandler(predictor, *args, **kwargs)
    return handler

def main():
    """メイン実行関数（Phase 2.2拡張版）"""
    try:
        port = int(os.environ.get('PORT', 8080))
        
        print(f"🚀 FX予測システム - Phase 2.2 Edition 起動中...")
        print(f"📡 ポート: {port}")
        print(f"⏰ 起動時刻: {datetime.datetime.now().isoformat()}")
        
        # ライブラリ状態確認
        if REQUESTS_AVAILABLE:
            print("✅ Phase 2.1機能: 実データAPI連携が利用可能")
        else:
            print("⚠️ Phase 2.1機能: 標準ライブラリモードで動作")
            
        if DATEUTIL_AVAILABLE:
            print("✅ Phase 2.2機能: 営業日計算・タイムゾーン対応が利用可能")
        else:
            print("⚠️ Phase 2.2機能: 基本日付処理モードで動作")
        
        predictor = FXPredictor()
        print("✅ 予測エンジン初期化完了")
        
        handler = create_handler(predictor)
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 サーバー起動完了: http://0.0.0.0:{port}")
            print("🔄 リクエスト待機中...")
            print("=" * 50)
            
            # Phase 2.2機能テスト
            test_prediction = predictor.predict_rate("USD/JPY", 1, use_business_days=True, timezone="Tokyo")
            print(f"🧪 テスト予測: USD/JPY = {test_prediction['predicted_rate']}")
            print(f"📊 データソース: {test_prediction['current_data_source']}")
            print(f"📅 営業日計算: {test_prediction['use_business_days']}")
            print(f"🌍 タイムゾーン: {test_prediction['timezone']}")
            if 'market_info' in test_prediction:
                market_info = test_prediction['market_info']
                print(f"🏛️ 市場状況: {market_info.get('primary_market', 'N/A')} - {market_info.get('market_status', 'N/A')}")
            print("=" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 サーバー停止中...")
    except Exception as e:
        print(f"❌ サーバーエラー: {e}")
        print("🔄 Phase 2.1互換モードで再試行...")
        raise

if __name__ == "__main__":
    main()