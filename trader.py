"""
trader.py — Buy, Sell, Orders & Portfolio
==========================================
Provides trading operations using the Flattrade API:

  • place_buy_order   — buy shares (market or limit)
  • place_sell_order  — sell shares (market or limit)
  • get_order_book    — list all today's orders
  • get_positions     — current open positions with P&L
  • get_holdings      — long-term holdings
  • cancel_order      — cancel a pending order
  • get_account_limits — cash balance, margins

Price Types:
  - 'MKT'  : Market order — executes immediately at best price
  - 'LMT'  : Limit order  — executes only at your specified price or better
  - 'SL-LMT': Stop-Loss Limit

Product Types:
  - 'C' : CNC (Cash & Carry) — delivery/long-term holding
  - 'I' : Intraday (MIS)     — auto square-off at 3:20 PM
  - 'M' : Margin
"""

from api_helper import NorenApiPy


def place_buy_order(api, symbol, exchange, quantity, price=0.0, price_type='MKT',
                    product_type='C', trigger_price=None, remarks='buy_order'):
    """
    Place a BUY order.

    Args:
        api          : NorenApiPy session object
        symbol       : Trading symbol e.g. 'INFY-EQ'
        exchange     : 'NSE' or 'BSE'
        quantity     : Number of shares to buy
        price        : Limit price (0 for market orders)
        price_type   : 'MKT' | 'LMT' | 'SL-LMT'
        product_type : 'C' (delivery) | 'I' (intraday)
        trigger_price: Required for SL orders
        remarks      : Order tag (any string)

    Returns:
        dict with order status and order ID
    """
    ret = api.place_order(
        buy_or_sell='B',
        product_type=product_type,
        exchange=exchange,
        tradingsymbol=symbol,
        quantity=quantity,
        discloseqty=0,
        price_type=price_type,
        price=price,
        trigger_price=trigger_price,
        retention='DAY',
        remarks=remarks
    )
    _print_order_result('BUY', symbol, quantity, price, price_type, ret)
    return ret


def place_sell_order(api, symbol, exchange, quantity, price=0.0, price_type='MKT',
                     product_type='C', trigger_price=None, remarks='sell_order'):
    """
    Place a SELL order.

    Args: (same as place_buy_order)

    Returns:
        dict with order status and order ID
    """
    ret = api.place_order(
        buy_or_sell='S',
        product_type=product_type,
        exchange=exchange,
        tradingsymbol=symbol,
        quantity=quantity,
        discloseqty=0,
        price_type=price_type,
        price=price,
        trigger_price=trigger_price,
        retention='DAY',
        remarks=remarks
    )
    _print_order_result('SELL', symbol, quantity, price, price_type, ret)
    return ret


def get_order_book(api):
    """Fetch and display all orders placed today."""
    ret = api.get_order_book()
    if not ret:
        print("\n  No orders found today.\n")
        return []
    print(f"\n  📋 Order Book ({len(ret)} orders)")
    print(f"  {'Order ID':<25} {'Symbol':<20} {'B/S':<5} {'Qty':<8} {'Price':<10} {'Status'}")
    print(f"  {'-'*85}")
    for o in ret:
        print(f"  {o.get('norenordno',''):<25} {o.get('tsym',''):<20} "
              f"{o.get('trantype',''):<5} {o.get('qty',''):<8} "
              f"{o.get('prc',''):<10} {o.get('status','')}")
    print()
    return ret


def get_positions(api):
    """Fetch and display current open positions with P&L."""
    ret = api.get_positions()
    if not ret:
        print("\n  No open positions.\n")
        return []
    print(f"\n  📊 Positions ({len(ret)} open)")
    print(f"  {'Symbol':<20} {'Qty':<8} {'Avg Price':<12} {'LTP':<10} {'P&L':<12} {'Product'}")
    print(f"  {'-'*75}")
    for p in ret:
        pnl = float(p.get('rpnl', 0)) + float(p.get('urmtom', 0))
        pnl_str = f"₹{pnl:+.2f}"
        print(f"  {p.get('tsym',''):<20} {p.get('netqty',''):<8} "
              f"₹{p.get('netavgprc',''):<11} ₹{p.get('lp',''):<9} "
              f"{pnl_str:<12} {p.get('prd','')}")
    print()
    return ret


def get_holdings(api):
    """Fetch and display long-term holdings."""
    ret = api.get_holdings()
    if not ret:
        print("\n  No holdings found.\n")
        return []
    print(f"\n  🏦 Holdings ({len(ret)} stocks)")
    print(f"  {'Symbol':<20} {'Qty':<8} {'Avg Price':<12} {'LTP':<10} {'P&L':<12}")
    print(f"  {'-'*65}")
    for h in ret:
        pnl = (float(h.get('lp', 0)) - float(h.get('upldprc', 0))) * float(h.get('holdqty', 0))
        print(f"  {h.get('tsym',''):<20} {h.get('holdqty',''):<8} "
              f"₹{h.get('upldprc',''):<11} ₹{h.get('lp',''):<9} ₹{pnl:+.2f}")
    print()
    return ret


def cancel_order(api, order_id):
    """Cancel a pending order by its Order ID."""
    ret = api.cancel_order(orderno=order_id)
    if ret and ret.get('stat') == 'Ok':
        print(f"  ✅ Order {order_id} cancelled successfully.")
    else:
        print(f"  ❌ Cancel failed: {ret}")
    return ret


def get_account_limits(api):
    """Show cash balance and margin details."""
    ret = api.get_limits()
    if ret and ret.get('stat') == 'Ok':
        print(f"\n  💰 Account Limits")
        print(f"  {'='*35}")
        print(f"  Cash Balance   : ₹{float(ret.get('cash', 0)):,.2f}")
        print(f"  Pay-in Today   : ₹{float(ret.get('payin', 0)):,.2f}")
        print(f"  Pay-out        : ₹{float(ret.get('payout', 0)):,.2f}")
        print(f"  Blocked Margin : ₹{float(ret.get('brkcollamt', 0)):,.2f}")
        print(f"  {'='*35}\n")
    else:
        print(f"  ❌ Could not fetch limits: {ret}")
    return ret


def _print_order_result(side, symbol, qty, price, price_type, ret):
    """Internal helper to print order placement result."""
    if ret and ret.get('stat') == 'Ok':
        print(f"\n  ✅ {side} order placed!")
        print(f"     Symbol   : {symbol}")
        print(f"     Qty      : {qty}")
        print(f"     Price    : {'Market' if price_type == 'MKT' else f'₹{price}'}")
        print(f"     Order ID : {ret.get('norenordno', 'N/A')}\n")
    else:
        print(f"\n  ❌ {side} order FAILED: {ret}\n")


def run_trader_menu(api):
    """Interactive trading menu."""
    while True:
        print("  ┌─────────────────────────────────────────────┐")
        print("  │              Trading Panel                  │")
        print("  ├─────────────────────────────────────────────┤")
        print("  │  1. Place BUY order                         │")
        print("  │  2. Place SELL order                        │")
        print("  │  3. View order book                         │")
        print("  │  4. View open positions                     │")
        print("  │  5. View holdings                           │")
        print("  │  6. Cancel an order                         │")
        print("  │  7. Account balance & limits                │")
        print("  │  b. Back to main menu                       │")
        print("  └─────────────────────────────────────────────┘")
        choice = input("\n  Choice: ").strip().lower()

        if choice == '1':
            sym  = input("  Symbol (e.g. INFY-EQ): ").strip()
            ex   = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            qty  = int(input("  Quantity: ").strip())
            pt   = input("  Price type [MKT/LMT] (default MKT): ").strip().upper() or 'MKT'
            pr   = float(input("  Limit price (0 for market): ").strip() or 0)
            prod = input("  Product [C=delivery / I=intraday] (default C): ").strip().upper() or 'C'
            place_buy_order(api, sym, ex, qty, pr, pt, prod)

        elif choice == '2':
            sym  = input("  Symbol (e.g. INFY-EQ): ").strip()
            ex   = input("  Exchange [NSE/BSE] (default NSE): ").strip() or 'NSE'
            qty  = int(input("  Quantity: ").strip())
            pt   = input("  Price type [MKT/LMT] (default MKT): ").strip().upper() or 'MKT'
            pr   = float(input("  Limit price (0 for market): ").strip() or 0)
            prod = input("  Product [C=delivery / I=intraday] (default C): ").strip().upper() or 'C'
            place_sell_order(api, sym, ex, qty, pr, pt, prod)

        elif choice == '3':
            get_order_book(api)
        elif choice == '4':
            get_positions(api)
        elif choice == '5':
            get_holdings(api)
        elif choice == '6':
            oid = input("  Order ID to cancel: ").strip()
            cancel_order(api, oid)
        elif choice == '7':
            get_account_limits(api)
        elif choice == 'b':
            break
        else:
            print("  Invalid choice.\n")
