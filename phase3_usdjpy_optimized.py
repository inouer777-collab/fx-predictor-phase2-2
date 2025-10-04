#!/usr/bin/env python3
"""
Phase 3.0 USDJPY最適化版 - ドル円相場専用デイトレードシステム
ドル円の特性に合わせた最適化パラメータとロジック

目標：ドル円相場で予測精度 70%+ を実現
FX特化機能：スプレッド考慮、時間帯別分析、ボラティリティ最適化
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class Phase3USDJPYSystem:
    def __init__(self):
        self.name = "Phase 3.0 USDJPY Optimized Trading System"
        self.symbol = "USDJPY=X"
        self.currency_pair = "USD/JPY"
        
        # ドル円特化パラメータ
        self.fx_params = {
            'macd_fast': 8,      # FX向け高速化
            'macd_slow': 21,     # FX向け調整
            'macd_signal': 5,    # より敏感な反応
            'bb_period': 15,     # FX向け短期化
            'bb_std': 1.8,       # ドル円ボラティリティ調整
            'rsi_period': 10,    # FX向け短期化
            'atr_period': 10,    # FX向け調整
            'spread_cost': 0.002 # ドル円スプレッド（0.2銭想定）
        }
        
        print(f"🚀 {self.name} 初期化完了")
        print(f"💱 対象通貨ペア: {self.currency_pair}")
        print(f"🔧 FX最適化パラメータ適用済み")
        
    def fetch_usdjpy_data(self, period="6mo"):
        """ドル円データ取得"""
        try:
            print(f"💱 {self.currency_pair} データ取得中...")
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                print(f"❌ {self.symbol} のデータが取得できませんでした")
                return None
                
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # ドル円特有の処理
            data = self._add_usdjpy_features(data)
            
            print(f"✅ データ取得完了: {len(data)} 日分")
            return data
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
            return None
    
    def _add_usdjpy_features(self, data):
        """ドル円特有の特徴量追加"""
        # 日本・米国市場時間の概念（UTCベース）
        data['Hour'] = data.index.hour
        
        # 主要取引時間帯分類
        data['Tokyo_Session'] = ((data['Hour'] >= 0) & (data['Hour'] < 9)).astype(int)
        data['London_Session'] = ((data['Hour'] >= 8) & (data['Hour'] < 17)).astype(int)
        data['NY_Session'] = ((data['Hour'] >= 13) & (data['Hour'] < 22)).astype(int)
        data['Overlap_Session'] = ((data['Hour'] >= 13) & (data['Hour'] < 17)).astype(int)
        
        # ドル円レンジ分析
        data['Daily_Range'] = data['High'] - data['Low']
        data['Daily_Range_Pct'] = data['Daily_Range'] / data['Close'] * 100
        
        return data
    
    def calculate_fx_optimized_indicators(self, data):
        """FX最適化指標計算"""
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        indicators = {}
        params = self.fx_params
        
        # FX最適化MACD
        ema_fast = close.ewm(span=params['macd_fast']).mean()
        ema_slow = close.ewm(span=params['macd_slow']).mean()
        indicators['MACD'] = ema_fast - ema_slow
        indicators['MACD_Signal'] = indicators['MACD'].ewm(span=params['macd_signal']).mean()
        indicators['MACD_Histogram'] = indicators['MACD'] - indicators['MACD_Signal']
        
        # FX最適化ボリンジャーバンド
        sma_bb = close.rolling(window=params['bb_period']).mean()
        std_bb = close.rolling(window=params['bb_period']).std()
        indicators['BB_Upper'] = sma_bb + (std_bb * params['bb_std'])
        indicators['BB_Middle'] = sma_bb
        indicators['BB_Lower'] = sma_bb - (std_bb * params['bb_std'])
        indicators['BB_Width'] = indicators['BB_Upper'] - indicators['BB_Lower']
        indicators['BB_Position'] = (close - indicators['BB_Lower']) / indicators['BB_Width']
        
        # FX最適化RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
        rs = gain / loss
        indicators['RSI'] = 100 - (100 / (1 + rs))
        
        # FX最適化ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators['ATR'] = true_range.rolling(window=params['atr_period']).mean()
        indicators['ATR_Pct'] = indicators['ATR'] / close * 100
        
        # FX特化移動平均
        indicators['EMA_5'] = close.ewm(span=5).mean()
        indicators['EMA_13'] = close.ewm(span=13).mean()
        indicators['EMA_34'] = close.ewm(span=34).mean()
        
        # モメンタム指標
        indicators['Price_Change_3'] = close.pct_change(3)
        indicators['Price_Change_5'] = close.pct_change(5)
        
        # ボラティリティ指標
        indicators['Volatility_10'] = close.rolling(window=10).std() / close.rolling(window=10).mean()
        
        return indicators
    
    def generate_fx_signals(self, data, indicators):
        """FX特化シグナル生成"""
        signals = pd.DataFrame(index=data.index)
        signals['Price'] = data['Close']
        signals['Signal'] = 0
        signals['Position'] = 0
        signals['Confidence'] = 0.0
        signals['FX_Strategy'] = ''
        signals['Session'] = ''
        
        close = data['Close']
        
        for i in range(50, len(signals)):
            
            # セッション判定
            session = self._identify_trading_session(data.iloc[i])
            signals['Session'].iloc[i] = session
            
            # FX特化分析
            fx_momentum = self._analyze_fx_momentum(i, indicators)
            fx_mean_reversion = self._analyze_fx_mean_reversion(i, indicators)
            fx_breakout = self._analyze_fx_breakout(i, data, indicators)
            fx_risk = self._analyze_fx_risk(i, data, indicators)
            
            # セッション別重み調整
            session_multiplier = self._get_session_multiplier(session)
            
            # 統合判定
            signal_decision = self._make_fx_decision(
                fx_momentum, fx_mean_reversion, fx_breakout, fx_risk, session_multiplier
            )
            
            signals['Signal'].iloc[i] = signal_decision['signal']
            signals['Position'].iloc[i] = signal_decision['position']
            signals['Confidence'].iloc[i] = signal_decision['confidence']
            signals['FX_Strategy'].iloc[i] = signal_decision['strategy']
        
        return signals
    
    def _identify_trading_session(self, row):
        """取引セッション識別"""
        if row['Tokyo_Session']:
            return 'Tokyo'
        elif row['Overlap_Session']:
            return 'Overlap'  # 最も活発
        elif row['London_Session']:
            return 'London'
        elif row['NY_Session']:
            return 'NY'
        else:
            return 'Quiet'
    
    def _get_session_multiplier(self, session):
        """セッション別重み"""
        multipliers = {
            'Overlap': 1.3,  # 最高活発度
            'London': 1.2,
            'NY': 1.1,
            'Tokyo': 1.0,
            'Quiet': 0.7    # 低活発度
        }
        return multipliers.get(session, 1.0)
    
    def _analyze_fx_momentum(self, i, indicators):
        """FXモメンタム分析"""
        score = 0
        signals = []
        
        # MACD トレンド
        if indicators['MACD'].iloc[i] > indicators['MACD_Signal'].iloc[i]:
            if indicators['MACD_Histogram'].iloc[i] > indicators['MACD_Histogram'].iloc[i-1]:
                score += 2
                signals.append('macd_strong_bull')
            else:
                score += 1
                signals.append('macd_bull')
        else:
            if indicators['MACD_Histogram'].iloc[i] < indicators['MACD_Histogram'].iloc[i-1]:
                score -= 2
                signals.append('macd_strong_bear')
            else:
                score -= 1
                signals.append('macd_bear')
        
        # EMA配列確認
        ema5 = indicators['EMA_5'].iloc[i]
        ema13 = indicators['EMA_13'].iloc[i]
        ema34 = indicators['EMA_34'].iloc[i]
        
        if ema5 > ema13 > ema34:
            score += 1
            signals.append('ema_bullish')
        elif ema5 < ema13 < ema34:
            score -= 1
            signals.append('ema_bearish')
        
        return {'score': score, 'signals': signals}
    
    def _analyze_fx_mean_reversion(self, i, indicators):
        """FX平均回帰分析"""
        score = 0
        signals = []
        
        rsi = indicators['RSI'].iloc[i]
        bb_pos = indicators['BB_Position'].iloc[i]
        
        # RSI極値判定（FX用）
        if rsi < 25:  # FX用しきい値
            score += 2
            signals.append('rsi_oversold')
        elif rsi > 75:
            score -= 2
            signals.append('rsi_overbought')
        elif 40 <= rsi <= 60:
            score += 0.5
            signals.append('rsi_neutral')
        
        # ボリンジャーバンド極値
        if bb_pos < 0.05:  # より厳格
            score += 2
            signals.append('bb_extreme_oversold')
        elif bb_pos > 0.95:
            score -= 2
            signals.append('bb_extreme_overbought')
        elif bb_pos < 0.2:
            score += 1
            signals.append('bb_oversold')
        elif bb_pos > 0.8:
            score -= 1
            signals.append('bb_overbought')
        
        return {'score': score, 'signals': signals}
    
    def _analyze_fx_breakout(self, i, data, indicators):
        """FXブレイクアウト分析"""
        score = 0
        signals = []
        
        # ATRベースのブレイクアウト
        atr_pct = indicators['ATR_Pct'].iloc[i]
        atr_avg = indicators['ATR_Pct'].rolling(window=20).mean().iloc[i]
        
        price_change_3 = indicators['Price_Change_3'].iloc[i]
        price_change_5 = indicators['Price_Change_5'].iloc[i]
        
        # ボラティリティ拡大での方向性確認
        if atr_pct > atr_avg * 1.2:  # 高ボラティリティ
            if price_change_3 > 0.005:  # 0.5%以上の上昇
                score += 1
                signals.append('upward_breakout')
            elif price_change_3 < -0.005:
                score -= 1
                signals.append('downward_breakout')
        
        # レンジブレイク判定
        daily_range_pct = data['Daily_Range_Pct'].iloc[i]
        range_avg = data['Daily_Range_Pct'].rolling(window=20).mean().iloc[i]
        
        if daily_range_pct > range_avg * 1.3:
            if price_change_5 > 0:
                score += 0.5
                signals.append('range_break_up')
            else:
                score -= 0.5
                signals.append('range_break_down')
        
        return {'score': score, 'signals': signals}
    
    def _analyze_fx_risk(self, i, data, indicators):
        """FXリスク分析"""
        score = 0
        signals = []
        
        # ボラティリティリスク
        volatility = indicators['Volatility_10'].iloc[i]
        vol_avg = indicators['Volatility_10'].rolling(window=50).mean().iloc[i]
        
        if volatility <= vol_avg * 1.1:  # 安定した市場
            score += 1
            signals.append('stable_market')
        elif volatility >= vol_avg * 1.5:  # 不安定な市場
            score -= 1
            signals.append('volatile_market')
        
        # セッション活発度
        session = self._identify_trading_session(data.iloc[i])
        if session in ['Overlap', 'London']:
            score += 0.5
            signals.append('active_session')
        elif session == 'Quiet':
            score -= 0.5
            signals.append('quiet_session')
        
        return {'score': score, 'signals': signals}
    
    def _make_fx_decision(self, momentum, mean_reversion, breakout, risk, session_multiplier):
        """FX統合判定"""
        # 各要素のスコア計算
        momentum_score = momentum['score']
        reversion_score = mean_reversion['score']
        breakout_score = breakout['score']
        risk_score = risk['score']
        
        # 戦略別判定
        trend_score = momentum_score + breakout_score
        counter_score = reversion_score
        
        # セッション調整
        total_trend = trend_score * session_multiplier
        total_counter = counter_score * session_multiplier
        total_risk = risk_score
        
        # 最終スコア
        final_score = total_trend + total_counter + total_risk
        
        # 全シグナル統合
        all_signals = (momentum['signals'] + mean_reversion['signals'] + 
                      breakout['signals'] + risk['signals'])
        
        # 判定しきい値（FX用に調整）
        strong_threshold = 2.5
        moderate_threshold = 1.5
        
        if final_score >= strong_threshold:
            return {
                'signal': 1,
                'position': 1,
                'confidence': min(final_score / 4, 1.0),
                'strategy': f"FX_BUY: {', '.join(all_signals[:3])}"
            }
        elif final_score <= -strong_threshold:
            return {
                'signal': -1,
                'position': -1,
                'confidence': min(abs(final_score) / 4, 1.0),
                'strategy': f"FX_SELL: {', '.join(all_signals[:3])}"
            }
        elif final_score >= moderate_threshold:
            return {
                'signal': 1,
                'position': 0.5,  # 部分ポジション
                'confidence': final_score / 4,
                'strategy': f"FX_WEAK_BUY: {', '.join(all_signals[:2])}"
            }
        elif final_score <= -moderate_threshold:
            return {
                'signal': -1,
                'position': -0.5,
                'confidence': abs(final_score) / 4,
                'strategy': f"FX_WEAK_SELL: {', '.join(all_signals[:2])}"
            }
        else:
            return {
                'signal': 0,
                'position': 0,
                'confidence': 0.0,
                'strategy': "FX_HOLD: Mixed signals"
            }
    
    def calculate_fx_performance(self, signals):
        """FX特化パフォーマンス計算"""
        # スプレッドコスト考慮
        spread_cost = self.fx_params['spread_cost']
        
        # リターン計算
        signals['Returns'] = signals['Price'].pct_change()
        signals['Gross_Strategy_Returns'] = signals['Position'].shift(1) * signals['Returns']
        
        # スプレッドコスト適用
        signals['Trade_Cost'] = 0.0
        position_changes = signals['Position'].diff().abs()
        signals['Trade_Cost'] = position_changes * spread_cost
        
        # ネットリターン
        signals['Net_Strategy_Returns'] = signals['Gross_Strategy_Returns'] - signals['Trade_Cost']
        
        # 累積リターン
        signals['Cumulative_Returns'] = (1 + signals['Net_Strategy_Returns'].fillna(0)).cumprod()
        
        # パフォーマンス統計
        strategy_trades = signals[signals['Net_Strategy_Returns'] != 0]
        
        if len(strategy_trades) == 0:
            return self._empty_fx_metrics()
        
        win_trades = strategy_trades[strategy_trades['Net_Strategy_Returns'] > 0]
        lose_trades = strategy_trades[strategy_trades['Net_Strategy_Returns'] < 0]
        
        # FX特化メトリクス
        metrics = {
            'Total_Return': (signals['Cumulative_Returns'].iloc[-1] - 1) * 100,
            'Gross_Return': (signals['Gross_Strategy_Returns'].sum() + 1) * 100 - 100,
            'Trading_Costs': signals['Trade_Cost'].sum() * 100,
            'Win_Rate': (len(win_trades) / len(strategy_trades)) * 100,
            'Total_Trades': len(signals[abs(signals['Position'].diff()) > 0]),
            'Profitable_Trades': len(win_trades),
            'Losing_Trades': len(lose_trades),
            'Avg_Win': win_trades['Net_Strategy_Returns'].mean() * 100 if len(win_trades) > 0 else 0,
            'Avg_Loss': lose_trades['Net_Strategy_Returns'].mean() * 100 if len(lose_trades) > 0 else 0,
            'Best_Trade': strategy_trades['Net_Strategy_Returns'].max() * 100,
            'Worst_Trade': strategy_trades['Net_Strategy_Returns'].min() * 100,
            'Profit_Factor': abs(win_trades['Net_Strategy_Returns'].sum() / lose_trades['Net_Strategy_Returns'].sum()) if len(lose_trades) > 0 else float('inf'),
            'Max_Drawdown': self._calculate_max_drawdown(signals['Cumulative_Returns']),
            'Sharpe_Ratio': self._calculate_sharpe_ratio(signals['Net_Strategy_Returns']),
            'Final_Portfolio_Value': signals['Cumulative_Returns'].iloc[-1]
        }
        
        return metrics
    
    def _empty_fx_metrics(self):
        """空のFXメトリクス"""
        return {
            'Total_Return': 0, 'Gross_Return': 0, 'Trading_Costs': 0,
            'Win_Rate': 0, 'Total_Trades': 0, 'Profitable_Trades': 0, 'Losing_Trades': 0,
            'Avg_Win': 0, 'Avg_Loss': 0, 'Best_Trade': 0, 'Worst_Trade': 0,
            'Profit_Factor': 0, 'Max_Drawdown': 0, 'Sharpe_Ratio': 0,
            'Final_Portfolio_Value': 1.0
        }
    
    def _calculate_max_drawdown(self, cumulative_returns):
        """最大ドローダウン計算"""
        rolling_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        return drawdown.min() * 100
    
    def _calculate_sharpe_ratio(self, returns):
        """シャープレシオ計算"""
        if returns.std() == 0:
            return 0
        return (returns.mean() / returns.std()) * np.sqrt(252)
    
    def run_usdjpy_analysis(self):
        """ドル円特化分析実行"""
        print(f"\n🚀 Phase 3.0 USDJPY最適化分析開始")
        print("=" * 70)
        
        # データ取得
        data = self.fetch_usdjpy_data()
        if data is None or len(data) < 100:
            print("❌ 分析に必要なデータが不足しています")
            return None
        
        # FX最適化指標計算
        print("📈 FX最適化指標計算中...")
        indicators = self.calculate_fx_optimized_indicators(data)
        
        # FXシグナル生成
        print("🎯 FX特化シグナル生成中...")
        signals = self.generate_fx_signals(data, indicators)
        
        # FXパフォーマンス評価
        print("📊 FX特化パフォーマンス分析中...")
        performance = self.calculate_fx_performance(signals)
        
        # 結果表示
        self._display_usdjpy_results(data, performance, signals)
        
        return {
            'performance': performance,
            'signals': signals,
            'data': data,
            'indicators': indicators
        }
    
    def _display_usdjpy_results(self, data, performance, signals):
        """ドル円結果表示"""
        print("\n🎉 Phase 3.0 USDJPY最適化分析結果")
        print("=" * 70)
        print(f"💱 通貨ペア: {self.currency_pair}")
        print(f"📅 分析期間: {data.index[0].strftime('%Y-%m-%d')} ～ {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"📈 総リターン(ネット): {performance['Total_Return']:.2f}%")
        print(f"📊 総リターン(グロス): {performance['Gross_Return']:.2f}%")
        print(f"💸 取引コスト: {performance['Trading_Costs']:.3f}%")
        print(f"🎯 予測精度: {performance['Win_Rate']:.1f}%")
        print(f"📋 総取引数: {performance['Total_Trades']}")
        print(f"✅ 利益取引: {performance['Profitable_Trades']}")
        print(f"❌ 損失取引: {performance['Losing_Trades']}")
        print(f"📈 平均利益: {performance['Avg_Win']:.3f}%")
        print(f"📉 平均損失: {performance['Avg_Loss']:.3f}%")
        print(f"🏆 最高取引: {performance['Best_Trade']:.3f}%")
        print(f"💥 最悪取引: {performance['Worst_Trade']:.3f}%")
        print(f"⚖️ プロフィットファクター: {performance['Profit_Factor']:.2f}")
        print(f"📉 最大ドローダウン: {performance['Max_Drawdown']:.2f}%")
        print(f"📊 シャープレシオ: {performance['Sharpe_Ratio']:.2f}")
        print(f"💰 最終ポートフォリオ価値: {performance['Final_Portfolio_Value']:.3f}")
        
        # FX精度評価
        win_rate = performance['Win_Rate']
        if win_rate >= 70:
            status = "🚀 FX目標達成"
        elif win_rate >= 60:
            status = "🎯 FX良好"
        elif win_rate >= 50:
            status = "⚡ FX改善中"
        else:
            status = "⚠️ FX要改善"
        
        print(f"\n🎯 FX予測精度評価: {status}")
        print(f"   現在の精度: {win_rate:.1f}%")
        print(f"   FX目標精度: 70%+")
        
        # 最新FXシグナル
        latest_signals = signals[signals['Signal'] != 0].tail(3)
        if len(latest_signals) > 0:
            print(f"\n📡 最新FXシグナル:")
            for date, row in latest_signals.iterrows():
                signal_text = "📈 買い" if row['Signal'] == 1 else "📉 売り"
                session = row['Session']
                print(f"   {date.strftime('%m/%d')}: ¥{row['Price']:.2f} - {signal_text} ({row['Confidence']:.1%}) [{session}] - {row['FX_Strategy']}")
        
        # 現在のFXポジション
        current_position = signals['Position'].iloc[-1]
        current_price = signals['Price'].iloc[-1]
        current_session = signals['Session'].iloc[-1]
        
        if abs(current_position) > 0:
            pos_text = f"📈 ロング({current_position:.1f})" if current_position > 0 else f"📉 ショート({abs(current_position):.1f})"
            print(f"\n📍 現在のFXポジション: {pos_text} (¥{current_price:.2f}) [{current_session}セッション]")
        else:
            print(f"\n📍 現在のFXポジション: ⏸️ フラット (¥{current_price:.2f}) [{current_session}セッション]")

def main():
    """メイン実行関数"""
    print("🚀 Phase 3.0 USDJPY最適化版デイトレードシステム")
    print("   ドル円相場特化・FX最適化パラメータ適用")
    print("   目標：ドル円で予測精度 70%+ を実現")
    print("=" * 80)
    
    system = Phase3USDJPYSystem()
    result = system.run_usdjpy_analysis()
    
    if result:
        print(f"\n✅ Phase 3.0 USDJPY最適化分析完了！")
        print(f"💱 ドル円予測精度: {result['performance']['Win_Rate']:.1f}%")
        print(f"💰 ネットリターン: {result['performance']['Total_Return']:.2f}%")
        print(f"💸 取引コスト: {result['performance']['Trading_Costs']:.3f}%")
        print(f"⚖️ シャープレシオ: {result['performance']['Sharpe_Ratio']:.2f}")
        
        if result['performance']['Win_Rate'] >= 70:
            print(f"\n🎉 ドル円FX目標達成！プロダクション運用準備完了")
        else:
            print(f"\n⚡ ドル円FXシステム性能向上中 - 継続的最適化推奨")
        
        print(f"\n🚀 ドル円特化Phase 3.0システム実装完了!")
        print(f"   - FX最適化パラメータ適用")
        print(f"   - セッション別取引戦略")
        print(f"   - スプレッドコスト考慮")
        print(f"   - ドル円特有パターン検出")
    else:
        print("❌ ドル円分析実行に失敗しました")

if __name__ == "__main__":
    main()