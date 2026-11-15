"""Virtual Investing & Paper Trading Engine for FinPilot AI.
Provides simulated order execution, FX conversions, portfolio calculations,
and risk analytics with zero real-money connectivity.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import math
from sqlalchemy.orm import Session

from database.models import (
    User, VirtualAccount, Portfolio, Holdings, VirtualOrders, VirtualTransactions
)
from backend.data.market_data import get_latest_price
from backend.data.global_exchanges import get_exchange_info

# Indicative FX Conversion rates relative to USD
# Provides deterministic, realistic multi-currency conversion for paper trading
BASE_FX_TO_USD = {
    "USD": 1.0,
    "INR": 0.0116,    # 1 INR = ~0.0116 USD (or ~86 INR per USD)
    "EUR": 1.08,      # 1 EUR = 1.08 USD
    "GBP": 1.28,      # 1 GBP = 1.28 USD
    "JPY": 0.0066,    # 1 JPY = ~0.0066 USD (or ~152 JPY per USD)
    "CAD": 0.73,
    "AUD": 0.65,
    "HKD": 0.128,
    "KRW": 0.00072,
    "CHF": 1.12,
    "CNY": 0.138,
    "SAR": 0.266
}


def get_fx_rate(from_curr: str, to_curr: str) -> float:
    """Calculate conversion rate between two currencies via USD base."""
    f = from_curr.upper()
    t = to_curr.upper()
    if f == t:
        return 1.0
    f_to_usd = BASE_FX_TO_USD.get(f, 1.0)
    t_to_usd = BASE_FX_TO_USD.get(t, 1.0)
    # 1 from_curr in to_curr = f_to_usd / t_to_usd
    return f_to_usd / t_to_usd


class PaperTradingEngine:
    """Core paper trading and portfolio calculation engine."""

    @staticmethod
    def get_user_account_summary(user_id: int, db: Session) -> Dict[str, Any]:
        """Fetch and recalculate comprehensive live portfolio and cash metrics."""
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"error": "User not found"}

        v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
        if not v_acc:
            v_acc = VirtualAccount(user_id=user_id, initial_virtual_balance=100000.0, available_cash=100000.0, account_currency="INR")
            db.add(v_acc)
            db.commit()
            db.refresh(v_acc)

        acc_currency = v_acc.account_currency or user.preferred_currency or "INR"
        holdings = db.query(Holdings).filter(Holdings.user_id == user_id, Holdings.quantity > 0).all()

        total_invested_in_acc_curr = 0.0
        total_current_holdings_val = 0.0
        holdings_data = []

        for h in holdings:
            # Fetch latest real price
            quote_info = get_latest_price(h.ticker)
            current_price = quote_info.get("price") if quote_info else None
            asset_currency = (h.currency or quote_info.get("currency") or "USD").upper()

            # FX rate: asset currency -> user's account currency
            fx = get_fx_rate(asset_currency, acc_currency)

            if current_price is None or current_price <= 0:
                current_price = h.average_cost

            curr_val_asset = h.quantity * current_price
            cost_basis_asset = h.quantity * h.average_cost

            curr_val_acc = curr_val_asset * fx
            cost_basis_acc = cost_basis_asset * fx

            unrealized_pnl_acc = curr_val_acc - cost_basis_acc
            pnl_pct = ((current_price - h.average_cost) / h.average_cost * 100) if h.average_cost > 0 else 0.0

            total_invested_in_acc_curr += cost_basis_acc
            total_current_holdings_val += curr_val_acc

            holdings_data.append({
                "holding_id": h.holding_id,
                "ticker": h.ticker,
                "company_name": h.company_name or h.ticker,
                "exchange": h.exchange,
                "country": h.country,
                "quantity": h.quantity,
                "average_cost": h.average_cost,
                "current_price": current_price,
                "asset_currency": asset_currency,
                "current_value_acc": round(curr_val_acc, 2),
                "invested_amount_acc": round(cost_basis_acc, 2),
                "unrealized_pnl_acc": round(unrealized_pnl_acc, 2),
                "pnl_pct": round(pnl_pct, 2),
                "fx_rate_applied": round(fx, 4)
            })

        # Calculate realized P&L from transactions
        transactions = db.query(VirtualTransactions).filter(VirtualTransactions.user_id == user_id).all()
        total_realized_pnl = sum(t.realized_pnl for t in transactions if t.realized_pnl is not None)

        total_portfolio_value = v_acc.available_cash + total_current_holdings_val
        overall_unrealized_pnl = total_current_holdings_val - total_invested_in_acc_curr
        
        initial_bal = v_acc.initial_virtual_balance or 100000.0
        total_return_pct = ((total_portfolio_value - initial_bal) / initial_bal * 100) if initial_bal > 0 else 0.0

        # Update Portfolio table
        port = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
        if not port:
            port = Portfolio(user_id=user_id)
            db.add(port)
        port.total_value = total_portfolio_value
        port.invested_value = total_current_holdings_val
        port.cash_balance = v_acc.available_cash
        port.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Risk metrics
        risk_metrics = PaperTradingEngine._calculate_risk_metrics(holdings_data, total_current_holdings_val, total_portfolio_value)

        return {
            "account_currency": acc_currency,
            "initial_virtual_balance": round(initial_bal, 2),
            "available_cash": round(v_acc.available_cash, 2),
            "invested_value": round(total_current_holdings_val, 2),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "unrealized_pnl": round(overall_unrealized_pnl, 2),
            "realized_pnl": round(total_realized_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "holdings": holdings_data,
            "risk_metrics": risk_metrics
        }

    @staticmethod
    def _calculate_risk_metrics(holdings_data: List[Dict[str, Any]], total_invested: float, total_val: float) -> Dict[str, Any]:
        """Compute portfolio concentration and risk analytics."""
        if not holdings_data or total_invested <= 0:
            return {
                "concentration_risk": "Low (100% Cash)",
                "max_holding_pct": 0.0,
                "top_holding": "None",
                "hhi_index": 0.0,
                "asset_allocation": {"Cash": 100.0, "Equities": 0.0},
                "country_exposure": {},
                "diversification_status": "All cash — allocate into quality assets to diversify"
            }

        sorted_h = sorted(holdings_data, key=lambda x: x["current_value_acc"], reverse=True)
        top_h = sorted_h[0]
        max_pct = (top_h["current_value_acc"] / total_invested) * 100

        # Herfindahl-Hirschman Index (HHI)
        hhi = sum(((h["current_value_acc"] / total_invested) * 100) ** 2 for h in holdings_data)

        if max_pct > 50 or hhi > 2500:
            conc_label = "High (Heavy single-stock exposure)"
        elif max_pct > 25 or hhi > 1500:
            conc_label = "Moderate"
        else:
            conc_label = "Well Diversified"

        # Country exposure
        country_exp: Dict[str, float] = {}
        for h in holdings_data:
            c = h.get("country") or "Other"
            country_exp[c] = country_exp.get(c, 0.0) + h["current_value_acc"]
        
        country_pcts = {c: round((v / total_invested) * 100, 1) for c, v in country_exp.items()}

        cash_pct = round(((total_val - total_invested) / total_val * 100), 1) if total_val > 0 else 0.0
        equity_pct = round((total_invested / total_val * 100), 1) if total_val > 0 else 0.0

        return {
            "concentration_risk": conc_label,
            "max_holding_pct": round(max_pct, 1),
            "top_holding": f"{top_h['company_name']} ({top_h['ticker']})",
            "hhi_index": round(hhi, 1),
            "asset_allocation": {"Cash": cash_pct, "Equities": equity_pct},
            "country_exposure": country_pcts,
            "diversification_status": "Diversified across global markets" if len(holdings_data) >= 4 else "Concentrated in fewer than 4 holdings"
        }

    @staticmethod
    def execute_buy_order(
        user_id: int,
        ticker: str,
        company_name: str,
        exchange: str,
        country: str,
        currency: str,
        order_type: str,  # 'MARKET' or 'LIMIT'
        quantity: Optional[float] = None,
        investment_amount_acc: Optional[float] = None,
        limit_price: Optional[float] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Execute a simulated buy order with real market pricing and currency conversion."""
        v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
        if not v_acc:
            return {"success": False, "error": "Virtual account not found."}

        acc_currency = v_acc.account_currency or "INR"
        quote_info = get_latest_price(ticker)
        current_market_price = quote_info.get("price") if quote_info else None

        if current_market_price is None or current_market_price <= 0:
            return {
                "success": False,
                "error": f"Live market price for {ticker} is currently unavailable. Simulated order rejected to prevent fabricated pricing."
            }

        # Determine quote source transparency
        quote_source = quote_info.get("source", "UNKNOWN")
        is_demo = quote_info.get("is_demo", False)
        quote_warning = None
        if is_demo:
            quote_warning = (
                f"⚠️ DEMO DATA: This order was executed using offline/cached pricing "
                f"(source: {quote_source}). The quoted price of {current_market_price:.2f} "
                f"may not reflect the actual live market price. "
                f"Connect to the internet for real-time quotes."
            )

        asset_curr = (currency or quote_info.get("currency") or "USD").upper()
        fx_rate = get_fx_rate(asset_curr, acc_currency)

        # Determine price & execution
        if order_type.upper() == "LIMIT":
            if not limit_price or limit_price <= 0:
                return {"success": False, "error": "Valid limit price required for Limit orders."}
            if current_market_price > limit_price:
                # Pending limit order
                order = VirtualOrders(
                    user_id=user_id,
                    ticker=ticker,
                    company_name=company_name,
                    exchange=exchange,
                    currency=asset_curr,
                    order_type="LIMIT",
                    side="BUY",
                    quantity=quantity or 1.0,
                    limit_price=limit_price,
                    order_status="PENDING",
                    created_at=datetime.now(timezone.utc)
                )
                db.add(order)
                db.commit()
                return {
                    "success": True,
                    "status": "PENDING",
                    "message": f"Limit order placed for {quantity} shares at {limit_price} {asset_curr}. Current price: {current_market_price} {asset_curr}."
                }
            exec_price = limit_price
        else:
            exec_price = current_market_price

        # Calculate quantity and total required in account currency
        if quantity is not None and quantity > 0:
            trade_qty = quantity
            total_cost_acc = trade_qty * exec_price * fx_rate
        elif investment_amount_acc is not None and investment_amount_acc > 0:
            trade_cost_in_asset_curr = investment_amount_acc / fx_rate
            trade_qty = round(trade_cost_in_asset_curr / exec_price, 4)
            total_cost_acc = investment_amount_acc
        else:
            return {"success": False, "error": "Please provide either quantity or investment amount."}

        # Validate sufficient cash
        if v_acc.available_cash < total_cost_acc:
            return {
                "success": False,
                "error": f"Insufficient virtual funds. Required: {acc_currency} {total_cost_acc:,.2f}, Available: {acc_currency} {v_acc.available_cash:,.2f}"
            }

        # Deduct cash
        v_acc.available_cash -= total_cost_acc

        # Record Order
        order = VirtualOrders(
            user_id=user_id,
            ticker=ticker,
            company_name=company_name,
            exchange=exchange,
            currency=asset_curr,
            order_type=order_type.upper(),
            side="BUY",
            quantity=trade_qty,
            limit_price=limit_price,
            execution_price=exec_price,
            order_status="EXECUTED",
            created_at=datetime.now(timezone.utc),
            executed_at=datetime.now(timezone.utc)
        )
        db.add(order)
        db.flush()

        # Record Transaction
        tx = VirtualTransactions(
            user_id=user_id,
            order_id=order.order_id,
            ticker=ticker,
            company_name=company_name,
            transaction_type="BUY",
            quantity=trade_qty,
            price=exec_price,
            fees=0.0,
            total_amount=total_cost_acc,
            currency=acc_currency,
            realized_pnl=0.0,
            transaction_date=datetime.now(timezone.utc)
        )
        db.add(tx)

        # Update Holdings
        holding = db.query(Holdings).filter(Holdings.user_id == user_id, Holdings.ticker == ticker).first()
        if holding:
            total_existing_cost = holding.quantity * holding.average_cost
            total_new_cost = trade_qty * exec_price
            holding.quantity += trade_qty
            holding.average_cost = (total_existing_cost + total_new_cost) / holding.quantity
        else:
            holding = Holdings(
                user_id=user_id,
                ticker=ticker,
                company_name=company_name,
                exchange=exchange,
                country=country,
                quantity=trade_qty,
                average_cost=exec_price,
                currency=asset_curr
            )
            db.add(holding)

        db.commit()

        result = {
            "success": True,
            "status": "EXECUTED",
            "ticker": ticker,
            "quantity": trade_qty,
            "execution_price": exec_price,
            "asset_currency": asset_curr,
            "total_cost_acc": round(total_cost_acc, 2),
            "account_currency": acc_currency,
            "remaining_cash": round(v_acc.available_cash, 2),
            "fx_rate": round(fx_rate, 4),
            "quote_source": quote_source,
            "is_demo_price": is_demo,
            "message": f"Successfully purchased {trade_qty} shares of {ticker} at {exec_price:.2f} {asset_curr}."
        }
        if quote_warning:
            result["quote_warning"] = quote_warning
        return result

    @staticmethod
    def execute_sell_order(
        user_id: int,
        ticker: str,
        quantity: float,
        db: Session
    ) -> Dict[str, Any]:
        """Sell part or all of an existing holding, realizing P&L."""
        v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
        holding = db.query(Holdings).filter(Holdings.user_id == user_id, Holdings.ticker == ticker).first()

        if not holding or holding.quantity <= 0:
            return {"success": False, "error": f"You do not own any shares of {ticker}."}

        if quantity > holding.quantity:
            return {
                "success": False,
                "error": f"Cannot sell {quantity} shares. You currently own {holding.quantity} shares."
            }

        quote_info = get_latest_price(ticker)
        current_price = quote_info.get("price") if quote_info else None
        if not current_price or current_price <= 0:
            return {"success": False, "error": f"Unable to fetch live quote for {ticker}. Sell order aborted."}

        quote_source = quote_info.get("source", "UNKNOWN")
        is_demo = quote_info.get("is_demo", False)
        quote_warning = None
        if is_demo:
            quote_warning = (
                f"⚠️ DEMO DATA: This sell order was executed using offline/cached pricing "
                f"(source: {quote_source}). The quoted price of {current_price:.2f} "
                f"may not reflect the actual live market price."
            )

        acc_currency = v_acc.account_currency or "INR"
        asset_curr = (holding.currency or "USD").upper()
        fx_rate = get_fx_rate(asset_curr, acc_currency)

        sale_proceeds_acc = quantity * current_price * fx_rate
        cost_basis_acc = quantity * holding.average_cost * fx_rate
        realized_pnl_acc = sale_proceeds_acc - cost_basis_acc

        # Credit cash
        v_acc.available_cash += sale_proceeds_acc

        # Deduct holding
        remaining_qty = holding.quantity - quantity
        if remaining_qty <= 0.0001:
            db.delete(holding)
            remaining_qty = 0.0
        else:
            holding.quantity = remaining_qty

        # Record Order
        order = VirtualOrders(
            user_id=user_id,
            ticker=ticker,
            company_name=holding.company_name or ticker,
            exchange=holding.exchange,
            currency=asset_curr,
            order_type="MARKET",
            side="SELL",
            quantity=quantity,
            execution_price=current_price,
            order_status="EXECUTED",
            created_at=datetime.now(timezone.utc),
            executed_at=datetime.now(timezone.utc)
        )
        db.add(order)
        db.flush()

        # Record Transaction
        tx = VirtualTransactions(
            user_id=user_id,
            order_id=order.order_id,
            ticker=ticker,
            company_name=holding.company_name or ticker,
            transaction_type="SELL",
            quantity=quantity,
            price=current_price,
            fees=0.0,
            total_amount=sale_proceeds_acc,
            currency=acc_currency,
            realized_pnl=realized_pnl_acc,
            transaction_date=datetime.now(timezone.utc)
        )
        db.add(tx)
        db.commit()

        result = {
            "success": True,
            "ticker": ticker,
            "quantity_sold": quantity,
            "sale_price": current_price,
            "asset_currency": asset_curr,
            "sale_proceeds_acc": round(sale_proceeds_acc, 2),
            "realized_pnl_acc": round(realized_pnl_acc, 2),
            "account_currency": acc_currency,
            "remaining_quantity": round(remaining_qty, 4),
            "new_cash_balance": round(v_acc.available_cash, 2),
            "quote_source": quote_source,
            "is_demo_price": is_demo,
            "message": f"Successfully sold {quantity} shares of {ticker}. Realized P&L: {acc_currency} {realized_pnl_acc:+,.2f}."
        }
        if quote_warning:
            result["quote_warning"] = quote_warning
        return result

    @staticmethod
    def reset_virtual_account(user_id: int, new_balance: Optional[float] = None, db: Session = None) -> Dict[str, Any]:
        """Reset the virtual portfolio and cash balance with complete audit logging."""
        v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
        if not v_acc:
            return {"success": False, "error": "Account not found."}

        reset_val = new_balance if new_balance and new_balance > 0 else (v_acc.initial_virtual_balance or 100000.0)

        # Clear holdings
        db.query(Holdings).filter(Holdings.user_id == user_id).delete()

        # Reset cash
        v_acc.available_cash = reset_val
        v_acc.initial_virtual_balance = reset_val

        # Reset portfolio
        port = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
        if port:
            port.total_value = reset_val
            port.invested_value = 0.0
            port.cash_balance = reset_val
            port.updated_at = datetime.now(timezone.utc)

        # Log reset transaction
        tx = VirtualTransactions(
            user_id=user_id,
            ticker="ACCOUNT_RESET",
            company_name="Virtual Account Reset",
            transaction_type="RESET",
            quantity=0.0,
            price=0.0,
            total_amount=reset_val,
            currency=v_acc.account_currency or "INR",
            realized_pnl=0.0,
            transaction_date=datetime.now(timezone.utc)
        )
        db.add(tx)
        db.commit()

        return {
            "success": True,
            "message": f"Practice account reset to {v_acc.account_currency} {reset_val:,.2f}.",
            "new_cash_balance": reset_val
        }

    @staticmethod
    def add_virtual_funds(user_id: int, amount: float, db: Session) -> Dict[str, Any]:
        """Add additional fake practice funds to the virtual account."""
        if amount <= 0:
            return {"success": False, "error": "Amount must be greater than zero."}

        v_acc = db.query(VirtualAccount).filter(VirtualAccount.user_id == user_id).first()
        if not v_acc:
            return {"success": False, "error": "Account not found."}

        v_acc.available_cash += amount
        
        tx = VirtualTransactions(
            user_id=user_id,
            ticker="FUNDS_DEPOSIT",
            company_name="Simulated Virtual Top-Up",
            transaction_type="DEPOSIT",
            quantity=0.0,
            price=0.0,
            total_amount=amount,
            currency=v_acc.account_currency or "INR",
            realized_pnl=0.0,
            transaction_date=datetime.now(timezone.utc)
        )
        db.add(tx)
        db.commit()

        return {
            "success": True,
            "new_balance": round(v_acc.available_cash, 2),
            "currency": v_acc.account_currency,
            "message": f"Added {v_acc.account_currency} {amount:,.2f} virtual practice funds."
        }
