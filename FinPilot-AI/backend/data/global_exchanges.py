"""Global exchange registries, market identifiers, currencies, and trading calendars."""
import re
from typing import NamedTuple


class ExchangeInfo(NamedTuple):
    code: str
    name: str
    country: str
    region: str
    currency: str
    currency_symbol: str
    mic: str
    timezone: str
    suffix: str
    flag: str


# Global Stock Exchanges Registry
GLOBAL_EXCHANGES = {
    # United States
    "NYSE": ExchangeInfo("NYSE", "New York Stock Exchange", "United States", "North America", "USD", "$", "XNYS", "America/New_York", "", "🇺🇸"),
    "NASDAQ": ExchangeInfo("NASDAQ", "NASDAQ Stock Market", "United States", "North America", "USD", "$", "XNAS", "America/New_York", "", "🇺🇸"),
    "AMEX": ExchangeInfo("AMEX", "NYSE American", "United States", "North America", "USD", "$", "XASE", "America/New_York", "", "🇺🇸"),
    "US": ExchangeInfo("US", "US Composite", "United States", "North America", "USD", "$", "XNYS", "America/New_York", "", "🇺🇸"),
    
    # India
    "NSE": ExchangeInfo("NSE", "National Stock Exchange of India", "India", "Asia-Pacific", "INR", "₹", "XNSE", "Asia/Kolkata", ".NS", "🇮🇳"),
    "BSE": ExchangeInfo("BSE", "Bombay Stock Exchange", "India", "Asia-Pacific", "INR", "₹", "XBOM", "Asia/Kolkata", ".BO", "🇮🇳"),
    "NSI": ExchangeInfo("NSI", "National Stock Exchange of India", "India", "Asia-Pacific", "INR", "₹", "XNSE", "Asia/Kolkata", ".NS", "🇮🇳"),
    
    # United Kingdom
    "LSE": ExchangeInfo("LSE", "London Stock Exchange", "United Kingdom", "Europe", "GBP", "£", "XLON", "Europe/London", ".L", "🇬🇧"),
    "LON": ExchangeInfo("LON", "London Stock Exchange", "United Kingdom", "Europe", "GBP", "£", "XLON", "Europe/London", ".L", "🇬🇧"),
    
    # Germany
    "XETRA": ExchangeInfo("XETRA", "Deutsche Börse Xetra", "Germany", "Europe", "EUR", "€", "XETR", "Europe/Berlin", ".DE", "🇩🇪"),
    "FRA": ExchangeInfo("FRA", "Frankfurt Stock Exchange", "Germany", "Europe", "EUR", "€", "XFRA", "Europe/Berlin", ".F", "🇩🇪"),
    "GER": ExchangeInfo("GER", "Deutsche Börse", "Germany", "Europe", "EUR", "€", "XETR", "Europe/Berlin", ".DE", "🇩🇪"),
    
    # Japan
    "TSE": ExchangeInfo("TSE", "Tokyo Stock Exchange", "Japan", "Asia-Pacific", "JPY", "¥", "XTKS", "Asia/Tokyo", ".T", "🇯🇵"),
    "TYO": ExchangeInfo("TYO", "Tokyo Stock Exchange", "Japan", "Asia-Pacific", "JPY", "¥", "XTKS", "Asia/Tokyo", ".T", "🇯🇵"),
    "JPX": ExchangeInfo("JPX", "Japan Exchange Group", "Japan", "Asia-Pacific", "JPY", "¥", "XTKS", "Asia/Tokyo", ".T", "🇯🇵"),
    
    # Hong Kong & China
    "HKEX": ExchangeInfo("HKEX", "Hong Kong Stock Exchange", "Hong Kong", "Asia-Pacific", "HKD", "HK$", "XHKG", "Asia/Hong_Kong", ".HK", "🇭🇰"),
    "HKG": ExchangeInfo("HKG", "Hong Kong Stock Exchange", "Hong Kong", "Asia-Pacific", "HKD", "HK$", "XHKG", "Asia/Hong_Kong", ".HK", "🇭🇰"),
    "SSE": ExchangeInfo("SSE", "Shanghai Stock Exchange", "China", "Asia-Pacific", "CNY", "¥", "XSHG", "Asia/Shanghai", ".SS", "🇨🇳"),
    "SZSE": ExchangeInfo("SZSE", "Shenzhen Stock Exchange", "China", "Asia-Pacific", "CNY", "¥", "XSHE", "Asia/Shanghai", ".SZ", "🇨🇳"),
    "SHG": ExchangeInfo("SHG", "Shanghai Stock Exchange", "China", "Asia-Pacific", "CNY", "¥", "XSHG", "Asia/Shanghai", ".SS", "🇨🇳"),
    "SHE": ExchangeInfo("SHE", "Shenzhen Stock Exchange", "China", "Asia-Pacific", "CNY", "¥", "XSHE", "Asia/Shanghai", ".SZ", "🇨🇳"),
    
    # Canada
    "TSX": ExchangeInfo("TSX", "Toronto Stock Exchange", "Canada", "North America", "CAD", "C$", "XTSE", "America/Toronto", ".TO", "🇨🇦"),
    "TSXV": ExchangeInfo("TSXV", "TSX Venture Exchange", "Canada", "North America", "CAD", "C$", "XTSX", "America/Toronto", ".V", "🇨🇦"),
    "TOR": ExchangeInfo("TOR", "Toronto Stock Exchange", "Canada", "North America", "CAD", "C$", "XTSE", "America/Toronto", ".TO", "🇨🇦"),
    
    # Australia
    "ASX": ExchangeInfo("ASX", "Australian Securities Exchange", "Australia", "Asia-Pacific", "AUD", "A$", "XASX", "Australia/Sydney", ".AX", "🇦🇺"),
    
    # Europe
    "EURONEXT": ExchangeInfo("EURONEXT", "Euronext Paris", "France", "Europe", "EUR", "€", "XPAR", "Europe/Paris", ".PA", "🇫🇷"),
    "PAR": ExchangeInfo("PAR", "Euronext Paris", "France", "Europe", "EUR", "€", "XPAR", "Europe/Paris", ".PA", "🇫🇷"),
    "AMS": ExchangeInfo("AMS", "Euronext Amsterdam", "Netherlands", "Europe", "EUR", "€", "XAMS", "Europe/Amsterdam", ".AS", "🇳🇱"),
    "BRU": ExchangeInfo("BRU", "Euronext Brussels", "Belgium", "Europe", "EUR", "€", "XBRU", "Europe/Brussels", ".BR", "🇧🇪"),
    "SIX": ExchangeInfo("SIX", "SIX Swiss Exchange", "Switzerland", "Europe", "CHF", "CHF", "XSWX", "Europe/Zurich", ".SW", "🇨🇭"),
    "SWX": ExchangeInfo("SWX", "SIX Swiss Exchange", "Switzerland", "Europe", "CHF", "CHF", "XSWX", "Europe/Zurich", ".SW", "🇨🇭"),
    "MIL": ExchangeInfo("MIL", "Borsa Italiana", "Italy", "Europe", "EUR", "€", "XMIL", "Europe/Rome", ".MI", "🇮🇹"),
    "MCE": ExchangeInfo("MCE", "Bolsa de Madrid", "Spain", "Europe", "EUR", "€", "XMCE", "Europe/Madrid", ".MC", "🇪🇸"),
    
    # South Korea
    "KRX": ExchangeInfo("KRX", "Korea Exchange", "South Korea", "Asia-Pacific", "KRW", "₩", "XKRX", "Asia/Seoul", ".KS", "🇰🇷"),
    "KSC": ExchangeInfo("KSC", "Korea Stock Exchange (KOSPI)", "South Korea", "Asia-Pacific", "KRW", "₩", "XKRX", "Asia/Seoul", ".KS", "🇰🇷"),
    "KOE": ExchangeInfo("KOE", "KOSDAQ", "South Korea", "Asia-Pacific", "KRW", "₩", "XKOS", "Asia/Seoul", ".KQ", "🇰🇷"),
    
    # Singapore
    "SGX": ExchangeInfo("SGX", "Singapore Exchange", "Singapore", "Asia-Pacific", "SGD", "S$", "XSES", "Asia/Singapore", ".SI", "🇸🇬"),
    "SES": ExchangeInfo("SES", "Singapore Exchange", "Singapore", "Asia-Pacific", "SGD", "S$", "XSES", "Asia/Singapore", ".SI", "🇸🇬"),
    
    # Saudi Arabia
    "TADAWUL": ExchangeInfo("TADAWUL", "Saudi Stock Exchange (Tadawul)", "Saudi Arabia", "Middle East", "SAR", "SAR", "XSAU", "Asia/Riyadh", ".SR", "🇸🇦"),
    "SAU": ExchangeInfo("SAU", "Saudi Stock Exchange", "Saudi Arabia", "Middle East", "SAR", "SAR", "XSAU", "Asia/Riyadh", ".SR", "🇸🇦"),
    
    # Brazil
    "B3": ExchangeInfo("B3", "B3 - Brasil Bolsa Balcão", "Brazil", "Latin America", "BRL", "R$", "BVMF", "America/Sao_Paulo", ".SA", "🇧🇷"),
    "SAO": ExchangeInfo("SAO", "B3 São Paulo", "Brazil", "Latin America", "BRL", "R$", "BVMF", "America/Sao_Paulo", ".SA", "🇧🇷"),
}

# Suffix to Exchange lookup
SUFFIX_TO_EXCHANGE = {
    ".NS": "NSE",
    ".BO": "BSE",
    ".L": "LSE",
    ".DE": "XETRA",
    ".F": "FRA",
    ".T": "TSE",
    ".HK": "HKEX",
    ".SS": "SSE",
    ".SZ": "SZSE",
    ".TO": "TSX",
    ".V": "TSXV",
    ".AX": "ASX",
    ".PA": "EURONEXT",
    ".AS": "AMS",
    ".BR": "BRU",
    ".SW": "SIX",
    ".MI": "MIL",
    ".MC": "MCE",
    ".KS": "KRX",
    ".KQ": "KOE",
    ".SI": "SGX",
    ".SR": "TADAWUL",
    ".SA": "B3",
}

# Currency Symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "GBp": "p",
    "INR": "₹",
    "JPY": "¥",
    "CNY": "¥",
    "HKD": "HK$",
    "CAD": "C$",
    "AUD": "A$",
    "CHF": "CHF",
    "KRW": "₩",
    "SGD": "S$",
    "SAR": "SAR",
    "BRL": "R$",
    "TWD": "NT$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "ZAR": "R",
    "MXN": "Mex$",
}


def get_exchange_info(exchange_code_or_ticker: str) -> ExchangeInfo:
    """Resolve exchange metadata from an exchange code or a ticker with suffix.
    
    Defaults to US (USD) if unrecognized.
    """
    token = exchange_code_or_ticker.strip().upper()
    
    # Direct match on exchange code
    if token in GLOBAL_EXCHANGES:
        return GLOBAL_EXCHANGES[token]
    
    # Check ticker suffix (e.g. RELIANCE.NS -> .NS -> NSE)
    for suffix, exc_code in SUFFIX_TO_EXCHANGE.items():
        if token.endswith(suffix):
            return GLOBAL_EXCHANGES[exc_code]
            
    # Default fallback
    return GLOBAL_EXCHANGES["US"]


def format_currency_amount(amount: float, currency_code: str = "USD") -> str:
    """Format a monetary amount in its native currency with symbol and code."""
    if amount is None or not (isinstance(amount, (int, float))):
        return "N/A"
    
    code = (currency_code or "USD").upper()
    symbol = CURRENCY_SYMBOLS.get(code, f"{code} ")
    
    # JPY and KRW do not use decimal subunits
    if code in ("JPY", "KRW"):
        return f"{symbol}{amount:,.0f} {code}"
    
    # GBp (pence)
    if code == "GBP" or currency_code == "GBp":
        return f"£{amount:,.2f} GBP"
        
    return f"{symbol}{amount:,.2f} {code}"


def normalize_ticker_for_exchange(ticker: str, exchange_code: str = "") -> str:
    """Normalize a raw ticker to include the appropriate exchange suffix if necessary.
    
    Example: ('RELIANCE', 'NSE') -> 'RELIANCE.NS'
             ('7203', 'TSE') -> '7203.T'
             ('NVDA', 'NASDAQ') -> 'NVDA'
    """
    t = ticker.strip().upper()
    
    # Already contains a dot suffix?
    if "." in t:
        return t
        
    exc = (exchange_code or "").strip().upper()
    if not exc:
        return t
        
    info = GLOBAL_EXCHANGES.get(exc)
    if info and info.suffix:
        return f"{t}{info.suffix}"
        
    return t
