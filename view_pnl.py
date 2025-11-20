"""
View Simulated Trading P&L Report
Shows detailed statistics from simulated wallet
"""

import json
import os
from datetime import datetime
from simulated_wallet import SimulatedWallet


def print_separator(char="=", length=70):
    """Print a separator line"""
    print(char * length)


def main():
    """Display P&L report"""
    wallet = SimulatedWallet()

    print_separator()
    print("SIMULATED TRADING P&L REPORT")
    print_separator()

    # Balance Summary
    balance_info = wallet.get_balance_summary()
    print(f"\n📊 Balance Summary:")
    print(f"  Initial Balance:    ${balance_info['initial_balance']:>12,.2f} USDT")
    print(f"  Current Balance:    ${balance_info['available_balance']:>12,.2f} USDT")
    print(f"  Locked in Margin:   ${balance_info['used_margin']:>12,.2f} USDT")
    print(f"  Total Balance:      ${balance_info['total_balance']:>12,.2f} USDT")
    print(f"  Total P&L:          ${balance_info['total_pnl']:>12,.2f} ({balance_info['pnl_percent']:>+6.2f}%)")

    # Open Positions
    print(f"\n📈 Open Positions: {balance_info['position_count']}")
    positions = wallet.get_all_positions()

    if positions:
        print_separator("-")
        for pos in positions:
            pnl_symbol = "🟢" if pos['pnl'] >= 0 else "🔴"
            print(f"  {pnl_symbol} {pos['pair']} - {pos['side'].upper()}")
            print(f"     Entry: ${pos['entry_price']:.2f} | Current: ${pos['current_price']:.2f}")
            print(f"     Size: {pos['size']:.6f} | Margin: ${pos['margin']:.2f}")
            print(f"     Leverage: {pos['leverage']}x")
            print(f"     P&L: ${pos['pnl']:.2f} ({pos['pnl_percent']:+.2f}%)")
            print(f"     TP: ${pos['take_profit']:.2f} | SL: ${pos['stop_loss']:.2f}")
            print()

    # Trading Statistics
    stats = wallet.get_statistics()
    print(f"\n📉 Trading Statistics:")
    print(f"  Total Trades:       {stats['total_trades']:>12}")

    if stats['total_trades'] > 0:
        print(f"  Winning Trades:     {stats['winning_trades']:>12} ({stats['win_rate']:.1f}%)")
        print(f"  Losing Trades:      {stats['losing_trades']:>12}")
        print(f"  Win Rate:           {stats['win_rate']:>12.2f}%")
        print(f"  Average Win:        ${stats['avg_win']:>11,.2f}")
        print(f"  Average Loss:       ${stats['avg_loss']:>11,.2f}")
        print(f"  Largest Win:        ${stats['largest_win']:>11,.2f}")
        print(f"  Largest Loss:       ${stats['largest_loss']:>11,.2f}")

        # Risk/Reward Ratio
        if stats['avg_loss'] != 0:
            rr_ratio = abs(stats['avg_win'] / stats['avg_loss'])
            print(f"  Risk/Reward Ratio:  {rr_ratio:>12.2f}:1")

    # Recent Trades
    print(f"\n📜 Recent Trades (Last 10):")
    trades = wallet.get_trade_history(limit=10)
    closed_trades = [t for t in trades if t['type'] == 'close']

    if closed_trades:
        print_separator("-")
        for trade in closed_trades[-10:]:
            pnl = trade['pnl']
            pnl_symbol = "🟢" if pnl >= 0 else "🔴"
            timestamp = datetime.fromisoformat(trade['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

            print(f"  {pnl_symbol} {trade['pair']} - {trade['side'].upper()}")
            print(f"     Entry: ${trade['entry_price']:.2f} | Exit: ${trade['close_price']:.2f}")
            print(f"     P&L: ${pnl:.2f} ({trade['pnl_percent']:+.2f}%)")
            print(f"     Reason: {trade['reason']}")
            print(f"     Time: {timestamp}")
            print()
    else:
        print("  No closed trades yet")

    print_separator()

    # Wallet File Info
    if os.path.exists(wallet.data_file):
        file_size = os.path.getsize(wallet.data_file)
        file_time = datetime.fromtimestamp(os.path.getmtime(wallet.data_file))
        print(f"\nData file: {wallet.data_file}")
        print(f"Last updated: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"File size: {file_size} bytes")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("⚠️  No simulated wallet data found.")
        print("   Run the bot in dry-run mode first to generate trading data.")
    except Exception as e:
        print(f"Error: {e}")
