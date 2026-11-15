export interface User {
  user_id: number;
  name: string;
  email: string;
  experience_level: string;
  learning_goals?: string;
  risk_comfort?: string;
  preferred_currency: string;
  preferred_mode?: string;
  onboarding_completed: boolean;
  created_at?: string;
}

export interface Quote {
  ticker: string;
  price: number;
  close: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  change: number;
  change_pct: number;
  currency: string;
  timestamp?: string;
  formatted_close: string;
  formatted_change: string;
  source?: string;
}

export interface IndexData {
  name: string;
  ticker: string;
  country: string;
  flag: string;
  price: number;
  change: number;
  change_pct: number;
  formatted_close: string;
  formatted_change: string;
}

export interface Holding {
  holding_id: number;
  ticker: string;
  company_name: string;
  exchange: string;
  country: string;
  quantity: number;
  average_cost: number;
  current_price: number;
  asset_currency: string;
  current_value_acc: number;
  invested_amount_acc: number;
  unrealized_pnl_acc: number;
  pnl_pct: number;
  fx_rate_applied: number;
}

export interface PortfolioSummary {
  account_id: number;
  account_currency: string;
  initial_virtual_balance: number;
  available_cash: number;
  invested_value: number;
  total_portfolio_value: number;
  unrealized_pnl: number;
  total_return_pct: number;
  holdings_count: number;
  holdings: Holding[];
  risk_metrics?: {
    hhi: number;
    concentration_risk: string;
  };
  country_exposure?: Record<string, number>;
  sector_exposure?: Record<string, number>;
}

export interface Order {
  order_id: number;
  ticker: string;
  company_name: string;
  exchange: string;
  order_type: string;
  side: string;
  quantity: number;
  execution_price: number;
  order_status: string;
  created_at: string;
}

export interface Transaction {
  transaction_id: number;
  ticker: string;
  company_name: string;
  type: string;
  quantity: number;
  price: number;
  total_amount: number;
  currency: string;
  realized_pnl: number;
  date: string;
}

export interface SearchResult {
  ticker: string;
  name: string;
  exchange: string;
  exchange_name?: string;
  country: string;
  region?: string;
  currency: string;
  currency_symbol?: string;
  flag?: string;
  score?: number;
}

export interface Candle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20?: number | null;
  sma50?: number | null;
  ema20?: number | null;
  rsi?: number;
  macd?: number;
  macd_signal?: number;
  macd_hist?: number;
}

export interface CompanyFundamentals {
  company_name: string;
  ticker: string;
  exchange: string;
  country: string;
  currency: string;
  currency_symbol: string;
  sector: string;
  industry: string;
  revenue?: number;
  net_income?: number;
  operating_income?: number;
  total_assets?: number;
  total_liabilities?: number;
  total_debt?: number;
  operating_cash_flow?: number;
  revenue_growth?: number;
  profit_margin?: number;
  eps?: number;
  debt_to_equity?: number;
  trailing_pe?: number;
  market_cap?: string;
}

export interface NewsItem {
  title: string;
  text: string;
  published_at: string;
  url: string;
  source: string;
  identified_company?: string;
}

export interface FilingItem {
  ticker: string;
  company_name: string;
  form: string;
  document_type: string;
  date: string;
  url: string;
  title: string;
  country: string;
  source: string;
}

export interface Lesson {
  lesson_id: string;
  title: string;
  category: string;
  description: string;
  content: string;
  completed: boolean;
  quiz?: {
    question: string;
    options: string[];
    correct_option_index: number;
    explanation: string;
  };
}

export interface AnalysisResult {
  ticker: string;
  company_name: string;
  country: string;
  exchange: string;
  currency: string;
  currency_symbol: string;
  prediction: {
    direction: string;
    probability: number;
    selected_model: string;
  };
  training: {
    best_model_name: string;
    best_metrics: {
      accuracy: number;
      precision: number;
      recall: number;
      f1_score: number;
      roc_auc: number;
    };
    comparison?: Record<string, any>;
  };
  sentiment: {
    available: boolean;
    overall_sentiment?: string;
    overall_label?: string;
    positive_ratio?: number;
    negative_ratio?: number;
    neutral_ratio?: number;
    message?: string;
  };
  shap_info?: {
    top_positive?: Array<{ feature: string; contribution: number }>;
    top_negative?: Array<{ feature: string; contribution: number }>;
    base_value?: number;
    estimator_type?: string;
  };
  llm_explanation?: string;
}
